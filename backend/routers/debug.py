"""
debug.py — Diagnostic endpoints for Vercel environment.
"""
from fastapi import APIRouter
import os
import sys
import platform
import logging
import traceback
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
        from backend.db import DB_PATH
        cursor = conn.execute("SELECT id, unidade, area, ciclo, evidence_folder_path FROM auditorias ORDER BY id DESC")
        rows = cursor.fetchall()
        
        audits = []
        for row in rows[:10]:
            ev_path = row['evidence_folder_path']
            audits.append({
                "id": row['id'],
                "name": f"{row['unidade']} - {row['area']} - {row['ciclo']}",
                "path_in_db": ev_path,
                "exists_on_disk": os.path.exists(ev_path) if ev_path and os.path.isabs(ev_path) else False
            })

        import shutil
        import platform
        import tempfile
        
        usage_main = shutil.disk_usage("/")
        usage_tmp = shutil.disk_usage("/tmp")
        usage_data = shutil.disk_usage("/app/data") if os.path.exists("/app/data") else usage_main
        
        return {
            "environment": {
                "os": platform.system(),
                "node": platform.node(),
                "cwd": os.getcwd(),
                "db_path": str(DB_PATH)
            },
            "total_audits_in_db": len(rows),
            "recent_audits": audits,
            "uploads_dir_content": os.listdir("data/uploads") if os.path.exists("data/uploads") else [],
            "disk_usage": {
                "root": {"free_gb": round(float(usage_main.free) / (1024**3), 2), "total_gb": round(float(usage_main.total) / (1024**3), 2)},
                "tmp": {"free_gb": round(float(usage_tmp.free) / (1024**3), 2), "total_gb": round(float(usage_tmp.total) / (1024**3), 2)},
                "data": {"free_gb": round(float(usage_data.free) / (1024**3), 2), "total_gb": round(float(usage_data.total) / (1024**3), 2)}
            }
        }
    except Exception as e:
        log.error(f"check_evidences error: {e}")
        return {"error": str(e), "traceback": traceback.format_exc()}
    finally:
        conn.close()

@router.get("/inspect-db")
def inspect_db():
    """Returns raw rows from auditorias table for debugging."""
    try:
        from backend.db import get_db
        with get_db() as conn:
            rows = conn.execute("SELECT id, unidade, area, ciclo, evidence_folder_path FROM auditorias").fetchall()
            users = conn.execute("SELECT id, email, role FROM users").fetchall()
            return {
                "auditorias_count": len(rows),
                "auditorias": [dict(r) for r in rows],
                "users_count": len(users),
                "users": [dict(r) for r in users]
            }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.get("/fix-paths")
def fix_paths():
    """Converts absolute Windows paths to local Railway paths."""
    try:
        from backend.db import get_db
        fixed = []
        with get_db() as conn:
            rows = conn.execute("SELECT id, evidence_folder_path FROM auditorias").fetchall()
            for row in rows:
                path = row['evidence_folder_path']
                # Search for any Windows-like patterns or OneDrive
                if path and (":" in path or "\\" in path or "OneDrive" in path or "Users" in path):
                    new_path = f"/app/data/uploads/{row['id']}/evidences"
                    conn.execute("UPDATE auditorias SET evidence_folder_path=? WHERE id=?", (new_path, row['id']))
                    fixed.append({"id": row['id'], "old": path, "new": new_path})
            
            if hasattr(conn, 'commit'): conn.commit()
            
        return {"status": "success", "fixed_count": len(fixed), "details": fixed}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@router.get("/nuclear-clean")
