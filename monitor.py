import socket
import threading
import json
import psutil
import os
from convertmusic import * # Configuración de red
HOST = '127.0.0.1'
PORT = 5000

# Estructuras de control globales
resultados_globales = []
total_esperado = 0
evento_completado = threading.Event()
usuarios = {}  # Formato: { "IP:Puerto": socket_connection }

# --- UTILIDADES DE SISTEMA ---
def kill_process_on_port(port):
    """Asegura que el puerto esté libre antes de iniciar el monitor."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections(kind='inet')
            for conn in connections:
                if conn.laddr.port == port:
                    print(f"[MONITOR] Liberando puerto {port} (PID: {proc.info['pid']})")
                    proc.terminate()
                    proc.wait(timeout=1)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
            pass

# --- LÓGICA DE PROCESAMIENTO DE TEXTO ---
def file_to_paragraphs(path):
    """Lee el archivo y lo divide en párrafos."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    with open(path, 'r', encoding='utf-8') as file:
        paragraphs = [p.strip() for p in file.read().split('\n\n') if p.strip()]
    return paragraphs

def parragraph_into_dictlist(path, clients_list):
    """Divide el texto equitativamente entre los clientes conectados."""
    paragraphs = file_to_paragraphs(path)
    num_clients = len(clients_list)
    
    if num_clients == 0:
        return []

    chunk_size = len(paragraphs) // num_clients
    remainder = len(paragraphs) % num_clients
    list_to_distribute = []
    start_index = 0

    for i in range(num_clients):
        end_index = start_index + chunk_size + (1 if i < remainder else 0)
        chunk = paragraphs[start_index:end_index]
        if chunk:
            list_to_distribute.append({"id": i, "text": chunk})
        start_index = end_index
    
    return list_to_distribute

# --- COMANDOS DEL MONITOR ---
def cmd_list(conn):
    """Envía la lista de nodos activos al solicitante."""
    nodos = ", ".join(usuarios.keys()) if usuarios else "Ninguno"
    conn.sendall(f"[MONITOR] Nodos activos: {nodos}\n".encode('utf-8'))

def cmd_broadcast(conn_solicitante, lista_distribucion):
    """Envía a cada cliente su parte correspondiente del procesamiento."""
    global total_esperado
    total_esperado = len(lista_distribucion)
    
    # Emparejar cada cliente con un fragmento del diccionario
    for i, (nombre_nodo, socket_nodo) in enumerate(usuarios.items()):
        if i < total_esperado:
            try:
                data_json = json.dumps(lista_distribucion[i]) + "\n"
                socket_nodo.sendall(data_json.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] No se pudo enviar datos a {nombre_nodo}: {e}")

def esperar_y_reensamblar(conn_solicitante):
    """Hilo que espera resultados, los une y genera el log final."""
    print("[MONITOR] Esperando resultados de los nodos...")
    # Espera hasta 60 segundos a que todos los nodos respondan
    finalizado = evento_completado.wait(timeout=60)
    
    if finalizado or len(resultados_globales) >= total_esperado:
        # Ordenar por ID para mantener coherencia con el texto original
        resultados_globales.sort(key=lambda x: x.get('id', 0))
        
        final_report = {
            "nodos_participantes": len(resultados_globales),
            "tokens_totales": [],
            "longitudes": [],
            "secuencia_midi": []
        }
        
        for res in resultados_globales:
            final_report["tokens_totales"].extend(res.get("tokens", []))
            final_report["longitudes"].extend(res.get("longitudes", []))
            final_report["secuencia_midi"].extend(res.get("notas_midi", []))
            
        with open("log_distribuido.json", "w") as f:
            json.dump(final_report, f, indent=4)
            
        print("[MONITOR] Archivo 'log_distribuido.json' generado con éxito.")
        conn_solicitante.sendall(b"[MONITOR] Procesamiento finalizado. Log generado.\n")
    else:
        conn_solicitante.sendall(b"[MONITOR] Error: Tiempo de espera agotado. Resultados incompletos.\n")

# --- MANEJO DE CONEXIONES ---
def manejar_nodo(conn, addr):
    nombre_nodo = f"{addr[0]}:{addr[1]}"
    usuarios[nombre_nodo] = conn
    print(f"[SISTEMA] Nodo conectado: {nombre_nodo}")
    
    global total_esperado
    
    try:
        while True:
            data = conn.recv(65536)
            if not data: break
            
            lineas = data.decode('utf-8').split('\n')
            for linea in lineas:
                if not linea.strip(): continue
                
                # Caso 1: Comandos de texto
                if linea.startswith('/'):
                    if linea.startswith('/list'):
                        cmd_list(conn)
                    elif linea.startswith('/sonar') or linea.startswith('/broadcast'):
                        try:
                            ruta = linea.split(maxsplit=1)[1]
                            lista_dist = parragraph_into_dictlist(ruta, list(usuarios.keys()))
                            
                            if not lista_dist:
                                conn.sendall(b"[MONITOR] Error: No hay nodos suficientes o archivo vacio.\n")
                                continue
                            
                            resultados_globales.clear()
                            evento_completado.clear()
                            cmd_broadcast(conn, lista_dist)
                            # Iniciar hilo de vigilancia para el reensamblaje
                            threading.Thread(target=esperar_y_reensamblar, args=(conn,), daemon=True).start()
                            
                        except Exception as e:
                            conn.sendall(f"[MONITOR] Error en comando: {e}\n".encode('utf-8'))
                
                # Caso 2: Recepción de resultados (JSON)
                else:
                    try:
                        res_dict = json.loads(linea)
                        resultados_globales.append(res_dict)
                        print(f"[LOG] Recibido fragmento {res_dict.get('id')} de {nombre_nodo}")
                        
                        if len(resultados_globales) >= total_esperado and total_esperado > 0:
                            evento_completado.set()
                    except json.JSONDecodeError:
                        # Si no es JSON, es un mensaje de chat o log
                        print(f"[{nombre_nodo}]: {linea}")

    except Exception as e:
        print(f"[ERROR] Error con nodo {nombre_nodo}: {e}")
    finally:
        if nombre_nodo in usuarios:
            del usuarios[nombre_nodo]
        conn.close()
        print(f"[SISTEMA] Nodo desconectado: {nombre_nodo}")

def iniciar_monitor():
    kill_process_on_port(PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"=== MONITOR CENTRAL INICIADO EN {HOST}:{PORT} ===")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=manejar_nodo, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    iniciar_monitor()
