"""
database.py — Camada de acesso a dados do Sistema de Auditoria TA
=================================================================
Responsabilidades:
  • Localização permanente do banco (C:\\AuditoriaTA\\dados\\)
  • Migrações incrementais de schema (sem perda de dados)
  • Backup automático com rotação (mantém últimos 30)
  • CRUD de auditorias e avaliações
  • Histórico de alterações (audit log)
  • Duplicar auditoria (novo ciclo baseado em ciclo anterior)
  • Comparativo entre ciclos
  • Exportação / importação do banco completo
"""

import sqlite3
import shutil
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE CAMINHOS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(r"C:\AuditoriaTA")
DADOS_DIR  = BASE_DIR / "dados"
BACKUP_DIR = BASE_DIR / "dados" / "backups"

# Fallback para ambientes de desenvolvimento (Linux/Mac/sandbox)
if not BASE_DIR.drive:
    BASE_DIR   = Path.home() / "AuditoriaTA"
    DADOS_DIR  = BASE_DIR / "dados"
    BACKUP_DIR = BASE_DIR / "dados" / "backups"

DB_PATH = DADOS_DIR / "auditoria_ta.db"

# Schema version atual — incrementar a cada migração adicionada
SCHEMA_VERSION = 13

log = logging.getLogger("auditoria_db")

# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS DE CONEXÃO
# ─────────────────────────────────────────────────────────────────────────────

def ensure_dirs():
    """Garante que as pastas de dados e backup existam."""
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_db(path: Path = None) -> sqlite3.Connection:
    """Abre conexão com WAL mode e foreign keys habilitados."""
    p = str(path or DB_PATH)
    conn = sqlite3.connect(p, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# SISTEMA DE MIGRAÇÕES INCREMENTAIS
# ─────────────────────────────────────────────────────────────────────────────

MIGRATIONS = {}  # version -> callable(conn)


def migration(version: int):
    """Decorator para registrar migrações."""
    def decorator(fn):
        MIGRATIONS[version] = fn
        return fn
    return decorator


@migration(1)
def _m1_schema_base(conn):
    """Schema base: tabelas auditorias e avaliacoes."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS auditorias (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        unidade              TEXT    NOT NULL,
        area                 TEXT    NOT NULL,
        ciclo                TEXT    NOT NULL,
        data_criacao         TEXT    NOT NULL,
        data_atualizacao     TEXT    NOT NULL,
        status               TEXT    DEFAULT 'em_andamento',
        assessment_file_path TEXT,
        evidence_folder_path TEXT,
        openai_api_key       TEXT,
        observacoes          TEXT,
        UNIQUE(unidade, area, ciclo)
    );

    CREATE TABLE IF NOT EXISTS avaliacoes (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        auditoria_id          INTEGER NOT NULL,
        pratica_num           INTEGER,
        pratica_nome          TEXT,
        subitem_idx           INTEGER,
        subitem_nome          TEXT,
        evidencia_descricao   TEXT,
        nivel_0               TEXT,
        nivel_1               TEXT,
        nivel_2               TEXT,
        nivel_3               TEXT,
        nivel_4               TEXT,
        nota_self_assessment  INTEGER,
        decisao               TEXT    DEFAULT 'pendente',
        nota_final            INTEGER,
        descricao_nc          TEXT,
        comentarios           TEXT,
        ia_decisao            TEXT,
        ia_nota_sugerida      INTEGER,
        ia_confianca          TEXT,
        ia_pontos_atendidos   TEXT,
        ia_pontos_faltantes   TEXT,
        ia_analise_detalhada  TEXT,
        ia_status             TEXT,
        FOREIGN KEY (auditoria_id) REFERENCES auditorias(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_aval_auditoria ON avaliacoes(auditoria_id);
    CREATE INDEX IF NOT EXISTS idx_aval_pratica   ON avaliacoes(auditoria_id, pratica_num);
    """)


@migration(2)
def _m2_schema_version(conn):
    """Tabela de controle de versão do schema."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version      INTEGER PRIMARY KEY,
        aplicado_em  TEXT    NOT NULL,
        descricao    TEXT
    );
    """)


@migration(3)
def _m3_audit_log(conn):
    """Log de alterações: rastreia quem/quando alterou cada avaliação."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp    TEXT    NOT NULL,
        auditoria_id INTEGER,
        pratica_num  INTEGER,
        subitem_idx  INTEGER,
        campo        TEXT,
        valor_antes  TEXT,
        valor_depois TEXT,
        usuario      TEXT    DEFAULT 'sistema'
    );
    CREATE INDEX IF NOT EXISTS idx_log_auditoria ON audit_log(auditoria_id);
    CREATE INDEX IF NOT EXISTS idx_log_ts        ON audit_log(timestamp);
    """)