def nuclear_clean():
    """Removes all files in uploads and clears app.log to recover space."""
    try:
        import shutil
        import os
        results = {"cleaned": [], "errors": []}
        
        # 1. Clear app.log
        log_path = "/app/data/app.log" if os.environ.get("RAILWAY_ENVIRONMENT") else "app.log"
        if os.path.exists(log_path):
            with open(log_path, "w") as f:
                f.write(f"--- Log cleared at {datetime.now().isoformat()} ---\n")
            results["cleaned"].append("app.log")

        # 2. Deletes contents of /app/data/uploads
        uploads_dir = "/app/data/uploads" if os.environ.get("RAILWAY_ENVIRONMENT") else "uploads"
        if os.path.exists(uploads_dir):
            for item in os.listdir(uploads_dir):
                item_path = os.path.join(uploads_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    results["cleaned"].append(f"uploads/{item}")
                except Exception as e:
                    results["errors"].append(f"Error deleting {item}: {str(e)}")
                    
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/clean-tmp")
def clean_tmp():
    """Manually clear the /tmp directory to avoid No Space Left on Device."""
    try:
        import shutil
        import os
        tmp = "/tmp"
        if not os.path.exists(tmp):
            return {"status": "error", "message": "/tmp not found"}
            
        count = 0
        errors = []
        for item in os.listdir(tmp):
            item_path = os.path.join(tmp, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                    count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                    count += 1
            except Exception as e:
                errors.append(f"{item}: {str(e)}")
                
        return {"status": "success", "cleaned_items": count, "errors": errors}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/logs")
def get_logs(lines: int = 100):
    """Returns the last N lines of the application log file."""
    log_path = "/app/data/app.log" if os.environ.get("RAILWAY_ENVIRONMENT") else "app.log"
    if not os.path.exists(log_path):
        return {"error": f"Log file not found at {log_path}"}
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()
            return {
                "path": log_path,
                "lines": content[-lines:] if len(content) > lines else content,
                "total_lines": len(content)
            }
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit-details/{audit_id}")
def get_audit_details(audit_id: int):
    """Deep inspection of a specific audit: files and evaluations."""
    try:
        from backend.db import get_db
        from pathlib import Path
        
        details = {
            "audit": None,
            "evaluation_samples": [],
            "files_on_disk": [],
            "evidence_map_raw": None
        }
        
        with get_db() as conn:
            # 1. Basic info
            row = conn.execute("SELECT * FROM auditorias WHERE id = ?", (audit_id,)).fetchone()
            if row:
                details["audit"] = dict(row)
                details["evidence_map_raw"] = row["evidence_map"]
            
            # 2. Evaluation samples (first 10)
            evs = conn.execute("SELECT id, pratica_num, subitem_idx, nota_self_assessment, decisao FROM avaliacoes WHERE auditoria_id = ? LIMIT 20", (audit_id,)).fetchall()
            details["evaluation_samples"] = [dict(e) for e in evs]
            
        # 3. List files on disk recursively
        if details["audit"] and details["audit"].get("evidence_folder_path"):
            path = Path(details["audit"]["evidence_folder_path"])
            if path.exists():
                for f in path.rglob("*"):
                    details["files_on_disk"].append({
                        "rel": str(f.relative_to(path)),
                        "abs": str(f),
                        "is_file": f.is_file(),
                        "size": f.stat().st_size if f.is_file() else 0
                    })
        
        return details
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.get("/re-extract/{audit_id}")
def re_extract_audit(audit_id: int):
    """Force re-extraction of audit ZIP using robust logic."""
    try:
        from backend.db import get_auditoria, BASE_DIR
        from backend.routers.evidencias import extract_zip_robustly, _get_or_build_evidence_map
        import json
        
        aud = get_auditoria(audit_id)
        if not aud:
            return {"error": "Audit not found"}
            
        audit_dir = BASE_DIR / "uploads" / str(audit_id)
        zip_path = audit_dir / f"evidences_{audit_id}.zip"
        extract_to = audit_dir / "evidences"
        
        if not zip_path.exists():
            zip_url = aud.get("evidence_zip_url")
            if zip_url.startswith("http"):
                import urllib.request
                log.info(f"Downloading ZIP for re-extraction from {zip_url}...")
                audit_dir.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(zip_url, zip_path)
            elif os.path.exists(zip_url):
                import shutil
                log.info(f"Copying local ZIP for re-extraction from {zip_url}...")
                audit_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(zip_url, zip_path)
            else:
                return {"error": f"Source ZIP not found at {zip_url} (it may have been cleaned up to save space)."}
            
        # 1. Re-extract
        log.info(f"Force re-extracting audit {audit_id}")
        extract_zip_robustly(zip_path, extract_to)
        
        # 2. Re-build map
        new_map = _get_or_build_evidence_map(str(extract_to), refresh=True)
        # Convert keys for DB
        db_map = {f"{p}.{s}": files for (p, s), files in new_map.items()}
        
        # 3. Update DB
        from backend.db import get_db, USE_POSTGRES
        with get_db() as conn:
            q = "UPDATE auditorias SET evidence_map=? WHERE id=?"
            if USE_POSTGRES: q = q.replace("?", "%s")
            conn.execute(q, (json.dumps(db_map), audit_id))
            conn.commit()
            
        return {
            "status": "success", 
            "message": "Re-extraction complete",
            "map_size": len(db_map)
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}
@router.get("/debug-import/{audit_id}")
def debug_import_audit(audit_id: int):
    """Deep debug of Excel Column I parsing."""
    try:
        from backend.db import get_auditoria, get_db
        import openpyxl
        
        aud = get_auditoria(audit_id)
        if not aud: return {"error": "Audit not found"}
        
        assessment_path = aud["assessment_file_path"]
        results = []
        
        wb = openpyxl.load_workbook(assessment_path, data_only=True)
        ws = wb.active
        
        current_p_num = None
        s_idx = 0
        
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=100, values_only=True)):
            if not any(row): continue
            
            row_info = {"line": i+1, "col_A": row[0], "col_B": row[1], "col_I": row[8] if len(row) > 8 else "MISSING"}
            
            if row[0] and str(row[0]).strip().isdigit():
                current_p_num = int(row[0])
                s_idx = 0
                row_info["type"] = "PRATICA"
            
            # Usar coluna C (index 2) para detectar subitem
            if current_p_num is not None and row[2]:
                # Skip if it's the header "PRÁTICA" in column B or "EVIDÊNCIA" in column C
                if str(row[1]).strip().upper() == "PRÁTICA" or str(row[2]).strip().upper() == "EVIDÊNCIA":
                    continue

                val_raw = row[8] if len(row) > 8 else None
                from backend.routers.export import _safe_int
                row_info["type"] = "SUBITEM" if "type" not in row_info else "PRATICA+SUBITEM"
                row_info["p"] = current_p_num
                row_info["s"] = s_idx
                row_info["nota"] = _safe_int(val_raw)
                s_idx += 1
            
            results.append(row_info)
            
        return {"audit_id": audit_id, "path": assessment_path, "parsed": results}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.post("/storage-cleanup")
