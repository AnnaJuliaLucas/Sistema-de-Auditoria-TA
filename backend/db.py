r"""
db.py — Database connection layer for FastAPI backend.
Supports BOTH SQLite (local dev) and PostgreSQL (Docker/production).

Behavior:
  - If DATABASE_URL env var is set → uses PostgreSQL
  - Otherwise → uses SQLite at C:\AuditoriaTA\dados\auditoria_ta.db
"""

import os
import urllib.parse
import json
import shutil
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
import logging

log = logging.getLogger("auditoria_db")

# ─────────────────────────────────────────────────────────────────────────────
# PATH CONFIGURATION (Shared)
# ─────────────────────────────────────────────────────────────────────────────
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
IS_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("RAILWAY_ENVIRONMENT")

if IS_VERCEL:
    BASE_DIR = Path("/tmp/AuditoriaTA")
elif IS_DOCKER:
    # No Railway ou Docker, usamos o volume persistente montado em /app/data
    BASE_DIR = Path("/app/data")
else:
    BASE_DIR = Path(r"C:\AuditoriaTA")
    if not BASE_DIR.drive:
        BASE_DIR = Path.home() / "AuditoriaTA"

DADOS_DIR  = BASE_DIR / "dados"
BACKUP_DIR = BASE_DIR / "dados" / "backups"
DB_PATH = DADOS_DIR / "auditoria_ta.db"
MAX_BACKUPS = 30


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MODE DETECTION
# ─────────────────────────────────────────────────────────────────────────────
# Check multiple possible env vars for PostgreSQL (Vercel Integration / Manual)
DATABASE_URL = (
    os.environ.get("DATABASE_URL") or 
    os.environ.get("POSTGRES_URL") or 
    os.environ.get("NEON_DATABASE_URL") or 
    ""
)
USE_POSTGRES = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")

if USE_POSTGRES:
    # Mask password for safe logging
    try:
        url_parts = DATABASE_URL.split("@")
        masked_url = url_parts[-1] if len(url_parts) > 1 else "configured"
        log.info(f"Using PostgreSQL: {masked_url}")
    except Exception:
        log.info("Using PostgreSQL: (masked due to error)")
else:
    import sqlite3
    log.info(f"Using SQLite: {DB_PATH}")


def ensure_dirs():
    if not USE_POSTGRES:
        DADOS_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

