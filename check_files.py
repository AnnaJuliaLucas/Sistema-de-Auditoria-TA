import os
from pathlib import Path

folder = r"C:/Users/Duda PC/OneDrive/Documentos/Automateasy/Auditoria/Evidências/Juiz de Fora/Redução"
print(f"Checking folder: {folder}")
print(f"Folder exists: {os.path.exists(folder)}")

if os.path.exists(folder):
    files = []
    for root, dirs, f_names in os.walk(folder):
        for f in f_names:
            files.append(os.path.join(root, f))
    
    print(f"Total files found: {len(files)}")
    for f in files[:10]:
        print(f"File: {f} | Exists: {os.path.exists(f)}")
        
    target = "Atualizado texto longo.PNG"
    found = [f for f in files if target in f]
    print(f"Search for '{target}': {found}")
else:
    print("Folder does not exist. Listing C:/Users/Duda PC/ ...")
    try:
        print(os.listdir("C:/Users/Duda PC"))
    except:
        print("Could not list C:/Users/Duda PC")
