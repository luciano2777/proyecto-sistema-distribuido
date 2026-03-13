import socket
import threading
import json
from convertmusic import convertir_a_mensajes_midi, reproducir_sonorizacion

HOST = '127.0.0.1'
PORT = 5000

# --- ESTADO GLOBAL DEL MONITOR ---
resultados_globales = []
total_esperado = 0
evento_completado = threading.Event()
procesadores_conocidos = []   # Lista de 'ip:puerto' de los procesadores activos


# ─────────────────────────────────────────────
# LÓGICA DE DISTRIBUCIÓN DE ARCHIVOS
# ─────────────────────────────────────────────

def file_to_paragraphs(path: str) -> list[str]:
    """Lee un archivo de texto y lo divide en párrafos (bloques separados por línea en blanco)."""
    with open(path, 'r', encoding='utf-8') as f:
        paragraphs = f.read().strip().split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]


def parragraph_into_dictlist(path: str, clients: list[str]) -> list[dict]:
    """
    Divide los párrafos del archivo entre los clientes disponibles.
    Devuelve una lista de dicts  {id, destino, text}  lista para enviar.
    """
    temp_list = file_to_paragraphs(path)
    n = len(clients)
    if n == 0:
        return []

    chunk_size = len(temp_list) // n
    remainder  = len(temp_list) % n
    listdict   = []
    start      = 0

    for i, destino in enumerate(clients):
        end = start + chunk_size + (1 if i < remainder else 0)
        chunk = temp_list[start:end]
        if chunk:
            listdict.append({"id": i, "destino": destino, "text": chunk})
        start = end

    return listdict


# ─────────────────────────────────────────────
# LÓGICA DE REENSAMBLADO Y SONORIZACIÓN
# ─────────────────────────────────────────────

