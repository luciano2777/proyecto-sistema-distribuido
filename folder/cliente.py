import socket
import threading
import json
from Tokenizador import *
HOST = '127.0.0.1'
PORT = 5000

def tokenizar_lista(lista_parrafos, id):
    # Initialize empty lists to accumulate data
    all_tokens = []
    all_valores = []
    all_midi = []

    for parrafo in lista_parrafos:
        # Process each paragraph individually
        tokens, valores, notas_midi = pipeline_palabras(
            parrafo, 
            metrica="longitud", 
            normalizar=True
        )
        # Extend the main lists with the new data
        all_tokens.extend(tokens)
        all_valores.extend(valores)
        all_midi.extend(notas_midi)

    # Return the final consolidated object
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
)# 2. Ver el resultado
    print(f"Tokens: {tokens}")        # ['en', 'un', 'lugar', 'de', 'la']
    print(f"Longitudes: {valores}")   # [2, 2, 5, 2, 2]
    print(f"Notas MIDI: {notas_midi}") # [0, 0, 127, 0, 0] (Normalizado a 0-127)
    newobject = {
        "id": id,
        "tokens": tokens,
        "longitudes":valores,
        "notas_midi":notas_midi
    }
    return newobject
    pass
def escuchar_servidor(conn):
    try:
        while True:
            data = conn.recv(65536)
            if not data: break
            
            mensaje_decodificado = data.decode('utf-8')
            
            # Check if the message is a JSON dictionary
            try:
                datos_dict = json.loads(mensaje_decodificado)
                contenido = datos_dict.get("text", "")

                if isinstance(contenido, list):
                    # It's a list of paragraphs!
                    resultado_final = tokenizar_lista(contenido, datos_dict.get("id", ""))
                else:
                    # It's just a single string
                    resultado_final = tokenizar(contenido, datos_dict.get("id", ""))
                print(f"Tokens: {resultado_final.get("tokens")}")        # ['en', 'un', 'lugar', 'de', 'la']
                print(f"Longitudes: {resultado_final.get("longitudes")}")   # [2, 2, 5, 2, 2]
                print(f"Notas MIDI: {resultado_final.get("notas_midi")}")
                # Send the single consolidated dictionary back
                conn.sendall(json.dumps(resultado_final).encode('utf-8'))

                
            except json.JSONDecodeError:
                # If it's not JSON, handle it as a normal message
                print(f"\r{mensaje_decodificado}\nYou: ", end="", flush=True)

                # Mantain your ACK logic for regular chat messages
                if mensaje_decodificado.startswith("[") and "]: " in mensaje_decodificado:
                    try:
                        remitente = mensaje_decodificado.split("]:")[0][1:]
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