def _pg_connect():
    """Conecta no PostgreSQL da Vercel/Neon com SSL."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    url = DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL is not set and USE_POSTGRES is True")
        
    # Standardize scheme (psycopg2 version compatibility)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        
    # Neon/Vercel usually require SSL
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
        
    try:
        # Use RealDictCursor to maintain compatibility with SQLite-style Row access
        return psycopg2.connect(url, cursor_factory=RealDictCursor)
    except Exception as e:
        log.error(f"PostgreSQL connection failed: {e}")
        raise

def _sqlite_connect():
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections. Works with both SQLite and PostgreSQL."""
    if USE_POSTGRES:
        conn = _pg_connect()
        try:
            yield PgCursorWrapper(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = _sqlite_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class PgCursorWrapper:
    """Wraps psycopg2 connection to provide sqlite3.Row-like dict access."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        import psycopg2
        import psycopg2.extras
        # Convert ? placeholders to %s for PostgreSQL, but only if they are not already %s
        # and be careful not to break existing %s or other % characters
        if "?" in sql:
            # Simple replacement works for most cases here as we don't use ? inside strings
            sql = sql.replace("?", "%s")
        
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(sql, params)
            return PgResultWrapper(cur)
        except Exception as e:
            cur.close()
            log.error(f"PostgreSQL Execute Error: {e} | SQL: {sql[:200]}...")
            raise

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


class PgResultWrapper:
    """Makes psycopg2 cursor results look like sqlite3 results and ensures closure."""
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        
        # In Postgres, we usually use RETURNING id or lastval()
        if cursor.description:
            try:
                if cursor.statusmessage and cursor.statusmessage.startswith("INSERT"):
                    # This is slightly expensive but keeps logic compatible with sqlite lastrowid
                    self._cursor.execute("SELECT lastval()")
                    row = self._cursor.fetchone()
                    if row:
                        self.lastrowid = list(row.values())[0] if isinstance(row, dict) else row[0]
            except Exception:
                pass

    def fetchone(self):
        try:
            row = self._cursor.fetchone()
            return dict(row) if row else None
        finally:
            # We don't close here because user might fetch multiple times 
            # (though fetchone is usually once)
            pass

    def fetchall(self):
        try:
            rows = self._cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            self._cursor.close()

    def __iter__(self):
        return iter(self.fetchall())


def _safe_int(v):
    if v is None:
        return None
    try:
        if isinstance(v, float) and (v != v):  # NaN
            return None
        return int(v)
    except (TypeError, ValueError):
        return None
# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    """Initialize/migrate the database."""
    if USE_POSTGRES:
        _init_postgres()
    else:
        ensure_dirs()
        
        # --- EMERGENCY DATA RESTORE ---
        # Se estamos no Cloud e o banco atual está vazio, mas temos um migrate_data_local.db
        migration_file = Path("migrate_data_local.db")
        if IS_DOCKER and migration_file.exists():
            try:
                # Verificar se o banco atual realmente está vazio
                conn_test = _sqlite_connect()
                has_data = False
                try:
                    res = conn_test.execute("SELECT COUNT(*) FROM auditorias").fetchone()
                    if res and res[0] > 0:
                        has_data = True
                except: pass
                conn_test.close()
                
                if not has_data:
                    log.info(f"Restoring database from {migration_file} to {DB_PATH}")
                    shutil.copy2(migration_file, DB_PATH)
                    log.info("Restore COMPLETED")
            except Exception as restore_err:
                log.error(f"Failed to restore data: {restore_err}")

        import sys
        parent = str(Path(__file__).resolve().parent.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import database as original_db
        original_db.init_db()
        
        # Seed test user only (never overwrites existing passwords)
        try:
            from backend.auth import get_password_hash
            hashed = get_password_hash("Audit@2026!")
            with get_db() as conn:
                # INSERT OR IGNORE — if user already exists, password is preserved
                conn.execute(
                    "INSERT OR IGNORE INTO users (email, password, role) VALUES (?, ?, ?)",
                    ("teste@automateasy.com.br", hashed, "admin")
                )
                conn.commit()
                log.info("Test user seeded/verified (existing passwords preserved)")
        except Exception as e:
            log.warning(f"Could not seed test user: {e}")

        # --- REPAIR MISSING COLUMNS (v15+) ---
        try:
            with _sqlite_connect() as conn:
                # knowledge_base table — CRITICAL for learning
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        titulo       TEXT    NOT NULL,
                        conteudo     TEXT    NOT NULL,
                        tag          TEXT    DEFAULT 'geral',
                        fonte        TEXT    DEFAULT 'manual',
                        data_criacao TEXT    NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_titulo ON knowledge_base(titulo)")

                # auditorias table migrations
                for col_name, col_type in [("evidence_map", "TEXT DEFAULT '{}'"), 
                                           ("evidence_zip_url", "TEXT DEFAULT ''"),
                                           ("ai_provider", "TEXT DEFAULT ''"),
                                           ("ai_base_url", "TEXT DEFAULT ''"),
                                           ("auditado_por", "TEXT DEFAULT ''"),
                                           ("revisado_por", "TEXT DEFAULT ''")]:
                    try:
                        conn.execute(f"ALTER TABLE auditorias ADD COLUMN {col_name} {col_type}")
                    except sqlite3.OperationalError:
                        pass # already exists
                # aprendizados table migrations
                for col_name, col_type in [("data_criacao", "TEXT DEFAULT ''")]:
                    try:
                        conn.execute(f"ALTER TABLE aprendizados ADD COLUMN {col_name} {col_type}")
                    except sqlite3.OperationalError:
                        pass # already exists
                conn.commit()
                
                # --- NEW CLEANUP FOR SQLITE ---
                # Fix stuck 'openai' providers that should be falling back to global
                conn.execute("UPDATE auditorias SET ai_provider = '' WHERE ai_provider = 'openai' AND (openai_api_key IS NULL OR openai_api_key = '')")
                conn.commit()
                log.info("SQLite defensive cleanup: cleared 'openai' from audits without keys")
        except Exception as repair_err:
            log.warning(f"Failed to perform defensive migration: {repair_err}")

    log.info("Database initialized")


def _init_postgres():
    """Create tables in PostgreSQL if they don't exist."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auditorias (
                id SERIAL PRIMARY KEY,
                unidade TEXT NOT NULL,
                area TEXT NOT NULL,
                ciclo TEXT NOT NULL,
                data_criacao TEXT,
                data_atualizacao TEXT,
                status TEXT DEFAULT 'em_andamento',
                assessment_file_path TEXT DEFAULT '',
                evidence_folder_path TEXT DEFAULT '',
                openai_api_key TEXT DEFAULT '',
                ai_provider TEXT DEFAULT '',
                ai_base_url TEXT DEFAULT '',
                modo_analise TEXT DEFAULT 'completo',
                observacoes TEXT DEFAULT '',
                evidence_map TEXT DEFAULT '{}',
                evidence_zip_url TEXT DEFAULT '',
                auditado_por TEXT DEFAULT '',
                revisado_por TEXT DEFAULT '',
                UNIQUE(unidade, area, ciclo)
            );

            -- Migration: Add evidence_map if it doesn't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='evidence_map') THEN
                    ALTER TABLE auditorias ADD COLUMN evidence_map TEXT DEFAULT '{}';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='evidence_zip_url') THEN
                    ALTER TABLE auditorias ADD COLUMN evidence_zip_url TEXT DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='ai_provider') THEN
                    ALTER TABLE auditorias ADD COLUMN ai_provider TEXT DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='ai_base_url') THEN
                    ALTER TABLE auditorias ADD COLUMN ai_base_url TEXT DEFAULT '';
                END IF;

                -- Ensure defaults are correct even if columns already existed
                ALTER TABLE auditorias ALTER COLUMN ai_provider SET DEFAULT '';
                ALTER TABLE auditorias ALTER COLUMN ai_base_url SET DEFAULT '';

                -- Migration: Add auditado_por and revisado_por columns
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='auditado_por') THEN
                    ALTER TABLE auditorias ADD COLUMN auditado_por TEXT DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='auditorias' AND column_name='revisado_por') THEN
                    ALTER TABLE auditorias ADD COLUMN revisado_por TEXT DEFAULT '';
                END IF;

                -- Backfill auditado_por from audit_log (earliest user per audit)
                UPDATE auditorias SET auditado_por = sub.usuario
                FROM (
                    SELECT DISTINCT ON (auditoria_id) auditoria_id, usuario
                    FROM audit_log
                    WHERE usuario IS NOT NULL AND usuario != '' AND usuario != 'auditor'
                    ORDER BY auditoria_id, timestamp ASC
                ) sub
                WHERE auditorias.id = sub.auditoria_id
                  AND (auditorias.auditado_por IS NULL OR auditorias.auditado_por = '');

                -- Fix stuck 'openai' providers that should be falling back to global
                UPDATE auditorias SET ai_provider = '' WHERE ai_provider = 'openai' AND (openai_api_key IS NULL OR openai_api_key = '');
            END $$;

            CREATE TABLE IF NOT EXISTS avaliacoes (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER REFERENCES auditorias(id) ON DELETE CASCADE,
                pratica_num INTEGER,
                pratica_nome TEXT,
                subitem_idx INTEGER,
                subitem_nome TEXT,
                evidencia_descricao TEXT DEFAULT '',
                nivel_0 TEXT DEFAULT '',
                nivel_1 TEXT DEFAULT '',
                nivel_2 TEXT DEFAULT '',
                nivel_3 TEXT DEFAULT '',
                nivel_4 TEXT DEFAULT '',
                nota_self_assessment INTEGER,
                decisao TEXT DEFAULT 'pendente',
                nota_final INTEGER,
                descricao_nc TEXT DEFAULT '',
                comentarios TEXT DEFAULT '',
                ia_decisao TEXT,
                ia_nota_sugerida INTEGER,
                ia_confianca TEXT,
                ia_pontos_atendidos TEXT,
                ia_pontos_faltantes TEXT,
                ia_analise_detalhada TEXT,
                ia_status TEXT,
                data_atualizacao TEXT
            );

            -- Migration: Add IA columns to avaliacoes if they don't exist
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_decisao') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_decisao TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_nota_sugerida') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_nota_sugerida INTEGER;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_confianca') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_confianca TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_pontos_atendidos') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_pontos_atendidos TEXT DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_pontos_faltantes') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_pontos_faltantes TEXT DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_analise_detalhada') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_analise_detalhada TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='ia_status') THEN
                    ALTER TABLE avaliacoes ADD COLUMN ia_status TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='avaliacoes' AND column_name='data_atualizacao') THEN
                    ALTER TABLE avaliacoes ADD COLUMN data_atualizacao TEXT;
                END IF;

                -- Migration: Add UNIQUE constraint to avaliacoes if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                               WHERE constraint_name='unique_audit_item' AND table_name='avaliacoes') THEN
                    ALTER TABLE avaliacoes ADD CONSTRAINT unique_audit_item UNIQUE (auditoria_id, pratica_num, subitem_idx);
                END IF;
            END $$;

            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TEXT,
                auditoria_id INTEGER,
                pratica_num INTEGER,
                subitem_idx INTEGER,
                campo TEXT,
                valor_antes TEXT,
                valor_depois TEXT,
                usuario TEXT DEFAULT 'auditor'
            );

            CREATE TABLE IF NOT EXISTS chat_revisao (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER,
                pratica_num INTEGER,
                subitem_idx INTEGER,
                timestamp TEXT,
                role TEXT,
                conteudo TEXT,
                decisao_snapshot TEXT,
                nota_snapshot INTEGER,
                confianca_snapshot TEXT
            );

            CREATE TABLE IF NOT EXISTS diario_auditoria (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER,
                data_entrada TEXT,
                tipo TEXT DEFAULT 'observacao',
                titulo TEXT DEFAULT '',
                conteudo TEXT DEFAULT '',
                pratica_ref TEXT DEFAULT '',
                prioridade TEXT DEFAULT 'normal',
                resolvido INTEGER DEFAULT 0,
                data_criacao TEXT,
                data_atualizacao TEXT
            );

            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'auditor'
            );

            CREATE TABLE IF NOT EXISTS aprendizados (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER,
                pratica_num INTEGER,
                subitem_idx INTEGER,
                categoria TEXT,
                descricao TEXT,
                exemplo TEXT,
                data_criacao TEXT
            );

            CREATE TABLE IF NOT EXISTS snapshots_nota (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER,
                pratica_num INTEGER,
                subitem_idx INTEGER,
                timestamp TEXT,
                nota INTEGER,
                origem TEXT
            );

            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            -- Ensure system_config has a Primary Key for ON CONFLICT
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM pg_index i 
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) 
                    WHERE i.indrelid = 'system_config'::regclass AND i.indisprimary
                ) THEN 
                    ALTER TABLE system_config ADD PRIMARY KEY (key); 
                END IF; 
            END $$;

            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                conteudo TEXT,
                tag TEXT DEFAULT 'geral',
                fonte TEXT DEFAULT 'manual',
                data_criacao TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_jobs (
                id TEXT PRIMARY KEY,
                auditoria_id INTEGER,
                tipo TEXT DEFAULT 'single',
                pratica_num INTEGER,
                subitem_idx INTEGER,
                nota_self_assessment INTEGER,
                status TEXT DEFAULT 'pending',
                resultado TEXT,
                erro TEXT,
                progresso TEXT,
                data_criacao TEXT,
                data_conclusao TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log.info("✅ PostgreSQL tables and migrations verified")
    except Exception as e:
        log.error(f"❌ Error in _init_postgres: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

def get_user(email: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

def create_user(email: str, hashed_password: str, role: str = "auditor"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
            (email, hashed_password, role)
        )

# ─────────────────────────────────────────────────────────────────────────────
# CRUD — AUDITORIAS
# ─────────────────────────────────────────────────────────────────────────────

def listar_auditorias() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT  a.*,
                    COUNT(av.id)                               AS total_subitens,
                    SUM(CASE WHEN av.decisao != 'pendente'
                             AND av.decisao IS NOT NULL
                             THEN 1 ELSE 0 END)                AS subitens_avaliados,
                    AVG(CASE WHEN av.nota_final IS NOT NULL
                             THEN CAST(av.nota_final AS FLOAT)
                             ELSE NULL END)                    AS media_nota_final,
                    SUM(CASE WHEN av.ia_status = 'ok'
                             THEN 1 ELSE 0 END)                AS ia_analisados
            FROM    auditorias a
            LEFT JOIN avaliacoes av ON av.auditoria_id = a.id
            GROUP BY a.id, a.unidade, a.area, a.ciclo, a.data_criacao,
                     a.data_atualizacao, a.status, a.assessment_file_path,
                     a.evidence_folder_path, a.openai_api_key, a.observacoes, a.modo_analise,
                     a.ai_provider, a.ai_base_url, a.evidence_map, a.evidence_zip_url,
                     a.auditado_por, a.revisado_por
            ORDER BY a.ciclo DESC, a.unidade, a.area
        """).fetchall()
        return [dict(r) for r in rows]


def get_auditoria(auditoria_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM auditorias WHERE id=?", (auditoria_id,)
        ).fetchone()
        return dict(row) if row else None


def atualizar_status(auditoria_id: int, status: str, usuario: str = None):
    with get_db() as conn:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE auditorias SET status=?, data_atualizacao=? WHERE id=?",
            (status, now, auditoria_id)
        )
        log.info(f"Audit {auditoria_id} status updated to {status} by {usuario or 'system'}")


def deletar_auditoria(auditoria_id: int):
    """Permanently removes an audit and all its evaluations from the database."""
    with get_db() as conn:
        # Evaluations first (FK)
        conn.execute("DELETE FROM avaliacoes WHERE auditoria_id=?", (auditoria_id,))
        # Audit itself
        conn.execute("DELETE FROM auditorias WHERE id=?", (auditoria_id,))
        log.info(f"Audit {auditoria_id} and its evaluations deleted from DB.")


def atualizar_config(auditoria_id: int, assessment_path: str,
                     evidence_folder: str, api_key: str, observacoes: str = None, 
                     modo_analise: str = "completo", evidence_zip_url: str = "",
                     ai_provider: str = "", ai_base_url: str = ""):
    log.info(f"DB: Saving config for audit {auditoria_id}: provider='{ai_provider}', has_key={bool(api_key)}")
    with get_db() as conn:
        now = datetime.now().isoformat()
        if observacoes is not None:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=?, evidence_folder_path=?,
                    openai_api_key=?, data_atualizacao=?, observacoes=?,
                    modo_analise=?, evidence_zip_url=?, ai_provider=?, ai_base_url=?
                WHERE id=?
            """, (assessment_path, evidence_folder, api_key, now, observacoes, modo_analise, evidence_zip_url, ai_provider, ai_base_url, auditoria_id))
        else:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=?, evidence_folder_path=?,
                    openai_api_key=?, data_atualizacao=?, modo_analise=?,
                    evidence_zip_url=?, ai_provider=?, ai_base_url=?
                WHERE id=?
            """, (assessment_path, evidence_folder, api_key, now, modo_analise, evidence_zip_url, ai_provider, ai_base_url, auditoria_id))


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — AVALIAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

def carregar_avaliacoes(auditoria_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM avaliacoes
            WHERE auditoria_id=?
            ORDER BY pratica_num, subitem_idx
        """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]


def get_avaliacao(avaliacao_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM avaliacoes WHERE id=?", (avaliacao_id,)
        ).fetchone()
        return dict(row) if row else None


def salvar_decisao(avaliacao_id: int, decisao: str, nota_final: Optional[int],
                   descricao_nc: str, comentarios: str, usuario: str = "auditor"):
    """Save auditor's manual decision — the core operation."""
    nota_final = _safe_int(nota_final)
    now = datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT decisao, nota_final, auditoria_id, pratica_num, subitem_idx, ia_status, ia_decisao FROM avaliacoes WHERE id=?",
            (avaliacao_id,)
        ).fetchone()
        
        ia_status = row["ia_status"] if row else None
        if row:
            if row["decisao"] != decisao:
                conn.execute("""
                    INSERT INTO audit_log (timestamp, auditoria_id, pratica_num, subitem_idx, campo, valor_antes, valor_depois, usuario)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (now, row["auditoria_id"], row["pratica_num"], row["subitem_idx"],
                      "decisao", row["decisao"], decisao, usuario))
            if row["nota_final"] != nota_final:
                conn.execute("""
                    INSERT INTO audit_log (timestamp, auditoria_id, pratica_num, subitem_idx, campo, valor_antes, valor_depois, usuario)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (now, row["auditoria_id"], row["pratica_num"], row["subitem_idx"],
                      "nota_final", str(row["nota_final"]), str(nota_final), usuario))

        conn.execute("""
            UPDATE avaliacoes
            SET decisao=?, nota_final=?, descricao_nc=?, comentarios=?, data_atualizacao=?
            WHERE id=?
        """, (decisao, nota_final, descricao_nc, comentarios, now, avaliacao_id))

        if row:
            conn.execute(
                "UPDATE auditorias SET data_atualizacao=? WHERE id=?",
                (now, row["auditoria_id"])
            )
            
            # --- RESPONSABILITY TRACKING ---
            # Track who audited and who revised this audit
            if usuario and usuario != "auditor" and decisao != 'pendente':
                aud = conn.execute(
                    "SELECT auditado_por, revisado_por, status FROM auditorias WHERE id=?",
                    (row["auditoria_id"],)
                ).fetchone()
                if aud:
                    auditado_por = (aud["auditado_por"] or "").strip()
                    revisado_por = (aud["revisado_por"] or "").strip()
                    status_aud = aud["status"] or "em_andamento"
                    
                    if not auditado_por:
                        # First person to make a decision is the auditor
                        conn.execute(
                            "UPDATE auditorias SET auditado_por=? WHERE id=?",
                            (usuario, row["auditoria_id"])
                        )
                    elif status_aud in ("concluida", "em_revisao", "aprovada"):
                        # If audit is complete and someone else is modifying, they're a reviewer
                        existing_reviewers = [r.strip() for r in revisado_por.split(",") if r.strip()]
                        if usuario not in existing_reviewers:
                            existing_reviewers.append(usuario)
                            conn.execute(
                                "UPDATE auditorias SET revisado_por=? WHERE id=?",
                                (", ".join(existing_reviewers), row["auditoria_id"])
                            )
            
            # --- AI LEARNING INDEXING ---
            # Indexamos a decisão do auditor na base de conhecimento para que o agente consulte no futuro.
            if decisao != 'pendente':
                titulo_conhecimento = f"REF_DECISAO: Prática {row['pratica_num']} Item {row['subitem_idx']}"
                conteudo_conhecimento = f"Decisão Auditor: {decisao}\nNota Final: {nota_final}\nNC: {descricao_nc}\nComentários: {comentarios}"
                
                # Evitar duplicidade exata no conhecimento recente para o mesmo item
                conn.execute("""
                    DELETE FROM knowledge_base 
                    WHERE titulo = ? AND tag = 'referencia_auditor'
                """, (titulo_conhecimento,))
                
                conn.execute("""
                    INSERT INTO knowledge_base (titulo, conteudo, tag, fonte, data_criacao)
                    VALUES (?, ?, 'referencia_auditor', 'feedback_humano', ?)
                """, (titulo_conhecimento, conteudo_conhecimento, now))


