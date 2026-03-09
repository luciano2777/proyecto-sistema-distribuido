import socket
import threading
import json
from Tokenizador import *
HOST = '127.0.0.1'
PORT = 5000

def tokenizar_lista(lista_parrafos, id):
    all_tokens = []
    all_valores = []
    all_midi = []
    for parrafo in lista_parrafos:
        tokens, valores, notas_midi = pipeline_palabras(
            parrafo, 
            metrica="longitud", 
            normalizar=True
        )
        all_tokens.extend(tokens)
        all_valores.extend(valores)
        all_midi.extend(notas_midi)
    return {
        "id": id,
        "tokens": all_tokens,
        "longitudes": all_valores,
        "notas_midi": all_midi
    }

def tokenizar(texto_ejemplo, id):
    tokens, valores, notas_midi = pipeline_palabras(
        texto_ejemplo, 
        metrica="longitud", 
        normalizar=True
    )
    print(f"Tokens: {tokens}")
    print(f"Longitudes: {valores}")
    print(f"Notas MIDI: {notas_midi}")
    return {
        "id": id,
        "tokens": tokens,
        "longitudes":valores,
        "notas_midi":notas_midi
    }

def escuchar_servidor(conn):
    try:
        while True:
            data = conn.recv(65536)
            if not data: break
            
            mensajes = data.decode('utf-8').split('\n')
            for mensaje_decodificado in mensajes:
                if not mensaje_decodificado.strip():
                    continue 
                
                try:
                    datos_dict = json.loads(mensaje_decodificado)
                    contenido = datos_dict.get("text", "")

                    if isinstance(contenido, list):
                        resultado_final = tokenizar_lista(contenido, datos_dict.get("id", ""))
                    else:
                        resultado_final = tokenizar(contenido, datos_dict.get("id", ""))
                        
                    respuesta = json.dumps(resultado_final) + "\n"
                    conn.sendall(respuesta.encode('utf-8'))
                    
                except json.JSONDecodeError:
                    print(f"\r{mensaje_decodificado}\nYou: ", end="", flush=True)

                    if mensaje_decodificado.startswith("[") and "]: " in mensaje_decodificado:
                        try:
                            # Extrae el identificador IP:Port del remitente
                            remitente = mensaje_decodificado.split("]:")[0][1:]
                            conn.sendall(f"__ACK__ {remitente}\n".encode('utf-8'))
                        except:
                            pass
    except Exception as e:
        print(f"\n[ERROR] Conexión perdida: {e}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        print("--- Chat por IP (Confirmacion de Entrega) ---")
        print("Comandos: /list | /send <ip:puerto> <msg> | /broadcast <ruta> | /sonar <ruta>")
        
        threading.Thread(target=escuchar_servidor, args=(s,), daemon=True).start()

        while True:
            msg = input("You: ")
            if msg.strip():
                s.sendall(msg.encode('utf-8'))
    except ConnectionRefusedError:
        print("No se pudo conectar al servidor.")