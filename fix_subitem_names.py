# fix_subitem_names.py
import sys
import os
from pathlib import Path

# Adicionar o diretório atual ao sys.path para importar os módulos do projeto
sys.path.append(os.getcwd())

try:
    from backend.db import get_db, USE_POSTGRES
    from criterios_oficiais import CRITERIOS
    print("Modules imported successfully.")
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fix_names():
    print("Starting subitem names correction...")
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Buscar todas as avaliações que tenham "Subitem" no nome (case insensitive)
        q_select = "SELECT id, pratica_num, subitem_idx, subitem_nome FROM avaliacoes WHERE subitem_nome LIKE 'Subitem %'"
        if USE_POSTGRES:
            q_select = "SELECT id, pratica_num, subitem_idx, subitem_nome FROM avaliacoes WHERE subitem_nome ILIKE 'Subitem %'"
            
        cursor.execute(q_select)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} generic subitems to fix.")
        
        fixed_count = 0
        for row in rows:
            # row é um objeto que pode ser acessado por índice ou chave
            if hasattr(row, 'keys'):
                row_dict = dict(row)
            else:
                row_dict = {'id': row[0], 'pratica_num': row[1], 'subitem_idx': row[2], 'subitem_nome': row[3]}
                
            p_num = row_dict['pratica_num']
            s_idx = row_dict['subitem_idx']
            key = (p_num, s_idx)
            
            if key in CRITERIOS:
                new_name = CRITERIOS[key]['subitem']
                item_id = row_dict['id']
                
                q_update = "UPDATE avaliacoes SET subitem_nome = ? WHERE id = ?"
                if USE_POSTGRES:
                    q_update = "UPDATE avaliacoes SET subitem_nome = %s WHERE id = %s"
                
                cursor.execute(q_update, (new_name, item_id))
                fixed_count += 1
                if fixed_count % 10 == 0:
                    print(f"Fixed {fixed_count} items...")
        
        conn.commit()
        print(f"Done! {fixed_count} subitems were updated with official names.")

if __name__ == "__main__":
    fix_names()
