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
    from backend.db import DB_PATH, USE_POSTGRES, DATABASE_URL
    import sqlite3
    import os
    from pathlib import Path
    
    path_str = str(DB_PATH)
    path_exists = os.path.exists(path_str)
    dir_exists = os.path.exists(str(DB_PATH.parent))
    
    tables = []
    auditoria_count = 0
    error = None
    
    # List other potential DB files to find lost data
    potential_dbs = []
    search_paths = ["/app", "/home/railway", "/tmp"]
    for sp in search_paths:
        if os.path.exists(sp):
            try:
                for root, dirs, files in os.walk(sp):
                    for file in files:
                        if file.endswith(".db"):
                            full_p = os.path.join(root, file)
                            potential_dbs.append({
                                "path": full_p,
                                "size": os.path.getsize(full_p),
                                "mtime": datetime.fromtimestamp(os.path.getmtime(full_p)).isoformat()
                            })
            except Exception:
                pass

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
        "db_path_exists": path_exists,
        "db_dir_exists": dir_exists,
        "tables": tables,
        "auditoria_count": auditoria_count,
        "potential_lost_dbs": potential_dbs,
        "error": error,
        "use_postgres": USE_POSTGRES,
        "env_railway": os.environ.get("RAILWAY_ENVIRONMENT"),
        "cwd": os.getcwd()
    }

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