def salvar_analise_ia(avaliacao_id: int, result: dict, nota_sa: int):
    """Save AI analysis result to an evaluation."""
    now = datetime.now().isoformat()
    decisao = result.get("decisao", "insuficiente")
    nota_sugerida = _safe_int(result.get("nota_sugerida"))

    with get_db() as conn:
        conn.execute("""
            UPDATE avaliacoes
            SET ia_decisao=?, ia_nota_sugerida=?, ia_confianca=?,
                ia_pontos_atendidos=?, ia_pontos_faltantes=?,
                ia_analise_detalhada=?, ia_status=?,
                decisao=CASE WHEN decisao='pendente' THEN ? ELSE decisao END,
                nota_final=CASE WHEN decisao='pendente' THEN ? ELSE nota_final END,
                data_atualizacao=?
            WHERE id=?
        """, (
            decisao, nota_sugerida, result.get("confianca"),
            json.dumps(result.get("pontos_atendidos") if isinstance(result.get("pontos_atendidos"), list) else [], ensure_ascii=False),
            json.dumps(result.get("pontos_faltantes") if isinstance(result.get("pontos_faltantes"), list) else [], ensure_ascii=False),
            result.get("analise_detalhada"), "ok",
            decisao, nota_sugerida, now, avaliacao_id
        ))

