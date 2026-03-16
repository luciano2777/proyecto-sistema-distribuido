import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from datetime import datetime
import threading, queue, json, os, time

# Modulo
import sys
from monitor import cmd_config, cmd_sonar, procesadores_conocidos
from convertmusic import convertir_a_mensajes_midi, reproducir_sonorizacion
import server
from monitor import main as monitor_main
import cliente

sys.path.append(os.path.dirname(__file__))  # Asegurar que encuentra tus módulos

class AplicacionMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Distribuido de Análisis Auditivo - Proyecto SD 2526-2")
        self.root.geometry("900x700")
        
        # Variables de control
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.IntVar(value=5000)
        self.conectado = False
        self.procesadores = []
        self.resultados_parciales = []
        
        # Cola para comunicación entre hilos
        self.cola_mensajes = queue.Queue()
        
        self.crear_menu()
        self.crear_widgets()
        self.procesar_cola()

    def crear_menu(self):
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
        
            # Menú Archivo
            menu_archivo = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Archivo", menu=menu_archivo)
            menu_archivo.add_command(label="Abrir archivo de texto", command=self.seleccionar_archivo)
            menu_archivo.add_command(label="Abrir JSON existente", command=self.cargar_json)
            menu_archivo.add_separator()
            menu_archivo.add_command(label="Salir", command=self.root.quit)
            
            # Menú Servidor
            menu_servidor = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Servidor", menu=menu_servidor)
            menu_servidor.add_command(label="Conectar", command=self.conectar_servidor)
            menu_servidor.add_command(label="Desconectar", command=self.desconectar_servidor)
            menu_servidor.add_command(label="Listar procesadores", command=self.listar_procesadores)
            
            # Menú Ayuda
            menu_ayuda = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Ayuda", menu=menu_ayuda)
            menu_ayuda.add_command(label="Acerca de", command=self.mostrar_acerca)

    def crear_widgets(self):
            # Frame superior para conexión
            self.crear_frame_conexion()
            
            # Notebook para pestañas
            self.notebook = ttk.Notebook(self.root)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Crear las pestañas
            self.crear_pestania_monitor()
            self.crear_pestania_procesadores()
            self.crear_pestania_sonorizacion()
            self.crear_pestania_visualizacion()
            
            # Área de log (común a todas)
            self.crear_area_log()
            
            # Barra de estado
            self.crear_barra_estado()

    def crear_frame_conexion(self):
                frame_conexion = ttk.LabelFrame(self.root, text="Conexión al Servidor", padding=5)
                frame_conexion.pack(fill=tk.X, padx=5, pady=5)
                
                ttk.Label(frame_conexion, text="IP:").grid(row=0, column=0, padx=2)
                ttk.Entry(frame_conexion, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=2)
                
                ttk.Label(frame_conexion, text="Puerto:").grid(row=0, column=2, padx=2)
                ttk.Entry(frame_conexion, textvariable=self.port_var, width=8).grid(row=0, column=3, padx=2)
                
                self.btn_conectar = ttk.Button(frame_conexion, text="Conectar", command=self.conectar_servidor)
                self.btn_conectar.grid(row=0, column=4, padx=5)
                
                self.led_estado = tk.Canvas(frame_conexion, width=20, height=20)
                self.led_estado.grid(row=0, column=5, padx=5)
                self.actualizar_led("rojo")
                
                frame_conexion.columnconfigure(6, weight=1)

    def crear_pestania_monitor(self):
                pestania = ttk.Frame(self.notebook)
                self.notebook.add(pestania, text="Monitor")
                
                # Frame para selección de archivo
                frame_archivo = ttk.LabelFrame(pestania, text="Archivo a procesar", padding=5)
                frame_archivo.pack(fill=tk.X, padx=5, pady=5)
                
                self.ruta_archivo_var = tk.StringVar()
                ttk.Entry(frame_archivo, textvariable=self.ruta_archivo_var, width=50).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
                ttk.Button(frame_archivo, text="Examinar...", command=self.seleccionar_archivo).pack(side=tk.RIGHT, padx=2)
                
                # Frame para configuración de salida
                frame_salida = ttk.LabelFrame(pestania, text="Archivo de salida", padding=5)
                frame_salida.pack(fill=tk.X, padx=5, pady=5)
                
                ttk.Label(frame_salida, text="Nombre:").pack(side=tk.LEFT, padx=2)
                self.nombre_salida_var = tk.StringVar(value="resultado_final")
                ttk.Entry(frame_salida, textvariable=self.nombre_salida_var, width=30).pack(side=tk.LEFT, padx=2)
                ttk.Label(frame_salida, text=".json").pack(side=tk.LEFT)
                
                # Botón de procesamiento
                frame_botones = ttk.Frame(pestania)
                frame_botones.pack(fill=tk.X, padx=5, pady=5)
                
                self.btn_procesar = ttk.Button(frame_botones, text="Iniciar Procesamiento (config)", 
                                            command=self.iniciar_procesamiento, state=tk.DISABLED)
                self.btn_procesar.pack(side=tk.LEFT, padx=5)
                
                # Barra de progreso
                self.progreso = ttk.Progressbar(frame_botones, length=300, mode='determinate')
                self.progreso.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
                
                # Lista de procesadores detectados
                frame_lista = ttk.LabelFrame(pestania, text="Procesadores conectados", padding=5)
                frame_lista.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                self.tree_procesadores = ttk.Treeview(frame_lista, columns=("estado", "fragmentos"), height=5)
                self.tree_procesadores.heading("#0", text="ID (ip:puerto)")
                self.tree_procesadores.heading("estado", text="Estado")
                self.tree_procesadores.heading("fragmentos", text="Fragmentos")
                self.tree_procesadores.column("#0", width=200)
                self.tree_procesadores.column("estado", width=100)
                self.tree_procesadores.column("fragmentos", width=80)
                
                scroll_tree = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree_procesadores.yview)
                self.tree_procesadores.configure(yscrollcommand=scroll_tree.set)
                
                self.tree_procesadores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scroll_tree.pack(side=tk.RIGHT, fill=tk.Y)

    def crear_pestania_procesadores(self):
        pestania = ttk.Frame(self.notebook)
        self.notebook.add(pestania, text="Procesadores")
        
        # Canvas con scroll para tarjetas de procesadores
        canvas = tk.Canvas(pestania)
        scrollbar = ttk.Scrollbar(pestania, orient="vertical", command=canvas.yview)
        self.frame_procesadores = ttk.Frame(canvas)
        
        self.frame_procesadores.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.frame_procesadores, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Aquí se agregarán dinámicamente los frames de cada procesador
        self.procesador_widgets = {}
    
    def crear_pestania_sonorizacion(self):
        pestania = ttk.Frame(self.notebook)
        self.notebook.add(pestania, text="Sonorización")
        
        # Frame para carga de JSON
        frame_json = ttk.LabelFrame(pestania, text="Archivo JSON", padding=5)
        frame_json.pack(fill=tk.X, padx=5, pady=5)
        
        self.ruta_json_var = tk.StringVar()
        ttk.Entry(frame_json, textvariable=self.ruta_json_var, width=50).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ttk.Button(frame_json, text="Cargar JSON", command=self.cargar_json).pack(side=tk.RIGHT, padx=2)
        
        # Controles de reproducción
        frame_controles = ttk.LabelFrame(pestania, text="Controles de reproducción", padding=5)
        frame_controles.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_controles, text="▶ Play", command=self.reproducir_sonido).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_controles, text="⏸ Pause", command=self.pausar_sonido).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_controles, text="⏹ Stop", command=self.detener_sonido).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame_controles, text="Velocidad:").pack(side=tk.LEFT, padx=(20, 2))
        self.velocidad_var = tk.DoubleVar(value=0.3)
        ttk.Scale(frame_controles, from_=0.1, to=1.0, variable=self.velocidad_var, orient=tk.HORIZONTAL, length=100).pack(side=tk.LEFT, padx=2)
        
        # Visualizador MIDI simple
        frame_visual = ttk.LabelFrame(pestania, text="Visualizador MIDI", padding=5)
        frame_visual.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas_midi = tk.Canvas(frame_visual, bg='white', height=150)
        self.canvas_midi.pack(fill=tk.BOTH, expand=True)
        
        # Vista previa de notas
        frame_preview = ttk.LabelFrame(pestania, text="Vista previa de notas", padding=5)
        frame_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_preview = scrolledtext.ScrolledText(frame_preview, height=5)
        self.text_preview.pack(fill=tk.BOTH, expand=True)

    def crear_pestania_visualizacion(self):
        pestania = ttk.Frame(self.notebook)
        self.notebook.add(pestania, text="Visualización")
        
        # Frame para cargar dos obras
        frame_comparacion = ttk.LabelFrame(pestania, text="Comparación de obras", padding=5)
        frame_comparacion.pack(fill=tk.X, padx=5, pady=5)
        
        # Obra 1
        ttk.Label(frame_comparacion, text="Obra 1:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.obra1_var = tk.StringVar()
        ttk.Entry(frame_comparacion, textvariable=self.obra1_var, width=30).grid(row=0, column=1, padx=2)
        ttk.Button(frame_comparacion, text="Cargar", command=lambda: self.cargar_obra_comparacion(1)).grid(row=0, column=2, padx=2)
        
        # Obra 2
        ttk.Label(frame_comparacion, text="Obra 2:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.obra2_var = tk.StringVar()
        ttk.Entry(frame_comparacion, textvariable=self.obra2_var, width=30).grid(row=1, column=1, padx=2)
        ttk.Button(frame_comparacion, text="Cargar", command=lambda: self.cargar_obra_comparacion(2)).grid(row=1, column=2, padx=2)
        
        ttk.Button(frame_comparacion, text="Comparar", command=self.comparar_obras).grid(row=2, column=0, columnspan=3, pady=5)
        
        # Área de resultados comparativos
        frame_resultados = ttk.LabelFrame(pestania, text="Resultados comparativos", padding=5)
        frame_resultados.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_comparacion = scrolledtext.ScrolledText(frame_resultados)
        self.text_comparacion.pack(fill=tk.BOTH, expand=True)
    
    def crear_area_log(self):
        frame_log = ttk.LabelFrame(self.root, text="Log del sistema", padding=5)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_log = scrolledtext.ScrolledText(frame_log, height=8)
        self.text_log.pack(fill=tk.BOTH, expand=True)
        
        frame_log_botones = ttk.Frame(frame_log)
        frame_log_botones.pack(fill=tk.X, pady=2)
        
        ttk.Button(frame_log_botones, text="Limpiar log", command=self.limpiar_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(frame_log_botones, text="Exportar log", command=self.exportar_log).pack(side=tk.LEFT, padx=2)
    
    def crear_barra_estado(self):
        self.barra_estado = ttk.Label(self.root, text="Listo | No conectado | Procesadores: 0", 
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.barra_estado.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def actualizar_led(self, color):
        self.led_estado.delete("all")
        if color == "verde":
            self.led_estado.create_oval(2, 2, 18, 18, fill="green", outline="darkgreen")
        else:
            self.led_estado.create_oval(2, 2, 18, 18, fill="red", outline="darkred")
    
    def conectar_servidor(self):
        if not self.conectado:
            self.agregar_log(f"Conectando a {self.host_var.get()}:{self.port_var.get()}...")
            
            # Aquí implementarías la conexión real usando tu código de monitor.py
            # Por ahora simulamos conexión exitosa
            self.conectado = True
            self.actualizar_led("verde")
            self.btn_conectar.config(text="Desconectar")
            self.btn_procesar.config(state=tk.NORMAL)
            self.agregar_log("✓ Conectado al servidor")
            
            # Iniciar hilo para simular recepción de procesadores
            self.iniciar_simulacion_procesadores()
        else:
            self.desconectar_servidor()
    
    def desconectar_servidor(self):
        self.conectado = False
        self.actualizar_led("rojo")
        self.btn_conectar.config(text="Conectar")
        self.btn_procesar.config(state=tk.DISABLED)
        self.agregar_log("Desconectado del servidor")
    
    def listar_procesadores(self):
        if self.conectado:
            # Aquí enviarías el comando /list al servidor
            self.agregar_log("Solicitando lista de procesadores...")

    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de texto",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.ruta_archivo_var.set(archivo)
            self.agregar_log(f"Archivo seleccionado: {archivo}")
    
    def cargar_json(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.ruta_json_var.set(archivo)
            self.agregar_log(f"JSON cargado: {archivo}")
            self.mostrar_preview_json(archivo)
    
    def cargar_obra_comparacion(self, num_obra):
        archivo = filedialog.askopenfilename(
            title=f"Seleccionar JSON para Obra {num_obra}",
            filetypes=[("Archivos JSON", "*.json")]
        )
        if archivo:
            if num_obra == 1:
                self.obra1_var.set(archivo)
            else:
                self.obra2_var.set(archivo)
            self.agregar_log(f"Obra {num_obra} cargada: {archivo}")
    
    def mostrar_preview_json(self, ruta):
        try:
            with open(ruta, 'r') as f:
                data = json.load(f)
            
            self.text_preview.delete(1.0, tk.END)
            notas = data.get("notas_midi_totales", [])
            tokens = data.get("tokens_totales", [])
            
            preview = f"Total de notas: {len(notas)}\n"
            preview += f"Total de tokens: {len(tokens)}\n"
            preview += f"Primeras 10 notas: {notas[:10]}\n"
            
            self.text_preview.insert(tk.END, preview)
        except Exception as e:
            self.agregar_log(f"Error al cargar JSON: {e}")

    def iniciar_procesamiento(self):
        if not self.ruta_archivo_var.get():
            messagebox.showerror("Error", "Debe seleccionar un archivo de texto")
            return
        
        if not self.tree_procesadores.get_children():
            messagebox.showwarning("Advertencia", "No hay procesadores conectados")
            return
        
        self.agregar_log(f"Iniciando procesamiento de: {self.ruta_archivo_var.get()}")
        self.agregar_log(f"Archivo de salida: {self.nombre_salida_var.get()}.json")
        
        # Simular progreso (reemplazar con llamada real a monitor.cmd_config)
        self.progreso['value'] = 0
        self.simular_progreso()
    
    def reproducir_sonido(self):
        if not self.ruta_json_var.get():
            messagebox.showerror("Error", "Debe cargar un archivo JSON")
            return
        
        self.agregar_log(f"Reproduciendo: {self.ruta_json_var.get()}")
        # Aquí llamarías a convertmusic.reproducir_sonorizacion
        # Pero en un hilo separado para no bloquear la GUI
        
        # Simulación visual
        self.simular_reproduccion()
    
    def simular_reproduccion(self):
        def animar():
            for i in range(20):
                if hasattr(self, 'reproduciendo') and not self.reproduciendo:
                    break
                self.cola_mensajes.put(("nota", i * 6))  # 0-120 aprox
                time.sleep(0.2)
        
        self.reproduciendo = True
        threading.Thread(target=animar, daemon=True).start()
    
    def pausar_sonido(self):
        self.reproduciendo = False
        self.agregar_log("Reproducción pausada")
    
    def detener_sonido(self):
        self.reproduciendo = False
        self.canvas_midi.delete("all")
        self.agregar_log("Reproducción detenida")
    
    def comparar_obras(self):
        if not self.obra1_var.get() or not self.obra2_var.get():
            messagebox.showerror("Error", "Debe cargar ambas obras")
            return
        
        self.text_comparacion.delete(1.0, tk.END)
        
        try:
            with open(self.obra1_var.get(), 'r') as f:
                data1 = json.load(f)
            with open(self.obra2_var.get(), 'r') as f:
                data2 = json.load(f)
            
            notas1 = data1.get("notas_midi_totales", [])
            notas2 = data2.get("notas_midi_totales", [])
            
            comparacion = "=== COMPARACIÓN DE OBRAS ===\n\n"
            comparacion += f"Obra 1 - Total notas: {len(notas1)}\n"
            comparacion += f"Obra 2 - Total notas: {len(notas2)}\n\n"
            
            if notas1 and notas2:
                comparacion += f"Promedio Obra 1: {sum(notas1)/len(notas1):.2f}\n"
                comparacion += f"Promedio Obra 2: {sum(notas2)/len(notas2):.2f}\n"
                comparacion += f"Desviación Obra 1: {self.calcular_desviacion(notas1):.2f}\n"
                comparacion += f"Desviación Obra 2: {self.calcular_desviacion(notas2):.2f}\n"
            
            self.text_comparacion.insert(tk.END, comparacion)
            
        except Exception as e:
            self.agregar_log(f"Error al comparar: {e}")
    
    def calcular_desviacion(self, notas):
        if not notas:
            return 0
        media = sum(notas) / len(notas)
        varianza = sum((x - media) ** 2 for x in notas) / len(notas)
        return varianza ** 0.5
    
    def agregar_log(self, mensaje):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_log.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.text_log.see(tk.END)
        self.actualizar_barra_estado()
    
    def limpiar_log(self):
        self.text_log.delete(1.0, tk.END)
    
    def exportar_log(self):
        archivo = filedialog.asksaveasfilename(
            title="Guardar log",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt")]
        )
        if archivo:
            with open(archivo, 'w') as f:
                f.write(self.text_log.get(1.0, tk.END))
            self.agregar_log(f"Log exportado a: {archivo}")
    
    def actualizar_barra_estado(self):
        estado = f"Listo | "
        estado += f"{'Conectado' if self.conectado else 'No conectado'} | "
        estado += f"Procesadores: {len(self.tree_procesadores.get_children())}"
        self.barra_estado.config(text=estado)
    
    def procesar_cola(self):
        """Procesa mensajes de la cola (ejecutar en hilo principal)"""
        try:
            while True:
                mensaje = self.cola_mensajes.get_nowait()
                
                if mensaje[0] == "nuevo_procesador":
                    self.agregar_procesador(mensaje[1])
                elif mensaje[0] == "progreso":
                    self.progreso['value'] = mensaje[1]
                elif mensaje[0] == "procesamiento_completado":
                    self.progreso['value'] = 100
                    self.agregar_log(f"✓ Procesamiento completado: {mensaje[1]}")
                    self.ruta_json_var.set(mensaje[1])
                    messagebox.showinfo("Completado", f"Procesamiento finalizado.\nArchivo: {mensaje[1]}")
                elif mensaje[0] == "nota":
                    self.dibujar_nota_midi(mensaje[1])
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.procesar_cola)
    
    def agregar_procesador(self, id_procesador):
        if id_procesador not in [self.tree_procesadores.item(item)['text'] 
                                 for item in self.tree_procesadores.get_children()]:
            self.tree_procesadores.insert("", tk.END, text=id_procesador, 
                                         values=("Conectado", "0"))
            self.agregar_log(f"Nuevo procesador detectado: {id_procesador}")
            self.actualizar_barra_estado()
            
            # También agregar a la pestaña de procesadores
            self.agregar_tarjeta_procesador(id_procesador)
    
    def agregar_tarjeta_procesador(self, id_procesador):
        frame = ttk.LabelFrame(self.frame_procesadores, text=id_procesador)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(frame, text="Estado:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text="Conectado", foreground="green").grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(frame, text="Fragmentos:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(frame, text="0").grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(frame, text="Última nota:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(frame, text="---").grid(row=2, column=1, sticky=tk.W)
        
        ttk.Button(frame, text="Detener", 
                  command=lambda: self.detener_procesador(id_procesador)).grid(row=3, column=0, columnspan=2, pady=2)
        
        self.procesador_widgets[id_procesador] = frame
    
    def detener_procesador(self, id_procesador):
        self.agregar_log(f"Deteniendo procesador: {id_procesador}")
        # Aquí implementarías la lógica para desconectar/eliminar el procesador
    
    def dibujar_nota_midi(self, nota):
        self.canvas_midi.delete("all")
        ancho = self.canvas_midi.winfo_width()
        alto = self.canvas_midi.winfo_height()
        
        # Dibujar barra proporcional a la nota
        x = nota / 127 * ancho
        self.canvas_midi.create_rectangle(0, 0, x, alto, fill="blue", outline="")
        self.canvas_midi.create_text(10, 10, anchor=tk.NW, text=f"Nota: {nota}")
    
    def mostrar_acerca(self):
        acerca = tk.Toplevel(self.root)
        acerca.title("Acerca de")
        acerca.geometry("400x300")
        acerca.resizable(False, False)
        
        ttk.Label(acerca, text="Sistema Distribuido de Análisis Auditivo", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(acerca, text="Proyecto SD 2526-2").pack()
        ttk.Label(acerca, text="Universidad Metropolitana de Caracas").pack()
        ttk.Label(acerca, text=" ").pack()
        ttk.Label(acerca, text="Este sistema permite procesar obras literarias").pack()
        ttk.Label(acerca, text="en nodos distribuidos y convertirlas en").pack()
        ttk.Label(acerca, text="eventos sonoros MIDI para su análisis auditivo.").pack()
        ttk.Label(acerca, text=" ").pack()
        ttk.Label(acerca, text="Tecnologías: Python, Sockets, Tkinter, MIDI").pack()
        ttk.Button(acerca, text="Cerrar", command=acerca.destroy).pack(pady=10)

# Punto de entrada principal
if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionMonitor(root)
    root.mainloop()