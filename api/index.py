import sys
from os.path import dirname, join, realpath

# Add backend directory to path
backend_path = join(dirname(dirname(realpath(__file__))), "backend")
sys.path.append(backend_path)

from backend.main import app

# This is the entry point for Vercel Python runtime
handler = app
