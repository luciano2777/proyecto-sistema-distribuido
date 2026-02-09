import socket
import threading

HOST = '127.0.0.1'
PORT = 5000

def escuchar_servidor(conn):
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            mensaje_decodificado = data.decode('utf-8')
            print(f"\r{mensaje_decodificado}\nYou: ", end="")

            # Lógica de Acuse de Recibo
            # Si el mensaje viene de un usuario (formato "[Nombre]: mensaje")
            if mensaje_decodificado.startswith("[") and "]: " in mensaje_decodificado:
                # se extra el nombre del remitente para confirmar recepción
                try:
                    remitente = mensaje_decodificado.split("]:")[0][1:]
                    # Enviamos confirmación oculta al servidor
                    conn.sendall(f"__ACK__ {remitente}".encode('utf-8'))
                except:
                    pass
    except:
        print("\n[ERROR] Conexión perdida.")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        print("--- Chat con Confirmacion de Entrega ---")
        print("Comandos: /register <nombre> | /list | /send <nombre> <msg>")
        
        threading.Thread(target=escuchar_servidor, args=(s,), daemon=True).start()

        while True:
            msg = input("You: ")
            if msg.strip():
                s.sendall(msg.encode('utf-8'))
    except ConnectionRefusedError:
        print("No se pudo conectar al servidor.")