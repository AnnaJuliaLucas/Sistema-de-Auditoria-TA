import urllib.parse
from pathlib import Path
import os

path_with_accents = r"C:/Users/Duda PC/OneDrive/Documentos/Automateasy/Auditoria/Evidências/Juiz de Fora/Redução/1 - ROTINAS DE TA/1.1 - Backup periódico e por evento/Atualizado texto longo.PNG"

# Simulate what the frontend might send
encoded = urllib.parse.quote(path_with_accents)
print(f"Encoded: {encoded}")

# Simulate backend decoding
decoded = urllib.parse.unquote(encoded)
print(f"Decoded: {decoded}")

file_path = Path(decoded)
print(f"Path object: {file_path}")
print(f"Exists: {file_path.exists()}")

# Test with backslashes vs forward slashes
path_fixed = path_with_accents.replace("/", "\\")
print(f"Fixed exists: {Path(path_fixed).exists()}")

# Test extension check
ext = file_path.suffix.lower()
print(f"Extension: {ext}")
EXTS_ALL = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.xlsx', '.xls', '.docx', '.doc'}
print(f"In EXTS_ALL: {ext in EXTS_ALL}")