@migration(5)
def _m5_chat_revisao(conn):
    """Tabela de histórico de revisão colaborativa humano-IA por subitem."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS chat_revisao (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        auditoria_id    INTEGER NOT NULL,
        pratica_num     INTEGER NOT NULL,
        subitem_idx     INTEGER NOT NULL,
        timestamp       TEXT    NOT NULL,
        role            TEXT    NOT NULL,
        conteudo        TEXT    NOT NULL,
        decisao_snapshot     TEXT,
        nota_snapshot        INTEGER,
        confianca_snapshot   TEXT,
        FOREIGN KEY (auditoria_id) REFERENCES auditorias(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chat_sub
        ON chat_revisao(auditoria_id, pratica_num, subitem_idx);
    """)


@migration(6)
def _m6_aprendizados(conn):
    """Tabela de aprendizado por revisão colaborativa (exemplos few-shot)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS aprendizados (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pratica_num     INTEGER NOT NULL,
            subitem_idx     INTEGER NOT NULL,
            pratica_nome    TEXT,
            subitem_nome    TEXT,
            unidade         TEXT,
            area            TEXT,
            ciclo           TEXT,
            nota_sa         INTEGER,
            nota_ia_inicial INTEGER,
            decisao_ia_inicial TEXT,
            observacao_auditor TEXT,
            decisao_consenso   TEXT,
            nota_consenso      INTEGER,
            justificativa      TEXT,
            data_registro   TEXT DEFAULT (datetime('now'))
        )
    """)
    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aprendizados_pratica
            ON aprendizados(pratica_num, subitem_idx);
        """)
    except Exception:
        pass
    conn.commit()


@migration(4)
def _m4_notas_historico(conn):
    """Tabela de snapshots de notas para comparativo entre ciclos."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS snapshots_nota (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        auditoria_id INTEGER NOT NULL,
        pratica_num  INTEGER,
        subitem_idx  INTEGER,
        nota_final   INTEGER,
        decisao      TEXT,
        capturado_em TEXT    NOT NULL,
        FOREIGN KEY (auditoria_id) REFERENCES auditorias(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_snap_aud ON snapshots_nota(auditoria_id);

    -- Adicionar coluna 'observacoes' em auditorias (caso ainda não exista)
    -- SQLite não tem IF NOT EXISTS em ALTER TABLE, então usamos try/except via Python
    """)
    # Adicionar colunas extras em auditorias sem quebrar se já existirem
    for col_def in [
        "ALTER TABLE auditorias ADD COLUMN observacoes TEXT",
        "ALTER TABLE avaliacoes ADD COLUMN data_atualizacao TEXT",
    ]:
        try:
            conn.execute(col_def)
        except sqlite3.OperationalError:
            pass  # coluna já existe — ok


@migration(10)
def _m10_ai_provider_config(conn):
    """Adiciona campos de provedor de AI e base URL em auditorias."""
    for col_def in [
        "ALTER TABLE auditorias ADD COLUMN ai_provider TEXT DEFAULT 'openai'",
        "ALTER TABLE auditorias ADD COLUMN ai_base_url TEXT",
        "ALTER TABLE auditorias ADD COLUMN modo_analise TEXT DEFAULT 'completo'",
    ]:
        try:
            conn.execute(col_def)
        except sqlite3.OperationalError:
            pass  # coluna já existe


@migration(7)
def _m7_diario_auditoria(conn):
    """Tabela de diário/notas de auditoria por auditoria_id."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diario_auditoria (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id    INTEGER NOT NULL,
            data_entrada    TEXT    NOT NULL,
            tipo            TEXT    DEFAULT 'observacao',
            titulo          TEXT,
            conteudo        TEXT    NOT NULL,
            pratica_ref     TEXT,
            prioridade      TEXT    DEFAULT 'normal',
            resolvido       INTEGER DEFAULT 0,
            data_criacao    TEXT    NOT NULL,
            data_atualizacao TEXT   NOT NULL
        );
    """)
    conn.commit()
@migration(8)
def _m8_modo_analise(conn):
    """Adiciona coluna modo_analise em auditorias."""
    try:
        conn.execute("ALTER TABLE auditorias ADD COLUMN modo_analise TEXT DEFAULT 'completo'")
    except sqlite3.OperationalError:
        pass
    conn.commit()

@migration(9)
def _m9_system_config(conn):
    """Cria tabela de configurações globais do sistema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

@migration(11)
def _m11_knowledge_base(conn):
    """Cria tabela de base de conhecimento local (RAG)."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo       TEXT    NOT NULL,
        conteudo     TEXT    NOT NULL,
        tag          TEXT    DEFAULT 'geral',
        fonte        TEXT    DEFAULT 'manual',
        data_criacao TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_kb_titulo ON knowledge_base(titulo);
    """)
    conn.commit()

