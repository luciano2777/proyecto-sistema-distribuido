import socket
import threading
import psutil

HOST = '127.0.0.1'
PORT = 5000

# Diccionario {ip:puerto → socket} de todos los clientes conectados
usuarios: dict[str, socket.socket] = {}
usuarios_lock = threading.Lock()


# ─────────────────────────────────────────────
# UTILIDAD DE ARRANQUE
# ─────────────────────────────────────────────

def kill_process_on_port(port: int) -> None:
    """Libera el puerto si hay un proceso previo ocupándolo."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"[SERVIDOR] Cerrando proceso previo {proc.info['name']} "
                          f"(PID: {proc.info['pid']})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


# ─────────────────────────────────────────────
# COMANDOS DE RELAY (única responsabilidad del servidor)
# ─────────────────────────────────────────────

def cmd_list(conn: socket.socket) -> None:
    """/list — devuelve los identificadores de todos los clientes conectados."""
    with usuarios_lock:
        nombres = ", ".join(usuarios.keys()) if usuarios else "Nadie"
    conn.sendall(f"[SERVIDOR] Clientes conectados: {nombres}\n".encode('utf-8'))


def cmd_send(conn: socket.socket, mensaje: str, nombre_actual: str) -> None:
    """/send <ip:puerto> <contenido> — reenvío privado entre clientes."""
    partes = mensaje.split(maxsplit=2)
    if len(partes) < 3:
        conn.sendall(b"[SERVIDOR] Uso: /send <ip:puerto> <mensaje>\n")
        return

    destino   = partes[1]
    contenido = partes[2]

    with usuarios_lock:
        socket_destino = usuarios.get(destino)

    if socket_destino:
        try:
            socket_destino.sendall(f"[{nombre_actual}]: {contenido}\n".encode('utf-8'))
            conn.sendall(f"[INFO] Enviado a {destino}.\n".encode('utf-8'))
        except Exception as e:
            conn.sendall(f"[SERVIDOR] Error al enviar a {destino}: {e}\n".encode('utf-8'))
    else:
        conn.sendall(f"[SERVIDOR] Error: {destino} no está conectado.\n".encode('utf-8'))


# ─────────────────────────────────────────────
# GESTIÓN DE CLIENTES
# ─────────────────────────────────────────────

def manejar_cliente(conn: socket.socket, addr: tuple) -> None:
    nombre_actual = f"{addr[0]}:{addr[1]}"

    with usuarios_lock:
        usuarios[nombre_actual] = conn

    print(f"[SERVIDOR] Cliente conectado: {nombre_actual}")

    # Notificar a todos los demás clientes (incluido el Monitor) que hay uno nuevo
    aviso = f"[SISTEMA] Cliente conectado como: {nombre_actual}\n".encode('utf-8')
    with usuarios_lock:
        for nombre, sock in usuarios.items():
            if nombre != nombre_actual:
                try:
                    sock.sendall(aviso)
                except Exception:
                    pass

    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break

            for linea in data.decode('utf-8').split('\n'):
                linea = linea.strip()
                if not linea:
                    continue

                if linea == "/list":
                    cmd_list(conn)

                elif linea.startswith("/send"):
                    cmd_send(conn, linea, nombre_actual)

                elif linea.startswith("/register"):
                    conn.sendall(
                        f"[SERVIDOR] Ya estás identificado como {nombre_actual}\n"
                        .encode('utf-8')
                    )

                else:
                    conn.sendall(
                        f"[SERVIDOR] Comando no reconocido: '{linea}'\n"
                        .encode('utf-8')
                    )

    except Exception as e:
        print(f"[SERVIDOR] Error con {nombre_actual}: {e}")
    finally:
        with usuarios_lock:
            usuarios.pop(nombre_actual, None)
        conn.close()
        print(f"[SERVIDOR] Cliente desconectado: {nombre_actual}")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    kill_process_on_port(PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVIDOR] Escuchando en {HOST}:{PORT}")
        print("[SERVIDOR] Solo relay TCP — sin lógica de negocio.\n")
        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=manejar_cliente,
                args=(conn, addr),
                daemon=True
            ).start()