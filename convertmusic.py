import json
import time
import mido

# Función 1: Convertir valores numéricos a mensajes MIDI
def convertir_a_mensajes_midi(ruta_json):
    """
    Toma las notas del archivo JSON y las prepara como eventos MIDI 
    basados en la metodología de sonorización[cite: 14, 19].
    """
    try:
        with open(ruta_json, 'r') as f:
            data = json.load(f)
        
        notas_crudas = data.get("notas_midi_totales", [])
        mensajes_midi = []
        
        for valor in notas_crudas:
            # Se asegura que el valor esté en el rango [0, 127] según la normalización [cite: 18]
            nota = max(0, min(127, int(valor)))
            #  un mensaje de 'nota encendida' (note_on)
            mensajes_midi.append(mido.Message('note_on', note=nota, velocity=64))
            
        return mensajes_midi
    except FileNotFoundError:
        print("Error: No se encontró el archivo JSON.")
        return []

# Función 2: Hacer sonar las notas musicales
def reproducir_sonorizacion(mensajes_midi):
    """
    Envía los mensajes MIDI a un puerto de salida en tiempo real[cite: 29].
    Representa la cadencia y complejidad de la obra[cite: 8].
    """
    if not mensajes_midi:
        print("No hay notas para reproducir.")
        return

    # Abrir el puerto de salida predeterminado del sistema
    try:
        with mido.open_output() as port:
            print(f"Reproduciendo huella sonora en: {port.name}")
            
            for msg in mensajes_midi:
                print(f"Tocando nota MIDI: {msg.note}")
                port.send(msg)
                
                # Tiempo de espera entre notas para simular la cadencia métrica [cite: 23, 24]
                # Un valor de 0.3s permite distinguir la estructura
                time.sleep(0.3)
                
                # Apagar la nota para que no quede sostenida infinitamente
                port.send(mido.Message('note_off', note=msg.note, velocity=64))
                
    except IOError:
        print("Error: No se detectó un puerto de salida MIDI activo.")

# Ejecución principal
if __name__ == "__main__":
    archivo = '/home/luciano/Desktop/Universidad/12 trimesre/sistema distribuido/Proyecto/branchluciano2/folder/resultado_final.json'
    
    # Paso 1: Procesamiento de datos (Conversión)
    lista_de_notas = convertir_a_mensajes_midi(archivo)
    
    # Paso 2: Ejecución auditiva (Sonorización)
    reproducir_sonorizacion(lista_de_notas)