def esperar_y_reensamblar(conn: socket.socket, nombre_salida: str = "resultado_final.json") -> None:
    """
    Espera a que todos los procesadores devuelvan su fragmento procesado,
    ensambla el JSON final y lanza la sonorización.
    Se ejecuta en un hilo separado para no bloquear la entrada del usuario.
    """
    finalizado = evento_completado.wait(timeout=60)

    if not finalizado:
        print("\n[MONITOR] ⚠  Timeout: algunos procesadores no respondieron a tiempo.")
        return

    resultados_globales.sort(key=lambda x: x['id'])
    final_data = {
        "tokens_totales":    [],
        "longitud_tokens":   [],
        "notas_midi_totales": []
    }
    for res in resultados_globales:
        final_data["tokens_totales"].extend(res.get("tokens", []))
        final_data["longitud_tokens"].extend(res.get("longitudes", []))
        final_data["notas_midi_totales"].extend(res.get("notas_midi", []))

    # Asegurar extensión .json
    if not nombre_salida.endswith(".json"):
        nombre_salida += ".json"

    with open(nombre_salida, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    print(f"\n[MONITOR] ✔  Procesamiento completado. '{nombre_salida}' generado.")
    print(f"[MONITOR]    Tokens totales   : {len(final_data['tokens_totales'])}")
    print(f"[MONITOR]    Notas MIDI totales: {len(final_data['notas_midi_totales'])}")

    # Sonorizar automáticamente al terminar
    cmd_sonar(nombre_salida)


def cmd_sonar(ruta_json: str) -> None:
    """Convierte el JSON de resultado en notas MIDI y las reproduce."""
    try:
        lista_de_notas = convertir_a_mensajes_midi(ruta_json)
        if lista_de_notas:
            print(f"[MONITOR] 🎵 Iniciando sonorización desde '{ruta_json}'…")
            reproducir_sonorizacion(lista_de_notas)
        else:
            print("[MONITOR] No hay notas para reproducir.")
    except FileNotFoundError:
        print(f"[MONITOR] Error: no se encontró '{ruta_json}'.")
    except Exception as e:
        print(f"[MONITOR] Error en sonorización: {e}")


# ─────────────────────────────────────────────
# DISTRIBUCIÓN DE CARGA (broadcast por /send)
# ─────────────────────────────────────────────

def cmd_broadcast(conn: socket.socket, lista_dictionary: list[dict], nombre_salida: str = "resultado_final.json") -> None:
    """
    Envía a cada procesador su fragmento de texto mediante mensajes privados
    (/send ip:puerto payload) a través del servidor, respetando la restricción
    de que el servidor solo hace relay TCP.
    """
    global total_esperado
    total_esperado = len(lista_dictionary)
    resultados_globales.clear()
    evento_completado.clear()

    for item in lista_dictionary:
        destino = item["destino"]
        payload = json.dumps({"id": item["id"], "text": item["text"]})
        comando = f"/send {destino} {payload}\n"
        conn.sendall(comando.encode('utf-8'))
        print(f"[MONITOR] → Fragmento {item['id']} enviado a {destino}")

    print(f"[MONITOR] Esperando resultados de {total_esperado} procesador(es)…")
    threading.Thread(
        target=esperar_y_reensamblar,
        args=(conn, nombre_salida),
        daemon=True
    ).start()


# ─────────────────────────────────────────────
# COMANDO config()
# ─────────────────────────────────────────────

def cmd_config(conn: socket.socket, argumento: str) -> None:
    """
    Sintaxis soportada:
      config <ruta>                        → procesa ruta, guarda en resultado_final.json
      config <nombre_salida> <ruta>        → procesa ruta, guarda en <nombre_salida>.json
      config(<ruta>, ip:puerto, …)         → sintaxis legacy con paréntesis
    """
    interior = argumento.strip()

    # ── Sintaxis legacy con paréntesis ──────────────────────────────────────
    if interior.startswith("(") and interior.endswith(")"):
        interior = interior[1:-1]
        partes   = [p.strip() for p in interior.split(",")]
        archivo  = partes[0]
        clientes = [c.strip() for c in partes[1:] if c.strip()] or list(procesadores_conocidos)
        nombre_salida = "resultado_final.json"

    # ── Sintaxis nueva: config [nombre] ruta ────────────────────────────────
    else:
        partes = interior.split(maxsplit=1)
        if len(partes) == 0:
            print("[MONITOR] Uso: config <ruta>  o  config <nombre_salida> <ruta>")
            return
        elif len(partes) == 1:
            # Solo ruta
            archivo       = partes[0]
            nombre_salida = "resultado_final.json"
        else:
            # Primer token = nombre de salida, segundo = ruta
            nombre_salida = partes[0]
            archivo       = partes[1]
        clientes = list(procesadores_conocidos)

    if not clientes:
        print("[MONITOR] Error: no hay procesadores conocidos. "
              "Conecta al menos un cliente antes de usar config.")
        return

    print(f"[MONITOR] Configurando distribución:")
    print(f"          Archivo     : {archivo}")
    print(f"          Salida      : {nombre_salida if nombre_salida.endswith('.json') else nombre_salida + '.json'}")
    print(f"          Procesadores: {clientes}")

    try:
        lista = parragraph_into_dictlist(archivo, clientes)
    except FileNotFoundError:
        print(f"[MONITOR] Error: no se encontró el archivo '{archivo}'.")
        return
    except Exception as e:
        print(f"[MONITOR] Error leyendo archivo: {e}")
        return

    if not lista:
        print("[MONITOR] El archivo está vacío o no hay procesadores disponibles.")
        return

    cmd_broadcast(conn, lista, nombre_salida)


# ─────────────────────────────────────────────
# HILO DE ESCUCHA DEL SERVIDOR
# ─────────────────────────────────────────────

def escuchar_servidor(conn: socket.socket) -> None:
    """
    Escucha todos los mensajes entrantes del servidor:
    - JSON con tokens/notas (evento_sonado de un procesador)
    - Mensajes de texto normales (logs, confirmaciones del servidor)
    """
    global total_esperado

    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break

            for linea in data.decode('utf-8').split('\n'):
                linea = linea.strip()
                if not linea:
                    continue

                # Los procesadores responden vía /send, así que el servidor
                # hace relay con el prefijo "[ip:puerto]: payload" — extraerlo
                raw = linea
                if raw.startswith("[") and "]: " in raw:
                    raw = raw.split("]: ", 1)[1]

                # ¿Es un resultado JSON de un procesador? (evento_sonado)
                if '"tokens"' in raw:
                    try:
                        resultado = json.loads(raw)
                        resultados_globales.append(resultado)
                        remitente = resultado.get('id', '?')
                        print(f"\n[MONITOR] ✔ evento_sonado recibido — fragmento ID {remitente} "
                              f"({len(resultado.get('tokens', []))} tokens)")
                        print(f"[MONITOR]   Progreso: {len(resultados_globales)}/{total_esperado}")
                        if len(resultados_globales) == total_esperado:
                            evento_completado.set()
                        print("Monitor> ", end="", flush=True)
                        continue
                    except json.JSONDecodeError:
                        pass

                # ¿Es un anuncio de nuevo cliente? (el servidor lo reenvía)
                if "[SISTEMA] Cliente conectado" in linea:
                    # Extraer ip:puerto del mensaje del servidor
                    try:
                        identificador = linea.split("como:")[1].strip()
                        if identificador not in procesadores_conocidos:
                            procesadores_conocidos.append(identificador)
                            print(f"\n[MONITOR] Nuevo procesador registrado: {identificador}")
                            print("Monitor> ", end="", flush=True)
                    except IndexError:
                        pass
                    continue

                # Mensaje de texto normal (log del servidor, confirmaciones, etc.)
                print(f"\r{linea}\nMonitor> ", end="", flush=True)

    except Exception as e:
        print(f"\n[MONITOR] Conexión perdida: {e}")


# ─────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────

def main() -> None:
    print("╔══════════════════════════════════════════╗")
    print("║   MONITOR — Nodo Orquestador (SD 2526-2) ║")
    print("╚══════════════════════════════════════════╝")
    print("Comandos disponibles:")
    print("  config <archivo>                   — distribuir archivo (guarda en resultado_final.json)")
    print("  config <nombre> <archivo>          — distribuir archivo y guardar en <nombre>.json")
    print("  /sonar <ruta_json>                 — reproducir un JSON de resultado")
    print("  /list                              — ver clientes en el servidor")
    print("  /send <ip:puerto> <mensaje>        — enviar mensaje privado")
    print("  exit                               — cerrar el monitor\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
        except ConnectionRefusedError:
            print(f"[MONITOR] No se pudo conectar al servidor en {HOST}:{PORT}. "
                  "¿Está corriendo server.py?")
            return

        print(f"[MONITOR] Conectado al servidor en {HOST}:{PORT}\n")

        threading.Thread(target=escuchar_servidor, args=(s,), daemon=True).start()

        while True:
            try:
                entrada = input("Monitor> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[MONITOR] Cerrando…")
                break

            if not entrada:
                continue

            if entrada.lower() == "exit":
                break

            # ── Comando config() ────────────────────────────────────────────
            elif entrada.lower().startswith("config"):
                resto = entrada[len("config"):].strip()
                cmd_config(s, resto)

            # ── Sonorizar manualmente un JSON ───────────────────────────────
            elif entrada.startswith("/sonar"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    print("[MONITOR] Uso: /sonar <ruta_json>")
                else:
                    cmd_sonar(partes[1].strip())

            # ── Cualquier otro comando (/list, /send…) va directo al servidor
            else:
                s.sendall((entrada + "\n").encode('utf-8'))


if __name__ == "__main__":
    main()