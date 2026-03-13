import socket
import threading
import json
import os
from convertmusic import * 
HOST = '127.0.0.1'
PORT = 5000
resultados_globales = []
total_esperado = 0
evento_completado = threading.Event()
usuarios_remotos = [] # Lista de IPs que el monitor conoce vía el servidor

# --- TUS FUNCIONES (COPIADAS TAL CUAL) ---

def cmd_list(conn):
    # En este modo, el monitor pide la lista o la deduce de los eventos
    lista_nombres = ", ".join(usuarios_remotos) if usuarios_remotos else "Buscando nodos..."
    print(f"[MONITOR] Nodos detectados en la red: {lista_nombres}")

def cmd_send(conn, mensaje, nombre_actual):
    partes = mensaje.split(maxsplit=2)
    if len(partes) == 3:
        conn.sendall(mensaje.encode('utf-8')) # El server se encarga de rutearlo

def cmd_ack(mensaje, nombre_actual):
    partes = mensaje.split()
    if len(partes) == 2:
        remitente_original = partes[1]
        print(f"[SISTEMA] {nombre_actual} ha recibido tu mensaje.")

def cmd_broadcast(conn, nombre_actual, lista_dictionary):
    # Envía los fragmentos al servidor para que los reparta
    for dict_data in lista_dictionary:
        mensaje_json = (json.dumps(dict_data) + "\n").encode('utf-8')
        conn.sendall(mensaje_json)
    print(b"[INFO] Fragmentos enviados al servidor para distribucion. \n")

def file_to_paragraphs(path):
    with open(path, 'r', encoding='utf-8') as file:
        paragraphs = file.read().strip().split('\n\n')
    return paragraphs

def parragraph_into_dictlist(path, clients):
    temp_list = file_to_paragraphs(path) 
    Lenclients = len(clients)
    if Lenclients == 0: return []
    chunk_size = len(temp_list) // Lenclients
    remainder = len(temp_list) % Lenclients
    listdict = []
    start_index = 0
    for id_client in range(Lenclients):
        end_index = start_index + chunk_size + (1 if id_client < remainder else 0)
        paragraphs = temp_list[start_index:end_index]
        if paragraphs:
            listdict.append({"id": id_client, "text": paragraphs})
        start_index = end_index
    return listdict

def esperar_y_reensamblar(conn_solicitante):
    finalizado = evento_completado.wait(timeout=30)
    if finalizado:
        resultados_globales.sort(key=lambda x: x['id'])
        final_data = {
            "tokens_totales": [],
            "longitud_tokens": [],
            "notas_midi_totales": []
        }
        for res in resultados_globales:
            final_data["tokens_totales"].extend(res.get("tokens", []))
            final_data["longitud_tokens"].extend(res.get("longitudes", []))
            final_data["notas_midi_totales"].extend(res.get("notas_midi", []))
        with open("resultado_final.json", "w") as f:
            json.dump(final_data, f, indent=4)
        print("[MONITOR] Archivo 'resultado_final.json' generado.")
    else:
        print("[MONITOR] Error: Tiempo agotado.")

# --- GESTIÓN DE RED DEL MONITOR ---

def escuchar_red(conn):
    global total_esperado
    while True:
        try:
            data = conn.recv(65536)
            if not data: break
            mensaje = data.decode('utf-8')
            
            if mensaje.startswith('{'):
                res_dict = json.loads(mensaje)
                resultados_globales.append(res_dict)
                if len(resultados_globales) >= total_esperado:
                    evento_completado.set()
            else:
                print(f"\n[RED]: {mensaje}")
                # Si llega un mensaje de identificación, lo sumamos a usuarios_remotos
                if "conectado" in mensaje.lower():
                    # Lógica simple para rastrear nodos activos
                    pass
        except: break

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        threading.Thread(target=escuchar_red, args=(s,), daemon=True).start()
        print("=== MONITOR ACTIVO - CONECTADO AL SERVIDOR ===")
        
        while True:
            op = input("Monitor> ")
            if op.startswith("/sonar") or op.startswith("/broadcast"):
                try:
                    ruta = op.split(maxsplit=1)[1]
                    # Aquí el monitor usa sus funciones locales para preparar el envío
                    # Nota: Como el Monitor no conoce a los clientes directamente,
                    # Se asume una cantidad de nodos o el Monitor envía el archivo completo
                    # para que los nodos tomen su parte según su ID.
                    lista_dict = parragraph_into_dictlist(ruta, [1, 2]) # Ejemplo con 2 nodos
                    total_esperado = len(lista_dict)
                    resultados_globales.clear()
                    evento_completado.clear()
                    cmd_broadcast(s, "Monitor", lista_dict)
                    threading.Thread(target=esperar_y_reensamblar, args=(s,), daemon=True).start()
                except Exception as e: print(f"Error: {e}")
            else:
                s.sendall(op.encode('utf-8'))