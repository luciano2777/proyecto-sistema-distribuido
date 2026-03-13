import socket
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
    return {
        "id": id,
        "tokens": tokens,
        "longitudes": valores,
        "notas_midi": notas_midi
    }
 
def escuchar_servidor(conn):
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break
 
            for mensaje in data.decode('utf-8').split('\n'):
                mensaje = mensaje.strip()
                if not mensaje:
                    continue
 
                # El servidor hace relay con formato "[ip:puerto]: payload"
                # — guardar el remitente (Monitor) y extraer solo el payload
                remitente = None
                raw = mensaje
                if raw.startswith("[") and "]: " in raw:
                    remitente = raw.split("]: ", 1)[0][1:]   # ip:puerto del Monitor
                    raw = raw.split("]: ", 1)[1]
 
                try:
                    datos_dict = json.loads(raw)
                    contenido = datos_dict.get("text", "")
 
                    if isinstance(contenido, list):
                        resultado_final = tokenizar_lista(contenido, datos_dict.get("id", ""))
                    else:
                        resultado_final = tokenizar(contenido, datos_dict.get("id", ""))
 
                    # Devolver el resultado al Monitor vía /send (relay del servidor)
                    if remitente:
                        payload = json.dumps(resultado_final)
                        conn.sendall(f"/send {remitente} {payload}\n".encode('utf-8'))
                        print(f"[PROCESADOR] Fragmento ID {datos_dict.get('id')} procesado → enviado a {remitente}", flush=True)
                    else:
                        # Sin remitente conocido, enviar directo (fallback)
                        conn.sendall((json.dumps(resultado_final) + "\n").encode('utf-8'))
 
                except json.JSONDecodeError:
                    # Mensaje de texto normal (logs del servidor, avisos, etc.)
                    print(mensaje, flush=True)
 
    except Exception as e:
        print(f"[ERROR] Conexión perdida: {e}")
 
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        print("[PROCESADOR] Conectado al servidor. Esperando tareas del Monitor…")
        escuchar_servidor(s)
    except ConnectionRefusedError:
        print("[PROCESADOR] No se pudo conectar al servidor.")