# ─────────────────────────────────────────────────────────────────────────────
# APRENDIZADO DA IA
# ─────────────────────────────────────────────────────────────────────────────

def salvar_aprendizado(auditoria_id: int, pratica_num: int, subitem_idx: int,
                      categoria: str, descricao: str, exemplo: str = ""):
    """Insere um novo aprendizado no banco para uso futuro da IA."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO aprendizados (auditoria_id, pratica_num, subitem_idx, categoria, descricao, exemplo, data_criacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (auditoria_id, pratica_num, subitem_idx, categoria, descricao, exemplo, now))

def listar_aprendizados(pratica_num: Optional[int] = None, subitem_idx: Optional[int] = None) -> list[dict]:
    """Retorna os aprendizados registrados, permitindo filtrar por subitem."""
    with get_db() as conn:
        if pratica_num is not None and subitem_idx is not None:
            rows = conn.execute("""
                SELECT * FROM aprendizados 
                WHERE pratica_num=? AND subitem_idx=? 
                ORDER BY data_criacao DESC LIMIT 10
            """, (pratica_num, subitem_idx)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM aprendizados 
                ORDER BY data_criacao DESC LIMIT 100
            """).fetchall()
        return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────────────────────────
# CHAT REVISÃO
# ─────────────────────────────────────────────────────────────────────────────

