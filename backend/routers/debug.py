"""
debug.py — Diagnostic endpoints for Vercel environment.
"""
from fastapi import APIRouter
import os
import sys
import platform
import logging
from datetime import datetime

router = APIRouter(prefix="/api/debug", tags=["debug"])
log = logging.getLogger("auditoria_debug")

@router.get("/")
def get_debug_info():
    """Returns general environment info (SAFE)."""
    # Mask sensitive variables
    envs = {}
    for key in os.environ:
        val = os.environ[key]
        if any(secret in key.upper() for secret in ["KEY", "SECRET", "PWD", "PASSWORD", "URL", "DATABASE"]):
            # Mask most of it, keep start/end for identity
            if len(val) > 8:
                envs[key] = f"{val[:4]}...{val[-4:]}"
            else:
                envs[key] = "***"
        else:
            envs[key] = val

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "sys_path": sys.path[:5], # First few items
        "env_vars": envs,
        "backend_dir_exists": os.path.exists("backend"),
        "api_dir_exists": os.path.exists("api")
    }

@router.get("/libs")
def get_installed_libs():
    """Returns list of installed packages via pip."""
    try:
        import pkg_resources
        installed_packages = pkg_resources.working_set
        installed_packages_list = sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])
        return {"packages": installed_packages_list}
    except Exception as e:
        return {"error": str(e)}

@router.get("/db-status")
def get_db_status():
    """Checks database configuration state."""
    from backend.db import USE_POSTGRES, DATABASE_URL
    
    # Mask URL
    masked_url = "***"
    if DATABASE_URL:
        parts = DATABASE_URL.split("@")
        masked_url = parts[-1] if len(parts) > 1 else "configured"

    # Try import inside to check availability
    try:
        import psycopg2
        return {
            "use_postgres": USE_POSTGRES,
            "database_url_masked": masked_url,
            "postgres_driver_available": True,
            "psycopg2_version": psycopg2.__version__
        }
    except Exception as e:
        return {
            "use_postgres": USE_POSTGRES,
            "database_url_masked": masked_url,
            "postgres_driver_available": False,
            "error": str(e)
        }

@router.get("/db-details")
def get_db_details():
    """Returns detailed SQLite info for troubleshooting."""
    from backend.db import DB_PATH, USE_POSTGRES
    import sqlite3
    import os
    from pathlib import Path
    from datetime import datetime
    
    home_dir = str(Path.home())
    path_str = str(DB_PATH)
    path_exists = os.path.exists(path_str)
    
    tables = []
    auditoria_count = 0
    error = None
    
    potential_dbs = []
    # VERY aggressive search for ANY .db file in common system root paths
    search_paths = ["/app", home_dir, "/tmp", "/data", "/mnt", "/var/lib"]
    root_folders = []
    try:
        root_folders = os.listdir("/")
    except: pass
    
    seen_paths = set()
    for sp in search_paths:
        if os.path.exists(sp):
            try:
                for root, dirs, files in os.walk(sp):
                    if len(seen_paths) > 1000: break
                    for file in files:
                        if file.endswith(".db") or "auditoria" in file.lower():
                            full_p = os.path.join(root, file)
                            if full_p in seen_paths: continue
                            seen_paths.add(full_p)
                            try:
                                stats = os.stat(full_p)
                                if stats.st_size > 1000: # Only interesting DBs
                                    potential_dbs.append({
                                        "path": full_p,
                                        "size": stats.st_size,
                                        "mtime": datetime.fromtimestamp(stats.st_mtime).isoformat()
                                    })
                            except: pass
            except: pass

    try:
        if path_exists:
            conn = sqlite3.connect(path_str)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if "auditorias" in tables:
                row = conn.execute("SELECT COUNT(*) as cnt FROM auditorias").fetchone()
                auditoria_count = row["cnt"]
            conn.close()
    except Exception as e:
        error = str(e)
        
    return {
        "db_path": path_str,
        "home_path": home_dir,
        "root_folders": root_folders,
        "app_files": os.listdir("/app") if os.path.exists("/app") else [],
        "migrate_file_exists": os.path.exists("migrate_data_local.db"),
        "db_path_exists": path_exists,
        "tables": tables,
        "auditoria_count": auditoria_count,
        "potential_lost_dbs": potential_dbs,
        "error": error,
        "cwd": os.getcwd(),
        "env_values": {
            "RAILWAY_VOLUME_MOUNT_PATH": os.environ.get("RAILWAY_VOLUME_MOUNT_PATH"),
            "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT"),
        }
    }

@router.get("/restore-manual")
def restore_manual():
    """Manually force restore from migrate_data_local.db if it exists."""
    from backend.db import DB_PATH, ensure_dirs
    import shutil
    import os
    
    migration_file = "migrate_data_local.db"
    if not os.path.exists(migration_file):
        return {"status": "error", "message": f"File {migration_file} not found in {os.getcwd()}"}
    
    try:
        ensure_dirs()
        # Backup existing (empty) db just in case
        if os.path.exists(str(DB_PATH)):
            shutil.copy2(str(DB_PATH), str(DB_PATH) + ".bak")
            
        shutil.copy2(migration_file, str(DB_PATH))
        return {
            "status": "success", 
            "message": f"Restored from {migration_file} to {DB_PATH}",
            "size": os.path.getsize(str(DB_PATH))
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/force-init")
def force_init_db():
    """Manually triggers database initialization and returns the result/error."""
    try:
        import traceback
        from backend.db import init_db
        log.info("Manual init_db triggered via API")
        init_db()
        return {"status": "success", "message": "Database initialization completed successfully"}
    except Exception as e:
        err = traceback.format_exc()
        log.error(f"Manual init_db FAILED: {err}")
        return {
            "status": "error",
            "message": str(e),
            "traceback": err
        }

@router.get("/check-evidences")
def check_evidences():
    """Diagnostic for evidence mapping and extraction."""
    from backend.db import DB_PATH, get_db
    import sqlite3
    import json
    from pathlib import Path

    if not os.path.exists(str(DB_PATH)):
        return {"error": f"DB not found at {DB_PATH}"}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT id, unidade, area, ciclo, evidence_folder_path, evidence_map FROM auditorias ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return {"status": "none", "message": "No audits found"}

        ev_path = row['evidence_folder_path']
        p = Path(ev_path) if ev_path else None
        
        folders = []
        if p and p.exists():
            folders = [str(d.relative_to(p)) for d in p.glob("*/*") if d.is_dir()][:20]

        import shutil
        total, used, free = shutil.disk_usage("/")
        
        return {
            "audit_id": row['id'],
            "audit_name": f"{row['unidade']} - {row['area']} - {row['ciclo']}",
            "evidence_folder_in_db": ev_path,
            "folder_exists_on_disk": p.exists() if p else False,
            "total_files_on_disk": len(list(p.glob("**/*"))) if p and p.exists() else 0,
            "sample_subdirs": folders,
            "evidence_map_size": len(json.loads(row['evidence_map'])) if row['evidence_map'] else 0,
            "uploads_dir_content": os.listdir("/app/data/uploads") if os.path.exists("/app/data/uploads") else [],
            "disk_usage": {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used/total)*100, 2)
            }
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
