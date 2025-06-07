# progrma auxiliar para mostrar as imagens capturadas en una ventana, solo sirve para debug#
import os
import sys
import datetime
from PIL import Image, ImageTk
import tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time # Importar time para usar time.sleep si es necesario

# --- Clase para la aplicación de visualización de imágenes ---
class ImageViewerApp:
    def __init__(self, master, folder_path):
        self.master = master
        self.master.title("Última Imagen Creada")
        self.folder_path = folder_path
        self.current_image_path = None
        self.original_image = None
        self.photo_image = None

        # Configurar el tamaño inicial de la ventana
        self.initial_width = 600
        self.initial_height = 600
        self.master.geometry(f"{self.initial_width}x{self.initial_height}")
        self.center_window()

        self.image_label = tk.Label(master)
        self.image_label.pack(expand=True, fill=tk.BOTH)

        self.last_update_time = tk.StringVar()
        self.time_label = tk.Label(master, textvariable=self.last_update_time, font=("Helvetica", 10))
        self.time_label.pack(pady=5)

        self.status_label = tk.Label(master, text="Monitoreando carpeta...", fg="blue")
        self.status_label.pack(pady=5)

        # Vincular el evento de configuración (redimensionamiento) de la ventana
        self.master.bind("<Configure>", self.on_window_resize)

        # Inicializar el tamaño de la ventana para el evento de redimensionamiento
        self.master.update_idletasks() # Asegura que los widgets tengan un tamaño antes de la primera carga
        self._last_width = self.master.winfo_width()
        self._last_height = self.master.winfo_height()

        self.update_image() # Carga la primera imagen al iniciar
        print(f"Aplicación iniciada. Monitoreando: {self.folder_path}")

    def center_window(self):
        """Centra la ventana en la pantalla."""
        self.master.update_idletasks() # Actualiza los "idletasks" para obtener el tamaño real de la ventana

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        x = (screen_width // 2) - (self.initial_width // 2)
        y = (screen_height // 2) - (self.initial_height // 2)

        self.master.geometry(f"{self.initial_width}x{self.initial_height}+{x}+{y}")

    def find_latest_image(self):
        """Busca la última imagen creada en la carpeta."""
        imagenes = []
        if not os.path.isdir(self.folder_path):
            self.status_label.config(text=f"Error: La ruta '{self.folder_path}' no es una carpeta válida.", fg="red")
            return None

        for archivo in os.listdir(self.folder_path):
            ruta_completa_archivo = os.path.join(self.folder_path, archivo)
            # Depuración: Imprimir archivos encontrados
            # print(f"Analizando archivo: {ruta_completa_archivo}")
            if os.path.isfile(ruta_completa_archivo) and archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                tiempo_creacion = os.path.getctime(ruta_completa_archivo)
                imagenes.append((tiempo_creacion, ruta_completa_archivo))

        if not imagenes:
            print(f"No se encontraron imágenes en la carpeta '{self.folder_path}'.")
            return None

        imagenes.sort(key=lambda x: x[0], reverse=True)
        return imagenes[0][1]

    def update_image(self):
        """Carga la última imagen, la guarda y dispara su redimensionamiento."""
        latest_image_path = self.find_latest_image()

        if latest_image_path and latest_image_path != self.current_image_path:
            try:
                print(f"Intentando cargar nueva imagen: {latest_image_path}")
                self.original_image = Image.open(latest_image_path)
                self.current_image_path = latest_image_path
                self.resize_and_display_image()
                time_creacion_dt = datetime.datetime.fromtimestamp(os.path.getctime(latest_image_path))
                #self.last_update_time.set(f"Última imagen: {os.path.basename(latest_image_path)}\nCreada: {time_creacion_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                #self.status_label.config(text="Imagen actualizada.", fg="green")
                print(f"Imagen actualizada a: {latest_image_path}")

            except Exception as e:
                self.status_label.config(text=f"Error al cargar imagen: {e}", fg="red")
                print(f"Error al cargar imagen '{latest_image_path}': {e}")
        elif not latest_image_path:
            self.status_label.config(text="No se encontraron imágenes en la carpeta.", fg="orange")
            self.image_label.config(image='')
            self.image_label.image = None
            self.original_image = None
            self.photo_image = None
            self.last_update_time.set("")
            print("No se encontraron imágenes, limpiando pantalla.")
        elif self.original_image:
             # Si ya es la misma imagen, la redimensionamos por si acaso el tamaño de la ventana cambió
             # print("Imagen actual es la más reciente, verificando redimensionamiento.")
             self.resize_and_display_image()

    def resize_and_display_image(self):
        """Redimensiona la imagen actual para ajustarse a la ventana y la muestra."""
        if self.original_image is None:
            return

        # Obtener el tamaño actual del Label, o si aún no está mapeado, el tamaño de la ventana
        widget_width = self.image_label.winfo_width()
        widget_height = self.image_label.winfo_height()

        # Si el label aún no tiene tamaño (p. ej., al inicio o si es 1x1 por defecto)
        if widget_width <= 1 and widget_height <= 1:
             # Usar el tamaño de la ventana para el cálculo inicial
             widget_width = self.master.winfo_width()
             widget_height = self.master.winfo_height()

        # Restar un margen para el texto de abajo
        margin_height = self.time_label.winfo_height() + self.status_label.winfo_height() + 20

        # Asegurar que el tamaño sea positivo
        if widget_width <= 0 or (widget_height - margin_height) <= 0:
            # print("Tamaño de widget no válido para redimensionar la imagen.")
            return

        img_width, img_height = self.original_image.size
        ratio = min(widget_width / img_width, (widget_height - margin_height) / img_height)

        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        if new_width <= 0 or new_height <= 0:
            # print("Tamaño de imagen redimensionado sería 0 o negativo.")
            return

        try:
            resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)
            self.image_label.config(image=self.photo_image)
            self.image_label.image = self.photo_image
            # print(f"Imagen redimensionada a {new_width}x{new_height}")
        except Exception as e:
            print(f"Error al redimensionar/mostrar imagen: {e}")

    def on_window_resize(self, event):
        """Manejador de evento cuando la ventana es redimensionada."""
        # Se verifica si la geometría ha cambiado para evitar eventos superfluos
        current_width = self.master.winfo_width()
        current_height = self.master.winfo_height()

        if (current_width != self._last_width or current_height != self._last_height):
            if hasattr(self, '_resize_job'):
                self.master.after_cancel(self._resize_job)
            self._resize_job = self.master.after(50, self.resize_and_display_image)

            self._last_width = current_width
            self._last_height = current_height

# --- Clase para manejar eventos del sistema de archivos ---
class FolderEventHandler(FileSystemEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.last_detected_file = None # Para evitar procesar el mismo archivo múltiples veces

    def is_image_file(self, path):
        """Verifica si la ruta es un archivo de imagen."""
        return os.path.isfile(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))

    def process_event(self, event):
        """Lógica común para procesar eventos de archivo."""
        if not event.is_directory and self.is_image_file(event.src_path):
            # Condición para evitar procesar el mismo archivo si es modificado rápidamente
            if event.src_path != self.last_detected_file or \
               (time.time() - os.path.getmtime(event.src_path) < 2): # Última modificación hace menos de 2 segs

                print(f"Evento detectado para imagen: {event.src_path}")
                self.last_detected_file = event.src_path
                # Retraso para dar tiempo al sistema para escribir el archivo
                self.app.master.after(750, self.app.update_image) # Aumentado a 750ms

    def on_created(self, event):
        self.process_event(event)

    def on_modified(self, event):
        self.process_event(event) # Ambos eventos llaman a la misma lógica

# --- Punto de entrada principal ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tu_script.py <ruta_de_la_carpeta>")
        sys.exit(1)

    folder_to_monitor = sys.argv[1]

    root = tk.Tk()
    app = ImageViewerApp(root, folder_to_monitor)

    event_handler = FolderEventHandler(app)
    observer = Observer()
    # Considera cambiar recursive=False a True si tus imágenes pueden estar en subcarpetas
    observer.schedule(event_handler, folder_to_monitor, recursive=False)
    observer.start()
    print(f"Monitoreo de Watchdog iniciado para: {folder_to_monitor}")

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Programa terminado por el usuario (Ctrl+C).")
    finally:
        observer.stop()
        observer.join()
        print("Monitoreo de carpeta detenido limpiamente.")