def carregar_chat(auditoria_id: int, pratica_num: int, subitem_idx: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM chat_revisao
            WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
            ORDER BY timestamp ASC
        """, (auditoria_id, pratica_num, subitem_idx)).fetchall()
        return [dict(r) for r in rows]


def salvar_mensagem_chat(auditoria_id: int, pratica_num: int, subitem_idx: int,
                         role: str, conteudo: str,
                         decisao_snapshot: str = None, nota_snapshot: int = None,
                         confianca_snapshot: str = None):
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO chat_revisao
                (auditoria_id, pratica_num, subitem_idx, timestamp, role, conteudo,
                 decisao_snapshot, nota_snapshot, confianca_snapshot)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (auditoria_id, pratica_num, subitem_idx, now, role, conteudo,
              decisao_snapshot, nota_snapshot, confianca_snapshot))


# ─────────────────────────────────────────────────────────────────────────────
# ESTATÍSTICAS
# ─────────────────────────────────────────────────────────────────────────────

def estatisticas_auditoria(auditoria_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                                                AS total,
                SUM(CASE WHEN decisao != 'pendente' AND decisao IS NOT NULL THEN 1 ELSE 0 END) AS avaliados,
                SUM(CASE WHEN ia_status = 'ok' THEN 1 ELSE 0 END)      AS ia_ok,
                AVG(CASE WHEN nota_final IS NOT NULL AND nota_final != '' THEN CAST(nota_final AS FLOAT) END) AS media_final,
                AVG(CASE WHEN nota_self_assessment IS NOT NULL AND nota_self_assessment != '' THEN CAST(nota_self_assessment AS FLOAT) END) AS media_sa
            FROM avaliacoes WHERE auditoria_id=?
        """, (auditoria_id,)).fetchone()
        return dict(row) if row else {}


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP (SQLite only)
# ─────────────────────────────────────────────────────────────────────────────