def storage_cleanup():
    """Diagnostic tool to reclaim disk space from orphaned files and folders."""
    from backend.db import BASE_DIR, listar_auditorias
    import shutil
    import os
    from pathlib import Path
    
    results = {
        "deleted_zip_count": 0,
        "deleted_folder_count": 0,
        "errors": []
    }
    
    upload_dir = BASE_DIR / "uploads"
    if not upload_dir.exists():
        return {"data": "Upload directory not found", "results": results}
        
    all_audits = listar_auditorias()
    active_audit_ids = {str(a["id"]) for a in all_audits}
    em_andamento_ids = {str(a["id"]) for a in all_audits if (a.get("status") or "").lower().strip().replace(" ", "_") == "em_andamento"}
    
    log.info(f"Storage Cleanup started. Active: {active_audit_ids}, In-Progress: {em_andamento_ids}")

    # Iterate through all items in uploads/
    for item in list(upload_dir.iterdir()):
        try:
            # 1. Cleanup ZIP files in the root of uploads
            if item.is_file() and item.suffix.lower() == ".zip":
                item.unlink()
                results["deleted_zip_count"] += 1
                continue
                
            if item.is_dir():
                audit_id = item.name
                
                # 2. Delete folders for audits that don't exist anymore
                if audit_id not in active_audit_ids:
                    shutil.rmtree(item)
                    results["deleted_folder_count"] += 1
                    continue
                
                # 3. Delete folders for audits that are NOT "em_andamento"
                if audit_id not in em_andamento_ids:
                    shutil.rmtree(item)
                    results["deleted_folder_count"] += 1
                    continue
                
                # 4. Deep cleanup: Find and delete any ZIPs inside the audit folder (extracts are already done)
                for sub_zip in list(item.glob("*.zip")):
                    sub_zip.unlink()
                    results["deleted_zip_count"] += 1
                
                # Also check subfolders (like 'evidences/') for stray zips
                for sub_zip in list(item.rglob("*.zip")):
                    sub_zip.unlink()
                    results["deleted_zip_count"] += 1
                    
        except Exception as e:
            results["errors"].append(f"Error processing {item}: {str(e)}")
            
    log.info(f"Cleanup finished: {results}")
    return results
@router.get("/inspect")
def inspect_path(path: str = "/app/data"):
    """Generic directory listing for troubleshooting."""
    from pathlib import Path
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        
        details = {
            "path": str(p),
            "exists": p.exists(),
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "items": []
        }
        
        if p.is_dir():
            for item in p.iterdir():
                details["items"].append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
        
        return details
    except Exception as e:
        return {"error": str(e)}