@migration(12)
def _m12_system_config_v2(conn):
    """Garante que a tabela system_config exista (idempotente)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

def _get_schema_version(conn) -> int:
    """Retorna versão atual do banco (0 se não inicializado)."""
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        # tabela schema_version ainda não existe
        try:
            conn.execute("SELECT 1 FROM auditorias LIMIT 1")
            return 1  # banco antigo sem controle de versão
        except sqlite3.OperationalError:
            return 0  # banco vazio


def init_db():
    """
    Inicializa / migra o banco para a versão mais recente.
    Seguro para chamar múltiplas vezes (idempotente).
    """
    ensure_dirs()
    conn = get_db()
    try:
        current = _get_schema_version(conn)
        for ver in sorted(MIGRATIONS):
            if ver > current:
                log.info(f"Aplicando migração v{ver}...")
                MIGRATIONS[ver](conn)
                # Registrar versão (a tabela schema_version existe a partir de v2)
                if ver >= 2:
                    conn.execute(
                        "INSERT OR REPLACE INTO schema_version(version, aplicado_em, descricao) VALUES (?,?,?)",
                        (ver, datetime.now().isoformat(), MIGRATIONS[ver].__doc__)
                    )
                conn.commit()
        # ── Proteção defensiva: garantir tabelas críticas mesmo em BDs migrados ──
        _ensure_critical_tables(conn)
        return True
    except Exception as e:
        conn.rollback()
        log.error(f"Erro ao inicializar banco: {e}")
        raise
    finally:
        conn.close()


def _ensure_critical_tables(conn):
    """
    Garante que tabelas críticas existam, independente da versão do banco.
    Seguro para chamar em qualquer estado do banco (idempotente via IF NOT EXISTS).
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chat_revisao (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id    INTEGER NOT NULL,
            pratica_num     INTEGER NOT NULL,
            subitem_idx     INTEGER NOT NULL,
            timestamp       TEXT    NOT NULL,
            role            TEXT    NOT NULL,
            conteudo        TEXT    NOT NULL,
            decisao_snapshot     TEXT,
            nota_snapshot        INTEGER,
            confianca_snapshot   TEXT,
            FOREIGN KEY (auditoria_id) REFERENCES auditorias(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_chat_sub
            ON chat_revisao(auditoria_id, pratica_num, subitem_idx);

        CREATE TABLE IF NOT EXISTS aprendizados (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pratica_num     INTEGER NOT NULL,
            subitem_idx     INTEGER NOT NULL,
            pratica_nome    TEXT,
            subitem_nome    TEXT,
            unidade         TEXT,
            area            TEXT,
            ciclo           TEXT,
            nota_sa         INTEGER,
            nota_ia_inicial INTEGER,
            decisao_ia_inicial TEXT,
            observacao_auditor TEXT,
            decisao_consenso   TEXT,
            nota_consenso      INTEGER,
            justificativa      TEXT,
            data_registro   TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_aprendizados_pratica
            ON aprendizados(pratica_num, subitem_idx);
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP AUTOMÁTICO
# ─────────────────────────────────────────────────────────────────────────────

MAX_BACKUPS = 30  # manter últimos N backups


def fazer_backup(motivo: str = "auto") -> Path | None:
    """
    Cria uma cópia do banco com timestamp no nome.
    Mantém apenas os últimos MAX_BACKUPS arquivos.
    Retorna o caminho do backup criado, ou None se DB não existir.
    """
    if not DB_PATH.exists():
        return None
    ensure_dirs()
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"auditoria_ta_{motivo}_{ts}.db"
    shutil.copy2(DB_PATH, dest)

    # Rotação: remover backups mais antigos
    backups = sorted(BACKUP_DIR.glob("auditoria_ta_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > MAX_BACKUPS:
        backups.pop(0).unlink()

    return dest


def listar_backups() -> list[dict]:
    """Retorna lista de backups disponíveis (mais recente primeiro)."""
    if not BACKUP_DIR.exists():
        return []
    arquivos = sorted(
        BACKUP_DIR.glob("auditoria_ta_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    result = []
    for p in arquivos:
        stat  = p.stat()
        parts = p.stem.split("_")
        # Tentar extrair data/hora do nome
        try:
            data_str  = parts[-2]  # YYYYMMDD
            hora_str  = parts[-1]  # HHMMSS
            dt = datetime.strptime(f"{data_str}_{hora_str}", "%Y%m%d_%H%M%S")
            data_fmt = dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            data_fmt = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
        motivo = "_".join(parts[2:-2]) if len(parts) > 4 else "auto"
        result.append({
            "path":   p,
            "nome":   p.name,
            "data":   data_fmt,
            "motivo": motivo,
            "tamanho_kb": round(stat.st_size / 1024, 1),
        })
    return result


def restaurar_backup(backup_path: Path) -> bool:
    """
    Restaura o banco a partir de um backup.
    Faz um backup do banco atual antes de restaurar.
    """
    if not Path(backup_path).exists():
        return False
    fazer_backup(motivo="pre_restore")
    shutil.copy2(backup_path, DB_PATH)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — AUDITORIAS
# ─────────────────────────────────────────────────────────────────────────────

def listar_auditorias() -> pd.DataFrame:
    """Retorna todas as auditorias, com contagem de itens avaliados."""
    conn = get_db()
    try:
        df = pd.read_sql_query("""
            SELECT  a.*,
                    COUNT(av.id)                               AS total_subitens,
                    SUM(CASE WHEN av.decisao != 'pendente'
                             AND av.decisao IS NOT NULL
                             THEN 1 ELSE 0 END)                AS subitens_avaliados,
                    AVG(CASE WHEN av.nota_final IS NOT NULL
                             THEN CAST(av.nota_final AS REAL)
                             ELSE NULL END)                    AS media_nota_final,
                    SUM(CASE WHEN av.ia_status = 'ok'
                             THEN 1 ELSE 0 END)                AS ia_analisados
            FROM    auditorias a
            LEFT JOIN avaliacoes av ON av.auditoria_id = a.id
            GROUP BY a.id
            ORDER BY a.ciclo DESC, a.unidade, a.area
        """, conn)
        return df
    finally:
        conn.close()


def criar_auditoria(unidade: str, area: str, ciclo: str,
                    assessment_path: str = "", evidence_folder: str = "",
                    api_key: str = "", observacoes: str = "",
                    modo_analise: str = "completo") -> int | None:
    """
    Cria nova auditoria. Se já existir (unidade+area+ciclo), retorna o ID existente.
    """
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO auditorias
                (unidade, area, ciclo, data_criacao, data_atualizacao,
                 status, assessment_file_path, evidence_folder_path,
                 openai_api_key, observacoes, modo_analise)
            VALUES (?,?,?,?,?,'em_andamento',?,?,?,?,?)
        """, (unidade, area, ciclo, now, now,
              assessment_path, evidence_folder, api_key, observacoes, modo_analise))
        conn.commit()
        return conn.execute(
            "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
            (unidade, area, ciclo)
        ).fetchone()["id"]
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
            (unidade, area, ciclo)
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def get_auditoria(auditoria_id: int) -> dict | None:
    """Retorna dicionário com todos os campos de uma auditoria."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM auditorias WHERE id=?", (auditoria_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def atualizar_config(auditoria_id: int, assessment_path: str,
                     evidence_folder: str, api_key: str,
                     observacoes: str = None, modo_analise: str = "completo"):
    """Atualiza caminhos e chave de API de uma auditoria."""
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        if observacoes is not None:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=?, evidence_folder_path=?,
                    openai_api_key=?, data_atualizacao=?, observacoes=?,
                    modo_analise=?
                WHERE id=?
            """, (assessment_path, evidence_folder, api_key, now, observacoes, modo_analise, auditoria_id))
        else:
            conn.execute("""
                UPDATE auditorias
                SET assessment_file_path=?, evidence_folder_path=?,
                    openai_api_key=?, data_atualizacao=?, modo_analise=?
                WHERE id=?
            """, (assessment_path, evidence_folder, api_key, now, modo_analise, auditoria_id))
        conn.commit()
    finally:
        conn.close()


def atualizar_status(auditoria_id: int, status: str, observacao: str = None):
    """Atualiza status: 'em_andamento' | 'concluida' | 'em_revisao' | 'aprovada' | 'arquivada'."""
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        if observacao is not None:
            conn.execute(
                "UPDATE auditorias SET status=?, data_atualizacao=?, observacoes=? WHERE id=?",
                (status, now, observacao, auditoria_id)
            )
        else:
            conn.execute(
                "UPDATE auditorias SET status=?, data_atualizacao=? WHERE id=?",
                (status, now, auditoria_id)
            )
        conn.commit()
    finally:
        conn.close()


def excluir_auditoria(auditoria_id: int):
    """Remove auditoria e todas as avaliações (CASCADE)."""
    fazer_backup(motivo="pre_delete")
    conn = get_db()
    try:
        conn.execute("DELETE FROM auditorias WHERE id=?", (auditoria_id,))
        conn.commit()
    finally:
        conn.close()


def duplicar_auditoria(auditoria_id: int, novo_ciclo: str) -> int | None:
    """
    Cria uma cópia de uma auditoria para um novo ciclo.
    Copia a estrutura (práticas/subitens/notas SA) SEM decisões nem análises IA.
    Útil para iniciar auditoria de 2026 com base em 2025.
    Retorna o ID da nova auditoria.
    """
    conn = get_db()
    try:
        origem = conn.execute(
            "SELECT * FROM auditorias WHERE id=?", (auditoria_id,)
        ).fetchone()
        if not origem:
            return None

        now = datetime.now().isoformat()
        # Criar nova auditoria
        try:
            conn.execute("""
                INSERT INTO auditorias
                    (unidade, area, ciclo, data_criacao, data_atualizacao,
                     status, assessment_file_path, evidence_folder_path,
                     openai_api_key, observacoes, modo_analise)
                VALUES (?,?,?,?,?,'em_andamento',?,?,?,?,?)
            """, (
                origem["unidade"], origem["area"], novo_ciclo,
                now, now,
                origem["assessment_file_path"] or "",
                origem["evidence_folder_path"] or "",
                origem["openai_api_key"] or "",
                f"Ciclo duplicado de {origem['ciclo']}",
                origem.get("modo_analise", "completo")
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # já existe

        novo_id_row = conn.execute(
            "SELECT id FROM auditorias WHERE unidade=? AND area=? AND ciclo=?",
            (origem["unidade"], origem["area"], novo_ciclo)
        ).fetchone()
        if not novo_id_row:
            return None
        novo_id = novo_id_row["id"]

        # Copiar avaliações (apenas estrutura, zerando decisões e IA)
        avaliacoes = conn.execute(
            "SELECT * FROM avaliacoes WHERE auditoria_id=?", (auditoria_id,)
        ).fetchall()
        for av in avaliacoes:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO avaliacoes
                        (auditoria_id, pratica_num, pratica_nome,
                         subitem_idx, subitem_nome, evidencia_descricao,
                         nivel_0, nivel_1, nivel_2, nivel_3, nivel_4,
                         nota_self_assessment,
                         decisao, nota_final, descricao_nc, comentarios,
                         ia_decisao, ia_nota_sugerida, ia_confianca,
                         ia_pontos_atendidos, ia_pontos_faltantes,
                         ia_analise_detalhada, ia_status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pendente',NULL,'','',
                            NULL,NULL,NULL,NULL,NULL,NULL,NULL)
                """, (
                    novo_id,
                    av["pratica_num"], av["pratica_nome"],
                    av["subitem_idx"],  av["subitem_nome"],
                    av["evidencia_descricao"],
                    av["nivel_0"], av["nivel_1"], av["nivel_2"],
                    av["nivel_3"], av["nivel_4"],
                    av["nota_self_assessment"],
                ))
            except Exception:
                pass
        conn.commit()

        # Registrar no audit log
        _registrar_log(conn, novo_id, None, None, "auditoria_criada",
                       None, f"Duplicado de ID={auditoria_id} ciclo={origem['ciclo']}")
        conn.commit()
        return novo_id
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# CRUD — AVALIAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(v):
    """Converte para int nativo Python, retorna None se inválido."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and (v != v):  # NaN
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def salvar_avaliacao(auditoria_id, pratica_num, pratica_nome,
                     subitem_idx, subitem_nome, evidencia_desc,
                     n0, n1, n2, n3, n4, nota_sa,
                     decisao, nota_final, desc_nc, comentarios,
                     ia_decisao=None, ia_nota=None, ia_confianca=None,
                     ia_atendidos=None, ia_faltantes=None,
                     ia_analise=None, ia_status=None):
    """INSERT ou UPDATE de uma avaliação de subitem."""
    pratica_num = _safe_int(pratica_num)
    subitem_idx = _safe_int(subitem_idx)
    nota_sa     = _safe_int(nota_sa)
    nota_final  = _safe_int(nota_final)
    ia_nota     = _safe_int(ia_nota)
    now = datetime.now().isoformat()

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, decisao, nota_final FROM avaliacoes "
            "WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?",
            (auditoria_id, pratica_num, subitem_idx)
        ).fetchone()

        if row:
            # Registrar alteração no log se decisão ou nota mudou
            if row["decisao"] != decisao:
                _registrar_log(conn, auditoria_id, pratica_num, subitem_idx,
                               "decisao", row["decisao"], decisao)
            if row["nota_final"] != nota_final:
                _registrar_log(conn, auditoria_id, pratica_num, subitem_idx,
                               "nota_final",
                               str(row["nota_final"]), str(nota_final))

            conn.execute("""
                UPDATE avaliacoes
                SET decisao=?, nota_final=?, descricao_nc=?, comentarios=?,
                    ia_decisao=?, ia_nota_sugerida=?, ia_confianca=?,
                    ia_pontos_atendidos=?, ia_pontos_faltantes=?,
                    ia_analise_detalhada=?, ia_status=?,
                    data_atualizacao=?
                WHERE id=?
            """, (
                decisao, nota_final, desc_nc, comentarios,
                ia_decisao, ia_nota, ia_confianca,
                json.dumps(ia_atendidos  or [], ensure_ascii=False),
                json.dumps(ia_faltantes or [], ensure_ascii=False),
                ia_analise, ia_status, now, row["id"]
            ))
        else:
            conn.execute("""
                INSERT INTO avaliacoes
                    (auditoria_id, pratica_num, pratica_nome,
                     subitem_idx, subitem_nome, evidencia_descricao,
                     nivel_0, nivel_1, nivel_2, nivel_3, nivel_4,
                     nota_self_assessment,
                     decisao, nota_final, descricao_nc, comentarios,
                     ia_decisao, ia_nota_sugerida, ia_confianca,
                     ia_pontos_atendidos, ia_pontos_faltantes,
                     ia_analise_detalhada, ia_status, data_atualizacao)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                auditoria_id, pratica_num, pratica_nome,
                subitem_idx, subitem_nome, evidencia_desc,
                n0, n1, n2, n3, n4, nota_sa,
                decisao, nota_final, desc_nc, comentarios,
                ia_decisao, ia_nota, ia_confianca,
                json.dumps(ia_atendidos  or [], ensure_ascii=False),
                json.dumps(ia_faltantes or [], ensure_ascii=False),
                ia_analise, ia_status, now
            ))

        conn.execute(
            "UPDATE auditorias SET data_atualizacao=? WHERE id=?",
            (now, auditoria_id)
        )
        conn.commit()
    finally:
        conn.close()


def carregar_avaliacoes(auditoria_id: int) -> pd.DataFrame:
    """Carrega todas as avaliações de uma auditoria como DataFrame."""
    conn = get_db()
    try:
        df = pd.read_sql_query("""
            SELECT * FROM avaliacoes
            WHERE auditoria_id=?
            ORDER BY pratica_num, subitem_idx
        """, conn, params=(auditoria_id,))
        # Garantir tipos numéricos
        for col in ["pratica_num", "subitem_idx",
                    "nota_self_assessment", "nota_final", "ia_nota_sugerida"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────────────────────────────────────

def _registrar_log(conn, auditoria_id, pratica_num, subitem_idx,
                   campo, valor_antes, valor_depois, usuario="sistema"):
    """Insere um registro no audit_log (usa conexão já aberta)."""
    conn.execute("""
        INSERT INTO audit_log
            (timestamp, auditoria_id, pratica_num, subitem_idx,
             campo, valor_antes, valor_depois, usuario)
        VALUES (?,?,?,?,?,?,?,?)
    """, (datetime.now().isoformat(), auditoria_id, pratica_num,
          subitem_idx, campo, valor_antes, valor_depois, usuario))


def carregar_log(auditoria_id: int, limit: int = 200) -> pd.DataFrame:
    """Retorna os últimos N registros do audit_log de uma auditoria."""
    conn = get_db()
    try:
        return pd.read_sql_query("""
            SELECT * FROM audit_log
            WHERE auditoria_id=?
            ORDER BY timestamp DESC
            LIMIT ?
        """, conn, params=(auditoria_id, limit))
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# COMPARATIVO ENTRE CICLOS
# ─────────────────────────────────────────────────────────────────────────────

def listar_ciclos_area(unidade: str, area: str) -> list[dict]:
    """Retorna todos os ciclos disponíveis para unidade+área."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, ciclo, status, data_atualizacao,
                   (SELECT AVG(CAST(nota_final AS REAL))
                    FROM avaliacoes
                    WHERE auditoria_id=auditorias.id
                    AND nota_final IS NOT NULL) AS media
            FROM auditorias
            WHERE unidade=? AND area=?
            ORDER BY ciclo
        """, (unidade, area)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def comparativo_ciclos(auditoria_id_a: int, auditoria_id_b: int) -> pd.DataFrame:
    """
    Retorna DataFrame comparando nota_final de dois ciclos,
    calculando delta e indicando melhora/piora.
    """
    conn = get_db()
    try:
        df_a = pd.read_sql_query("""
            SELECT pratica_num, pratica_nome, subitem_idx, subitem_nome,
                   nota_final AS nota_a, decisao AS decisao_a
            FROM avaliacoes WHERE auditoria_id=?
        """, conn, params=(auditoria_id_a,))

        df_b = pd.read_sql_query("""
            SELECT pratica_num, subitem_idx,
                   nota_final AS nota_b, decisao AS decisao_b
            FROM avaliacoes WHERE auditoria_id=?
        """, conn, params=(auditoria_id_b,))

        df = df_a.merge(
            df_b, on=["pratica_num", "subitem_idx"], how="outer"
        )
        df["delta"] = pd.to_numeric(df["nota_b"], errors="coerce") - \
                      pd.to_numeric(df["nota_a"], errors="coerce")
        df["tendencia"] = df["delta"].apply(
            lambda d: "⬆️ Melhora" if d and d > 0
                 else ("⬇️ Piora"  if d and d < 0
                 else ("➡️ Igual"  if d == 0 else "—"))
        )
        return df.sort_values(["pratica_num", "subitem_idx"])
    finally:
        conn.close()


def snapshot_notas(auditoria_id: int):
    """
    Salva snapshot das notas atuais para histórico.
    Chamado manualmente pelo usuário ao "fechar" um ciclo.
    """
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        rows = conn.execute("""
            SELECT pratica_num, subitem_idx, nota_final, decisao
            FROM avaliacoes WHERE auditoria_id=?
        """, (auditoria_id,)).fetchall()
        for r in rows:
            conn.execute("""
                INSERT INTO snapshots_nota
                    (auditoria_id, pratica_num, subitem_idx,
                     nota_final, decisao, capturado_em)
                VALUES (?,?,?,?,?,?)
            """, (auditoria_id, r["pratica_num"], r["subitem_idx"],
                  r["nota_final"], r["decisao"], now))
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAÇÃO / IMPORTAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def exportar_banco(destino: Path = None) -> Path:
    """
    Cria uma cópia portátil do banco completo.
    Útil para compartilhar dados entre máquinas.
    """
    if destino is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = DADOS_DIR / f"export_completo_{ts}.db"
    shutil.copy2(DB_PATH, destino)
    return destino


def importar_banco(origem: Path, modo: str = "substituir") -> bool:
    """
    Importa banco de outra máquina.
    modo='substituir': substitui o banco atual (faz backup antes).
    modo='mesclar':    tenta mesclar auditorias novas (não implementado nesta versão).
    """
    if not Path(origem).exists():
        return False
    fazer_backup(motivo="pre_import")
    if modo == "substituir":
        shutil.copy2(origem, DB_PATH)
        init_db()  # aplicar migrações pendentes
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# ESTATÍSTICAS RÁPIDAS
# ─────────────────────────────────────────────────────────────────────────────

def estatisticas_auditoria(auditoria_id: int) -> dict:
    """Retorna métricas resumidas de uma auditoria."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*)                                               AS total,
                SUM(CASE WHEN decisao != 'pendente' THEN 1 ELSE 0 END) AS avaliados,
                SUM(CASE WHEN decisao = 'conforme'  THEN 1 ELSE 0 END) AS conformes,
                SUM(CASE WHEN decisao = 'nao_conforme' THEN 1 ELSE 0 END) AS nao_conformes,
                SUM(CASE WHEN ia_status = 'ok'      THEN 1 ELSE 0 END) AS com_ia,
                AVG(CAST(nota_self_assessment AS REAL))                AS media_sa,
                AVG(CAST(nota_final           AS REAL))                AS media_final
            FROM avaliacoes WHERE auditoria_id=?
        """, (auditoria_id,)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# REVISÃO COLABORATIVA — CHAT HUMANO-IA
# ─────────────────────────────────────────────────────────────────────────────

def salvar_mensagem_chat(auditoria_id: int, pratica_num: int, subitem_idx: int,
                         role: str, conteudo: str,
                         decisao_snapshot: str = None,
                         nota_snapshot: int = None,
                         confianca_snapshot: str = None):
    """Persiste uma mensagem do chat de revisão colaborativa."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO chat_revisao
                (auditoria_id, pratica_num, subitem_idx, timestamp,
                 role, conteudo,
                 decisao_snapshot, nota_snapshot, confianca_snapshot)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (auditoria_id, pratica_num, subitem_idx,
              datetime.now().isoformat(),
              role, conteudo,
              decisao_snapshot, nota_snapshot, confianca_snapshot))
        conn.commit()
    finally:
        conn.close()


def carregar_chat(auditoria_id: int, pratica_num: int,
                  subitem_idx: int) -> list[dict]:
    """Carrega histórico completo do chat de um subitem."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, timestamp, role, conteudo,
                   decisao_snapshot, nota_snapshot, confianca_snapshot
            FROM chat_revisao
            WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
            ORDER BY timestamp ASC
        """, (auditoria_id, pratica_num, subitem_idx)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def limpar_chat(auditoria_id: int, pratica_num: int, subitem_idx: int):
    """Remove todo o histórico de chat de um subitem."""
    conn = get_db()
    try:
        conn.execute("""
            DELETE FROM chat_revisao
            WHERE auditoria_id=? AND pratica_num=? AND subitem_idx=?
        """, (auditoria_id, pratica_num, subitem_idx))
        conn.commit()
    finally:
        conn.close()



def carregar_todos_chats_auditoria(auditoria_id: int) -> dict:
    """Carrega TODOS os chats de uma auditoria em UMA query.
    Retorna dict: {(pratica_num, subitem_idx): [msgs]} para lookup O(1) no loop de subitens.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT * FROM chat_revisao
            WHERE auditoria_id=?
            ORDER BY pratica_num, subitem_idx, timestamp
        """, (auditoria_id,)).fetchall()
        result = {}
        for row in rows:
            key = (int(row["pratica_num"]), int(row["subitem_idx"]))
            if key not in result:
                result[key] = []
            result[key].append(dict(row))
        return result
    finally:
        conn.close()


def historico_para_openai(msgs: list[dict]) -> list[dict]:
    """
    Converte histórico do banco para formato de mensagens da API OpenAI.
    Ignora mensagens do sistema (role='sistema').
    """
    result = []
    for m in msgs:
        if m["role"] in ("user", "assistant"):
            result.append({"role": m["role"], "content": m["conteudo"]})
    return result


# ─────────────────────────────────────────────────────────────────────────────
# APRENDIZADO CONTÍNUO — EXEMPLOS FEW-SHOT POR REVISÃO COLABORATIVA
# ─────────────────────────────────────────────────────────────────────────────

def registrar_aprendizado(
    pratica_num: int, subitem_idx: int,
    pratica_nome: str, subitem_nome: str,
    unidade: str, area: str, ciclo: str,
    nota_sa: int,
    nota_ia_inicial: int, decisao_ia_inicial: str,
    observacao_auditor: str,
    decisao_consenso: str, nota_consenso: int,
    justificativa: str = ""
):
    """
    Registra um caso de consenso humano-IA como exemplo de aprendizado.
    Só registra quando houve mudança de decisão (IA aprendeu com o auditor).
    """
    if decisao_ia_inicial == decisao_consenso and nota_ia_inicial == nota_consenso:
        return  # Sem divergência → não registra
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO aprendizados
                (pratica_num, subitem_idx, pratica_nome, subitem_nome,
                 unidade, area, ciclo,
                 nota_sa, nota_ia_inicial, decisao_ia_inicial,
                 observacao_auditor, decisao_consenso, nota_consenso, justificativa)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pratica_num, subitem_idx, pratica_nome, subitem_nome,
              unidade, area, ciclo,
              nota_sa, nota_ia_inicial, decisao_ia_inicial,
              observacao_auditor, decisao_consenso, nota_consenso, justificativa))
        conn.commit()
    finally:
        conn.close()


def buscar_exemplos_similares(pratica_num: int, subitem_idx: int,
                               limit: int = 3) -> list[dict]:
    """
    Retorna exemplos de aprendizado anteriores para o mesmo subitem.
    Usados como few-shot examples no prompt de revisão.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT pratica_nome, subitem_nome, unidade, ciclo,
                   nota_sa, nota_ia_inicial, decisao_ia_inicial,
                   observacao_auditor, decisao_consenso, nota_consenso,
                   justificativa, data_registro
            FROM aprendizados
            WHERE pratica_num=? AND subitem_idx=?
            ORDER BY data_registro DESC
            LIMIT ?
        """, (pratica_num, subitem_idx, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()




# ═══════════════════════════════════════════════════════════════
# DIÁRIO DE AUDITORIA — CRUD
# ═══════════════════════════════════════════════════════════════

def salvar_entrada_diario(
    auditoria_id: int,
    conteudo: str,
    tipo: str = "observacao",
    titulo: str = "",
    pratica_ref: str = "",
    prioridade: str = "normal",
    data_entrada: str = None,
    entrada_id: int = None
) -> int:
    """
    Cria ou atualiza uma entrada no diário.
    Retorna o id da entrada salva.
    """
    from datetime import datetime
    agora = datetime.now().isoformat()
    if data_entrada is None:
        data_entrada = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    try:
        if entrada_id:
            conn.execute("""
                UPDATE diario_auditoria
                SET conteudo=?, tipo=?, titulo=?, pratica_ref=?,
                    prioridade=?, data_entrada=?, data_atualizacao=?
                WHERE id=? AND auditoria_id=?
            """, (conteudo, tipo, titulo, pratica_ref, prioridade,
                  data_entrada, agora, entrada_id, auditoria_id))
            conn.commit()
            return entrada_id
        else:
            cur = conn.execute("""
                INSERT INTO diario_auditoria
                    (auditoria_id, data_entrada, tipo, titulo, conteudo,
                     pratica_ref, prioridade, resolvido, data_criacao, data_atualizacao)
                VALUES (?,?,?,?,?,?,?,0,?,?)
            """, (auditoria_id, data_entrada, tipo, titulo, conteudo,
                  pratica_ref, prioridade, agora, agora))
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def carregar_diario(auditoria_id: int, tipo: str = None) -> list[dict]:
    """Retorna entradas do diário ordenadas por data_entrada DESC, data_criacao DESC."""
    conn = get_db()
    try:
        if tipo:
            rows = conn.execute("""
                SELECT * FROM diario_auditoria
                WHERE auditoria_id=? AND tipo=?
                ORDER BY data_entrada DESC, data_criacao DESC
            """, (auditoria_id, tipo)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM diario_auditoria
                WHERE auditoria_id=?
                ORDER BY data_entrada DESC, data_criacao DESC
            """, (auditoria_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def marcar_resolvido_diario(entrada_id: int, auditoria_id: int, resolvido: bool = True):
    """Marca/desmarca uma entrada como resolvida."""
    from datetime import datetime
    conn = get_db()
    try:
        conn.execute("""
            UPDATE diario_auditoria
            SET resolvido=?, data_atualizacao=?
            WHERE id=? AND auditoria_id=?
        """, (1 if resolvido else 0, datetime.now().isoformat(), entrada_id, auditoria_id))
        conn.commit()
    finally:
        conn.close()


def excluir_entrada_diario(entrada_id: int, auditoria_id: int):
    """Remove uma entrada do diário."""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM diario_auditoria WHERE id=? AND auditoria_id=?",
            (entrada_id, auditoria_id)
        )
        conn.commit()
    finally:
        conn.close()


def resumo_diario(auditoria_id: int) -> dict:
    """Retorna contagens por tipo e prioridade."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT tipo, prioridade, resolvido, COUNT(*) AS cnt
            FROM diario_auditoria
            WHERE auditoria_id=?
            GROUP BY tipo, prioridade, resolvido
        """, (auditoria_id,)).fetchall()
        result = {"total": 0, "pendentes": 0, "alta_prioridade": 0, "por_tipo": {}}
        for r in rows:
            result["total"] += r["cnt"]
            if not r["resolvido"]:
                result["pendentes"] += r["cnt"]
            if r["prioridade"] == "alta" and not r["resolvido"]:
                result["alta_prioridade"] += r["cnt"]
            result["por_tipo"][r["tipo"]] = result["por_tipo"].get(r["tipo"], 0) + r["cnt"]
        return result
    finally:
        conn.close()


def listar_todos_aprendizados(limit: int = 100) -> list[dict]:
    """Lista todos os registros de aprendizado (para painel de gestão)."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, pratica_num, subitem_idx, pratica_nome, subitem_nome,
                   unidade, area, ciclo,
                   nota_ia_inicial, decisao_ia_inicial,
                   decisao_consenso, nota_consenso,
                   observacao_auditor, justificativa, data_registro
            FROM aprendizados
            ORDER BY data_registro DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