def fazer_backup(motivo: str = "auto") -> Optional[str]:
    if USE_POSTGRES:
        log.info("Backup skipped — PostgreSQL uses its own backup strategy")
        return None
    if not DB_PATH.exists():
        return None
    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"auditoria_ta_{motivo}_{ts}.db"
    shutil.copy2(DB_PATH, dest)
    backups = sorted(BACKUP_DIR.glob("auditoria_ta_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > MAX_BACKUPS:
        backups.pop(0).unlink()
    return str(dest)


# ─────────────────────────────────────────────────────────────────────────────
# EXCLUIR AUDITORIA
# ─────────────────────────────────────────────────────────────────────────────

def excluir_auditoria(auditoria_id: int):
    """Remove auditoria e todas as avaliações associadas (CASCADE)."""
    fazer_backup(motivo="pre_delete")
    with get_db() as conn:
        conn.execute("DELETE FROM auditorias WHERE id=?", (auditoria_id,))


# ─────────────────────────────────────────────────────────────────────────────
# DUPLICAR AUDITORIA (NOVO CICLO)
# ─────────────────────────────────────────────────────────────────────────────

def duplicar_auditoria(auditoria_id: int, novo_ciclo: str) -> Optional[int]:
    """
    Duplica uma auditoria para um novo ciclo.
    Copia a estrutura (práticas/subitens/notas SA) SEM decisões nem análises IA.
    Retorna o ID da nova auditoria.
    """
    with get_db() as conn:
        origem = conn.execute(
            "SELECT * FROM auditorias WHERE id=?", (auditoria_id,)
        ).fetchone()
        if not origem:
            return None
        origem = dict(origem)

        now = datetime.now().isoformat()
        # Verificar se já existe
        existing = conn.execute(
            "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
            (origem["unidade"], origem["area"], novo_ciclo)
        ).fetchone()
        if existing:
            return dict(existing)["id"]

        # Criar nova auditoria
        result = conn.execute("""
            INSERT INTO auditorias
                (unidade, area, ciclo, data_criacao, data_atualizacao,
                 status, assessment_file_path, evidence_folder_path,
                 openai_api_key, observacoes)
            VALUES (?,?,?,?,?,'em_andamento',?,?,?,?)
        """, (
            origem["unidade"], origem["area"], novo_ciclo,
            now, now,
            origem.get("assessment_file_path") or "",
            origem.get("evidence_folder_path") or "",
            origem.get("openai_api_key") or "",
            f"Ciclo duplicado de {origem['ciclo']}"
        ))

        novo_row = conn.execute(
            "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
            (origem["unidade"], origem["area"], novo_ciclo)
        ).fetchone()
        if not novo_row:
            return None
        novo_id = dict(novo_row)["id"]

        # Copiar avaliações (apenas estrutura, zerando decisões e IA)
        avaliacoes = conn.execute(
            "SELECT * FROM avaliacoes WHERE auditoria_id=?", (auditoria_id,)
        ).fetchall()
        for av in avaliacoes:
            av = dict(av)
            try:
                conn.execute("""
                    INSERT INTO avaliacoes
                        (auditoria_id, pratica_num, pratica_nome,
                         subitem_idx, subitem_nome, evidencia_descricao,
                         nivel_0, nivel_1, nivel_2, nivel_3, nivel_4,
                         nota_self_assessment, decisao)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'pendente')
                """, (
                    novo_id,
                    av["pratica_num"], av["pratica_nome"],
                    av["subitem_idx"], av["subitem_nome"],
                    av.get("evidencia_descricao", ""),
                    av.get("nivel_0", ""), av.get("nivel_1", ""),
                    av.get("nivel_2", ""), av.get("nivel_3", ""),
                    av.get("nivel_4", ""),
                    av.get("nota_self_assessment"),
                ))
            except Exception:
                pass

        # Registrar no audit log
        conn.execute("""
            INSERT INTO audit_log (timestamp, auditoria_id, pratica_num, subitem_idx, campo, valor_antes, valor_depois, usuario)
            VALUES (?,?,?,?,?,?,?,?)
        """, (now, novo_id, None, None, "auditoria_criada",
              None, f"Duplicado de ID={auditoria_id} ciclo={origem['ciclo']}", "sistema"))

        return novo_id


# ─────────────────────────────────────────────────────────────────────────────
# COMPARATIVO ENTRE CICLOS
# ─────────────────────────────────────────────────────────────────────────────

def comparativo_ciclos(auditoria_id_a: int, auditoria_id_b: int) -> list[dict]:
    """
    Compara nota_final de dois ciclos, calculando delta e tendência.
    Retorna lista de dicts com pratica, subitem, nota_a, nota_b, delta, tendencia.
    """
    with get_db() as conn:
        rows_a = conn.execute("""
            SELECT pratica_num, pratica_nome, subitem_idx, subitem_nome,
                   nota_final AS nota_a, decisao AS decisao_a
            FROM avaliacoes WHERE auditoria_id=?
            ORDER BY pratica_num, subitem_idx
        """, (auditoria_id_a,)).fetchall()

        rows_b_raw = conn.execute("""
            SELECT pratica_num, subitem_idx,
                   nota_final AS nota_b, decisao AS decisao_b
            FROM avaliacoes WHERE auditoria_id=?
        """, (auditoria_id_b,)).fetchall()

    # Index B by (pratica_num, subitem_idx)
    b_map = {}
    for r in rows_b_raw:
        r = dict(r)
        b_map[(r["pratica_num"], r["subitem_idx"])] = r

    result = []
    for row in rows_a:
        row = dict(row)
        key = (row["pratica_num"], row["subitem_idx"])
        b = b_map.get(key, {})
        nota_a = row.get("nota_a")
        nota_b = b.get("nota_b")
        delta = None
        tendencia = "—"
        if nota_a is not None and nota_b is not None:
            try:
                delta = int(nota_b) - int(nota_a)
                if delta > 0:
                    tendencia = "⬆️ Melhora"
                elif delta < 0:
                    tendencia = "⬇️ Piora"
                else:
                    tendencia = "➡️ Igual"
            except (TypeError, ValueError):
                pass
        result.append({
            "pratica_num": row["pratica_num"],
            "pratica_nome": row.get("pratica_nome", ""),
            "subitem_idx": row["subitem_idx"],
            "subitem_nome": row.get("subitem_nome", ""),
            "nota_a": nota_a,
            "nota_b": nota_b,
            "decisao_a": row.get("decisao_a", ""),
            "decisao_b": b.get("decisao_b", ""),
            "delta": delta,
            "tendencia": tendencia,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────────────────────────────────────

def carregar_audit_log(auditoria_id: int = None, limit: int = 200) -> list[dict]:
    """Retorna os últimos N registros do audit_log."""
    with get_db() as conn:
        if auditoria_id:
            rows = conn.execute("""
                SELECT * FROM audit_log
                WHERE auditoria_id=?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (auditoria_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def set_system_config(key: str, value: str):
    """Saves or updates a global system configuration value."""
    with get_db() as conn:
        if USE_POSTGRES:
            conn.execute("""
                INSERT INTO system_config (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """, (key, value))
        else:
            conn.execute("""
                INSERT INTO system_config (key, value)
                VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """, (key, value))

def get_system_config(key: str, default: str = "") -> str:
    """Retrieves a global system configuration value."""
    with get_db() as conn:
        try:
            if USE_POSTGRES:
                row = conn.execute("SELECT value FROM system_config WHERE key = %s", (key,)).fetchone()
            else:
                row = conn.execute("SELECT value FROM system_config WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
        except Exception:
            return default

def delete_vercel_blobs(urls: list[str]):
    """Delete blobs from Vercel Storage using the BLOB_READ_WRITE_TOKEN."""
    if not urls:
        return
        
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        log.warning("BLOB_READ_WRITE_TOKEN not found. Skipping blob deletion.")
        return
        
    try:
        import json
        import urllib.request
        
        # Vercel Blob API for deletion
        api_url = "https://blob.vercel-storage.com/delete"
        data = json.dumps({"urls": [u for u in urls if u and u.startswith("http")]}).encode("utf-8")
        
        req = urllib.request.Request(
            api_url, 
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            log.info(f"Vercel Blobs deleted. Count: {len(urls)}")
    except Exception as e:
        log.error(f"Failed to delete Vercel Blobs: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE (Base de Conhecimento)
# ─────────────────────────────────────────────────────────────────────────────

def listar_conhecimento(tag: str = None) -> list[dict]:
    """Retorna snippets da base de conhecimento."""
    with get_db() as conn:
        if tag:
            rows = conn.execute("SELECT * FROM knowledge_base WHERE tag=? ORDER BY data_criacao DESC", (tag,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM knowledge_base ORDER BY data_criacao DESC").fetchall()
        return [dict(r) for r in rows]

def adicionar_conhecimento(titulo: str, conteudo: str, tag: str = "geral", fonte: str = "manual"):
    """Adiciona um novo snippet de conhecimento."""
    with get_db() as conn:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO knowledge_base (titulo, conteudo, tag, fonte, data_criacao)
            VALUES (?, ?, ?, ?, ?)
        """, (titulo, conteudo, tag, fonte, now))

def buscar_contexto_relevante(query: str, limit: int = 3) -> str:
    """
    Busca simplificada (por palavra-chave no título) para compor contexto.
    Em uma versão futura, isso usaria embeddings (Vector Search).
    """
    try:
        with get_db() as conn:
            # Busca simples por LIKE no título ou conteúdo
            rows = conn.execute("""
                SELECT conteudo FROM knowledge_base
                WHERE titulo LIKE ? OR conteudo LIKE ?
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
            
            ctx = [str(r["conteudo"]) for r in rows if r["conteudo"] is not None]
            return "\n\n---\n\n".join(ctx) if ctx else ""
    except Exception as e:
        log.error(f"Erro ao buscar contexto RAG para '{query}': {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# AGENT JOBS
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_agent_jobs_table():
    """Create agent_jobs table if it doesn't exist (SQLite)."""
    if USE_POSTGRES:
        return  # Already handled in _init_postgres
    try:
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_jobs (
                    id TEXT PRIMARY KEY,
                    auditoria_id INTEGER,
                    tipo TEXT DEFAULT 'single',
                    pratica_num INTEGER,
                    subitem_idx INTEGER,
                    nota_self_assessment INTEGER,
                    status TEXT DEFAULT 'pending',
                    resultado TEXT,
                    erro TEXT,
                    progresso TEXT,
                    data_criacao TEXT,
                    data_conclusao TEXT
                )
            """)
            conn.commit()
    except Exception as e:
        log.warning(f"Could not create agent_jobs table: {e}")


def criar_agent_job(job_id: str, auditoria_id: int, tipo: str = "single",
                    pratica_num: int = None, subitem_idx: int = None,
                    nota_self_assessment: int = None):
    """Create a new agent job record."""
    _ensure_agent_jobs_table()
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agent_jobs (id, auditoria_id, tipo, pratica_num, subitem_idx,
                                    nota_self_assessment, status, data_criacao)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (job_id, auditoria_id, tipo, pratica_num, subitem_idx,
              nota_self_assessment, now))


def atualizar_agent_job(job_id: str, status: str, resultado: str = None,
                        erro: str = None, progresso: str = None):
    """Update an agent job's status and result."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            UPDATE agent_jobs
            SET status=?, resultado=COALESCE(?, resultado),
                erro=COALESCE(?, erro), progresso=COALESCE(?, progresso),
                data_conclusao=CASE WHEN ?='done' OR ?='error' THEN ? ELSE data_conclusao END
            WHERE id=?
        """, (status, resultado, erro, progresso, status, status, now, job_id))


def get_agent_job(job_id: str) -> Optional[dict]:
    """Get a single agent job by ID."""
    _ensure_agent_jobs_table()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM agent_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None


def listar_agent_jobs(auditoria_id: int = None, limit: int = 50) -> list:
    """List agent jobs, optionally filtered by audit."""
    _ensure_agent_jobs_table()
    with get_db() as conn:
        if auditoria_id:
            rows = conn.execute(
                "SELECT * FROM agent_jobs WHERE auditoria_id=? ORDER BY data_criacao DESC LIMIT ?",
                (auditoria_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agent_jobs ORDER BY data_criacao DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
