import socket
import threading
import psutil

HOST = '127.0.0.1'
PORT = 5000
usuarios = {} # {addr: conn}

def kill_process_on_port(port):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections(kind='inet')
            for conn in connections:
                if conn.laddr.port == port:
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass

def mostrar_nodos():
    print("\n" + "="*30)
    print("NODOS ACTIVOS EN LA RED:")
    if not usuarios:
        print("Ningún nodo conectado.")
    for addr in usuarios.keys():
        print(f" > {addr[0]}:{addr[1]}")
    print("="*30 + "\n")

def manejar_conexion(conn, addr):
    usuarios[addr] = conn
    mostrar_nodos()
    try:
        while True:
            data = conn.recv(65536)
            if not data: break
            # Retransmitir a todos los demás (Broadcast de red)
            for client_addr, client_conn in usuarios.items():
                if client_addr != addr:
                    try:
                        client_conn.sendall(data)
                    except: pass
    except: pass
    finally:
        if addr in usuarios:
            del usuarios[addr]
        conn.close()
        print(f"[DESCONEXIÓN]: {addr}")
        mostrar_nodos()

if __name__ == "__main__":
    kill_process_on_port(PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"SERVIDOR REGISTRO INICIADO EN {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=manejar_conexion, args=(conn, addr), daemon=True).start()