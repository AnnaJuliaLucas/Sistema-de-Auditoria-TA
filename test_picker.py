import threading

def _pick_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return ""
        
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Selecione o arquivo de Assessment (Excel)",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    root.destroy()
    return file_path

result = []
def target():
    result.append(_pick_file())

thread = threading.Thread(target=target)
thread.start()
thread.join()
print("Result:", result)
