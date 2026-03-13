import sys
import os
from pathlib import Path

# Vercel-specific path handling
# Adds the root directory (parent of 'api') to sys.path
current_dir = Path(__file__).parent.resolve()
root_path = current_dir.parent.resolve()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

try:
    print(f"DEBUG: Vercel startup. Root path: {root_path}", file=sys.stderr)
    from backend.main import app
    from backend.db import init_db
    init_db()  # Force database initialization unconditionally on cold start
except Exception as e:
    import traceback
    print("FATAL ERROR during Vercel startup:", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise e
