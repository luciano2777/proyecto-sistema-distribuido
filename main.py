import tkinter as tk
import sys
import os
import subprocess
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from Interfaz import AplicacionMonitor
except ImportError:
    print("ERROR: No se pudo importar 'interfaz.py'")
    sys.exit(1)

def main():
    root = tk.Tk()
    root.title("SD 2526-2 Proyecto")
    root.geometry("1000x750")
    root.minsize(800, 600)
    
    app = AplicacionMonitor(root)
    
    def al_cerrar():
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()

def main_con_servidor_automatico():
    procesos = []
    
    respuesta = input("¿Desea iniciar el servidor automáticamente? (s/n): ").lower()
    
    if respuesta == 's':
        try:
            servidor = subprocess.Popen(
                [sys.executable, "server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            procesos.append(servidor)
            
            resp_clientes = input("¿Iniciar clientes automáticamente? (s/n): ").lower()
            
            if resp_clientes == 's':
                num_clientes = input("Número de clientes a iniciar (default 2): ").strip()
                num_clientes = int(num_clientes) if num_clientes else 2
                
                for i in range(num_clientes):
                    cliente = subprocess.Popen(
                        [sys.executable, "cliente.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    procesos.append(cliente)
                    time.sleep(0.5)
                
        except Exception as e:
            print(f"Error al iniciar procesos: {e}")
    
    root = tk.Tk()
    root.geometry("1000x750")
    app = AplicacionMonitor(root)
    
    def al_cerrar():
        for proc in procesos:
            try:
                proc.terminate()
            except:
                try:
                    proc.kill()
                except:
                    pass
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()

if __name__ == "__main__":
    main()