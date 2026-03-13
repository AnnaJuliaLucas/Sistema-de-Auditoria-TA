import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from ai_analyzer import SYSTEM_PROMPT
    from criterios_oficiais import REGRAS_GERAIS, CRITERIOS
except ImportError as e:
    print(f"Error loading dependencies: {e}")
    sys.exit(1)

def generate_modelfile(model_base="llama3.2"):
    """Generates an Ollama Modelfile with pre-baked context."""
    
    # 1. Prepare context. We don't bake ALL criteria (too big), 
    # but we bake the systemic rules and the structure.
    
    baked_context = f"""
{SYSTEM_PROMPT}

### REGRAS OFICIAIS (RESUMO)
{REGRAS_GERAIS}

### INSTRUÇÕES PARA O AGENTE LOCAL
- Você é o motor central do AuditoriaTA.
- Suas análises devem ser baseadas EXCLUSIVAMENTE nas evidências fornecidas e no PO.AUT.002.
- Se não houver evidência clara, seja conservador na nota.
"""

    modelfile_content = f"""
FROM {model_base}
SYSTEM \"\"\"{baked_context.strip()}\"\"\"
PARAMETER temperature 0.1
PARAMETER num_ctx 8192
"""

    modelfile_path = Path(_parent) / "Modelfile_Auditoria"
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    
    print(f"✅ Modelfile created at {modelfile_path}")
    return modelfile_path

def create_ollama_model(modelfile_path):
    """Executes ollama create."""
    model_name = "auditoria-ta"
    print(f"🚀 Creating Ollama model '{model_name}' (this may take a minute)...")
    try:
        subprocess.run(["ollama", "create", model_name, "-f", str(modelfile_path)], check=True)
        print(f"✨ Success! Local model '{model_name}' is ready to use.")
    except FileNotFoundError:
        print("❌ Error: 'ollama' command not found. Please install Ollama first.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating model: {e}")

def index_knowledge_base():
    """Scans base_conhecimento and indexes files into the DB."""
    kb_path = Path("C:/AuditoriaTA/base_conhecimento")
    if not kb_path.exists():
        kb_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created knowledge folder: {kb_path}")
        return

    try:
        from backend.db import adicionar_conhecimento
        from ai_analyzer import extract_pdf_text, extract_docx_text
    except ImportError:
        print("⚠️ Skipping indexing: backend.db or ai_analyzer not available.")
        return

    print("🔍 Scanning knowledge folder for new documents...")
    files = list(kb_path.glob("*"))
    for f in files:
        if f.suffix.lower() == ".pdf":
            content = extract_pdf_text(str(f))
            adicionar_conhecimento(f.name, content, tag="local_doc", fonte=str(f))
            print(f"📄 Indexed PDF: {f.name}")
        elif f.suffix.lower() == ".docx":
            content = extract_docx_text(str(f))
            adicionar_conhecimento(f.name, content, tag="local_doc", fonte=str(f))
            print(f"📝 Indexed DOCX: {f.name}")
        elif f.suffix.lower() in [".txt", ".md"]:
            with open(f, "r", encoding="utf-8", errors="ignore") as tf:
                content = tf.read()
            adicionar_conhecimento(f.name, content, tag="local_doc", fonte=str(f))
            print(f"📑 Indexed TEXT: {f.name}")

if __name__ == "__main__":
    # 1. Index local knowledge
    index_knowledge_base()
    
    # 2. Build local AI model
    mf = generate_modelfile()
    create_ollama_model(mf)
