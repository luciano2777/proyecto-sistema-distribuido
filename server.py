import socket
import threading

HOST = '127.0.0.1'
PORT = 5000

usuarios = {}

def manejar_cliente(conn, addr):
    nombre_actual = None
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            mensaje = data.decode('utf-8').strip()
            
            # --- COMANDO: /register ---
            if mensaje.startswith("/register"):
                partes = mensaje.split()
                if len(partes) == 2:
                    nombre = partes[1]
                    if nombre in usuarios:
                        conn.sendall(b"[SERVER] Error: El nombre ya existe.")
                    else:
                        nombre_actual = nombre
                        usuarios[nombre_actual] = conn
                        conn.sendall(f"[SERVER] Registrado como {nombre_actual}".encode('utf-8'))
                else:
                    conn.sendall(b"[SERVER] Uso: /register <nombre>")

            # --- COMANDO: /list ---
            elif mensaje == "/list":
                lista_nombres = ", ".join(usuarios.keys()) if usuarios else "Nadie"
                conn.sendall(f"[SERVER] Usuarios conectados: {lista_nombres}".encode('utf-8'))

            # --- COMANDO: /send ---
            elif mensaje.startswith("/send"):
                if not nombre_actual:
                    conn.sendall(b"[SERVER] Error: Debes registrarte primero.")
                    continue
                
                partes = mensaje.split(maxsplit=2)
                if len(partes) == 3:
                    destino = partes[1]
                    contenido = partes[2]
                    
                    if destino in usuarios:
                        # se envia el mensaje al destino con el nombre del remitente
                        usuarios[destino].sendall(f"[{nombre_actual}]: {contenido}".encode('utf-8'))
                        conn.sendall(f"[INFO] Enviando a {destino}...".encode('utf-8'))
                    else:
                        conn.sendall(f"[SERVER] Error: {destino} no esta conectado.".encode('utf-8'))
                else:
                    conn.sendall(b"[SERVER] Uso: /send <usuario> <mensaje>")

            # --- COMANDO OCULTO: __ACK__ (Acuse de recibo) ---
            elif mensaje.startswith("__ACK__"):
                # Formato: __ACK__ <remitente_original>
                partes = mensaje.split()
                if len(partes) == 2:
                    remitente_original = partes[1]
                    if remitente_original in usuarios:
                        usuarios[remitente_original].sendall(f"[SISTEMA] {nombre_actual} ha recibido tu mensaje.".encode('utf-8'))

    except Exception as e:
        print(f"Error con {addr}: {e}")
    finally:
        if nombre_actual in usuarios:
            del usuarios[nombre_actual]
        conn.close()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor iniciado en {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()    