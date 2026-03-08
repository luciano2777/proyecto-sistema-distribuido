import socket
import threading
import json
import psutil
from convertmusic import * 
HOST = '127.0.0.1'
PORT = 5000
resultados_globales = []
esperando_resultados = False
total_esperado = 0
evento_completado = threading.Event()
# Diccionario para almacenar {nombre: socket_connection}
usuarios = {}
# --- FUNCIONES PARA EVITAR ERRORES---
def kill_process_on_port(port):
    """Encuentra y termina procesos que estén usando el puerto especificado."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections(kind='inet')
            for conn in connections:
                if conn.laddr.port == port:
                    print(f"[SISTEMA] Cerrando proceso previo {proc.info['name']} (PID: {proc.info['pid']})")
                    
                    # 1. Intentar terminación suave
                    proc.terminate()
                    
                    try:
                        # Esperar un momento corto
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        # 2. Si no cierra, forzar el cierre (SIGKILL)
                        print(f"[SISTEMA] El proceso no respondió, forzando kill...")
                        proc.kill()
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
# --- FUNCIONES DE COMANDOS ---

def cmd_register(conn, mensaje, nombre_actual):
    partes = mensaje.split()
    if len(partes) == 2:
        nombre = partes[1]
        if nombre in usuarios:
            conn.sendall(b"[SERVER] Error: El nombre ya existe.")
            return nombre_actual
        else:
            usuarios[nombre] = conn
            conn.sendall(f"[SERVER] Registrado como {nombre}".encode('utf-8'))
            return nombre
    else:
        conn.sendall(b"[SERVER] Uso: /register <nombre>")
        return nombre_actual

def cmd_list(conn):
    lista_nombres = ", ".join(usuarios.keys()) if usuarios else "Nadie"
    conn.sendall(f"[SERVER] Usuarios conectados: {lista_nombres}".encode('utf-8'))

def cmd_send(conn, mensaje, nombre_actual):
    if not nombre_actual:
        conn.sendall(b"[SERVER] Error: Debes registrarte primero.")
        return
    
    partes = mensaje.split(maxsplit=2)
    if len(partes) == 3:
        destino = partes[1]
        contenido = partes[2]
        
        if destino in usuarios:
            # Se envía el mensaje al destino con el nombre del remitente
            usuarios[destino].sendall(f"[{nombre_actual}]: {contenido}".encode('utf-8'))
            conn.sendall(f"[INFO] Enviando a {destino}...".encode('utf-8'))
        else:
            conn.sendall(f"[SERVER] Error: {destino} no esta conectado.".encode('utf-8'))
    else:
        conn.sendall(b"[SERVER] Uso: /send <usuario> <mensaje>")

def cmd_ack(mensaje, nombre_actual):
    partes = mensaje.split()
    if len(partes) == 2:
        remitente_original = partes[1]
        if remitente_original in usuarios:
            usuarios[remitente_original].sendall(f"[SISTEMA] {nombre_actual} ha recibido tu mensaje.".encode('utf-8'))

# -- PARTES PARA MANDAR EL TEXTO
# Esto servirá para repartir los parrafos entre los clientes.
def cmd_broadcast(conn, nombre_actual, lista_dictionary):
    if not nombre_actual:
        conn.sendall(b"[SERVER] Error: Debes registrarte primero.")
        return# Join all parts after the command into one message
    size_lista = len(lista_dictionary)
    conteo = 0
    # The For Loop: Iterating through the dictionary
    for nombre, cliente_socket in usuarios.items():
        if  conteo < size_lista:  # Optional: don't send to self
            try:
                conteo += 1
                
                dict_data = lista_dictionary[conteo -1]
                # Inside cmd_broadcast
                mensaje_json = (json.dumps(dict_data) + "\n").encode('utf-8') # Added \n
                cliente_socket.sendall(mensaje_json)
                
            except Exception as e:
                print(f"Error enviando a {nombre}: {e}")
    
    conn.sendall(b"[INFO] Mensaje enviado a todos. \n")
    
def parragraph_into_dictlist(path, clients):
    # 'list' contains all paragraphs in order
    temp_list = file_to_paragraphs(path) 
    
    Lenclients = len(clients)
    if Lenclients == 0:
        return []

    # Calculate how many paragraphs per client
    # total paragraphs / total clients
    chunk_size = len(temp_list) // Lenclients
    remainder = len(temp_list) % Lenclients

    listdict = []
    start_index = 0

    for id_client in range(Lenclients):
        # Determine the end point for this specific client's chunk
        # We add 1 extra paragraph to the early clients if there is a remainder
        end_index = start_index + chunk_size + (1 if id_client < remainder else 0)
        
        # Grab the contiguous chunk of text
        paragraphs = temp_list[start_index:end_index]
        
        if paragraphs:
            data = {
                "id": id_client,
                "text": paragraphs 
            }       
            listdict.append(data)
        
        # Move the starting point for the next client
        start_index = end_index

    return listdict
def file_to_paragraphs(path):
    with open(path, 'r', encoding='utf-8') as file:
        
        paragraphs = file.read().strip().split('\n\n')
    return paragraphs

# reensamblar
def esperar_y_reensamblar(conn_solicitante):
    # Esta función se queda "escuchando" hasta que la lista se llene
    finalizado = evento_completado.wait(timeout=30)
    
    if finalizado:
        # Ordenar por ID para reconstruir el orden original del archivo
        resultados_globales.sort(key=lambda x: x['id'])
        
        # Consolidar los datos de todos los clientes
        final_data = {
            "tokens_totales": [],
            "longitud_tokens": [],
            "notas_midi_totales": []
        }
        for res in resultados_globales:
            final_data["tokens_totales"].extend(res.get("tokens", []))
            final_data["longitud_tokens"].extend(res.get("longitudes", []))
            final_data["notas_midi_totales"].extend(res.get("notas_midi", []))
            
        # Guardar el resultado en un archivo físico
        with open("resultado_final.json", "w") as f:
            json.dump(final_data, f, indent=4)
        
        conn_solicitante.sendall(b"[SERVER] Procesamiento completado. Archivo 'resultado_final.json' generado.")
    else:
        conn_solicitante.sendall(b"[SERVER] Error: Algunos clientes no respondieron a tiempo.")
# --- LÓGICA DEL SERVIDOR ---

def manejar_cliente(conn, addr):
    nombre_actual = None
    global total_esperado
    try:
        while True:
            data = conn.recv(65536)
            if not data: break
            
            # Split by newline on the server side too
            mensajes = data.decode('utf-8').split('\n')
            
            for mensaje in mensajes:
                mensaje = mensaje.strip()
                if not mensaje: 
                    continue
                
                if mensaje.startswith('{') and '"tokens"' in mensaje:
                    try:
                        resultado = json.loads(mensaje)
                        resultados_globales.append(resultado)
                        print(f"[SISTEMA] Recibido fragmento ID: {resultado.get('id')} de {nombre_actual}")
                        
                        # Si ya tenemos todos, avisamos al hilo principal
                        if len(resultados_globales) == total_esperado:
                            evento_completado.set()
                        continue # Pasamos al siguiente mensaje en el bucle
                    except json.JSONDecodeError:
                        pass

                if mensaje.startswith("/register"):
                    nombre_actual = cmd_register(conn, mensaje, nombre_actual)

                elif mensaje == "/list":
                    cmd_list(conn)

                elif mensaje.startswith("/send"):
                    cmd_send(conn, mensaje, nombre_actual)
                    
                elif mensaje.startswith("/sonar"):
                    # Dividir el mensaje en comando y ruta (maxsplit=1 para no romper rutas con espacios)
                    partes = mensaje.split(maxsplit=1)
                    
                    if len(partes) < 2:
                        conn.sendall(b"[SERVER] Uso: /sonar <ruta_absoluta_del_archivo>\n")
                        continue
                        
                    # Extraer la ruta ingresada por el usuario
                    contenido = partes[1].strip()
                    
                    try:
                        # Intentar leer el archivo y hacerlo sonar
                        lista_de_notas = convertir_a_mensajes_midi(contenido)
    
                        # Paso 2: Ejecución auditiva (Sonorización)
                        reproducir_sonorizacion(lista_de_notas)
                        pass
                        
                    except FileNotFoundError:
                        # Evitar que el servidor colapse si el usuario escribe mal la ruta
                        mensaje_error = f"[SERVER] Error: No se encontro el archivo en la ruta '{contenido}'.\n"
                        conn.sendall(mensaje_error.encode('utf-8'))
                    except Exception as e:
                        mensaje_error = f"[SERVER] Error inesperado al procesar el archivo: {e}\n"
                        conn.sendall(mensaje_error.encode('utf-8'))

                elif mensaje.startswith("/broadcast"):
                    # Dividir el mensaje en comando y ruta (maxsplit=1 para no romper rutas con espacios)
                    partes = mensaje.split(maxsplit=1)
                    
                    if len(partes) < 2:
                        conn.sendall(b"[SERVER] Uso: /broadcast <ruta_absoluta_del_archivo>\n")
                        continue
                        
                    # Extraer la ruta ingresada por el usuario
                    contenido = partes[1].strip()
                    
                    try:
                        # Intentar leer el archivo y repartirlo
                        lista_dictionary = parragraph_into_dictlist(contenido, usuarios)
                        
                        total_esperado = len(lista_dictionary)
                        
                        # Evitar lanzar el proceso si no hay clientes o el archivo está vacío
                        if total_esperado == 0:
                            conn.sendall(b"[SERVER] Error: Archivo vacio o no hay clientes conectados.\n")
                            continue

                        # Limpiar los datos de sesiones anteriores
                        resultados_globales.clear()
                        evento_completado.clear()
                        print(f"[SISTEMA] Preparando broadcast para archivo: {contenido}")
                        
                        cmd_broadcast(conn, nombre_actual, lista_dictionary)
                        threading.Thread(target=esperar_y_reensamblar, args=(conn,), daemon=True).start()
                        
                    except FileNotFoundError:
                        # Evitar que el servidor colapse si el usuario escribe mal la ruta
                        mensaje_error = f"[SERVER] Error: No se encontro el archivo en la ruta '{contenido}'.\n"
                        conn.sendall(mensaje_error.encode('utf-8'))
                    except Exception as e:
                        mensaje_error = f"[SERVER] Error inesperado al procesar el archivo: {e}\n"
                        conn.sendall(mensaje_error.encode('utf-8'))
                    
                elif mensaje.startswith("__ACK__"):
                    cmd_ack(mensaje, nombre_actual)
                    
    except Exception as e:
        print(f"Error con {addr}: {e}")
    finally:
        if nombre_actual and nombre_actual in usuarios:
            del usuarios[nombre_actual]
        conn.close()

# --- INICIO DEL PROGRAMA ---

if __name__ == "__main__":
    kill_process_on_port(PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor iniciado en {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            print(f"Nueva conexión desde {addr}")
            threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()