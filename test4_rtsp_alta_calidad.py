from multiprocessing import Process, Queue
import cv2
import imutils
import argparse
import os
from anprclass import CannyANPR, EdgelessANPR, SobelANPR
import logging
from datetime import datetime
#import keyboard
import sys
import time
import re
from dotenv import load_dotenv
from skimage.metrics import structural_similarity as ssim




load_dotenv()


rtsp_url = os.getenv('url_rstp')

from multiprocessing import set_start_method
set_start_method("spawn", force=True)  

inicio = datetime.now()


ultima_patente = None

def patente_valida(texto):
    """
    Verifica si el texto cumple con el formato @@@@## o @@####
    """
    texto = texto.upper()  # Asegura que esté en mayúsculas
    patron1 = r'^[A-Z]{4}[0-9]{2}$'  # 4 letras y 2 números
    patron2 = r'^[A-Z]{2}[0-9]{4}$'  # 2 letras y 4 números
    return re.match(patron1, texto) or re.match(patron2, texto)


def matar_proceso():
    pid = os.getpid()
    print(f"Matando proceso {pid}...")
    os.kill(pid, 9)  # Señal 9 = SIGKILL (termina inmediatamente)


# Configuramos el logger
logging.basicConfig(
    filename='detector_patentes.log',  # nombre del archivo de log
    level=logging.INFO,
    format='[%(asctime)s] [UPTIME: %(uptime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Creamos un logger personalizado para insertar el uptime
class UptimeLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        now = datetime.now()
        uptime = now - inicio
        uptime_str = str(uptime).split('.')[0]  # quitamos microsegundos
        kwargs['extra'] = {'uptime': uptime_str}
        return msg, kwargs



def frame_worker(queue, anpr, psm, clear_border, debug, save, estado_patente):
    while True:
        item = queue.get()
        if item is None:
            break  # señal para terminar el proceso
        frame, iteration = item
        try:
            process_frame(frame, iteration, anpr, psm, clear_border, debug, save, estado_patente)
            '''except:
            #linea en donde fallo

            print("Fallo en procesar el frame:", sys.exc_info()[0]) # Imprimir el error 
            #imprimir toda las data
            print("Error:", sys.exc_info()[1])
            print("Traceback:", sys.exc_info()[2])
            # Imprimir el estado actual del proceso
            print("Estado actual del proceso:", estado_patente)
            # Imprimir el frame que falló
            print("Frame que fallo:", frame)'''
        except Exception as e:
            print(f"Error en procesar el frame {iteration}: {e}")
            # Imprimir toda las data
            # Imprimir el estado actual del proceso
            print("Estado actual del proceso:", estado_patente)
            # Imprimir el frame que falló
            print("Frame que fallo:", frame)
            # Detener el proceso si hay un error
            raise
            



def cleanup_text(text):
    """Limpia el texto OCR de caracteres no ASCII."""
    return "".join([c if ord(c) < 128 else "" for c in text]).strip()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Detección de placas desde RTSP con OCR.")
    parser.add_argument("-r", "--rtsp", type=str, required=False,
                        default=rtsp_url,
                        help="URL del stream RTSP de la cámara") # udp://192.168.100.231
    parser.add_argument("-c", "--clear-border", type=int, default=1,
                        help="Limpiar bordes antes del OCR")
    parser.add_argument("-C", "--CalidadProces", type=int, default=0,
                        help="procesa el flujo como venga y no limita a 400px cambia a 1 para no redimencionar")
    parser.add_argument("-p", "--psm", type=int, default=7,
                        help="Modo PSM de Tesseract OCR")
    parser.add_argument("-d", "--debug", type=int, default=0,
                        help="Mostrar visualizaciones intermedias")
    parser.add_argument("-a", "--algorithm", type=int, default=1,
                        help="Algoritmo de detección de bordes: 1-Sobel, 2-Canny, 3-Sin bordes")
    parser.add_argument("-s", "--save", type=int, default=1,
                        help="Guardar imágenes con resultado")
    parser.add_argument("-m", "--morphology", type=str, default='bh',
                        choices=['bh', 'th'],
                        help="Transformación morfológica: black hat (bh) o top hat (th)")
    parser.add_argument("-D", "--display", type=int, default=1,
                    help="Mostrar la ventana del stream (1 = sí, 0 = no)")
    return parser.parse_args()

def process_frame(frame, iteration, anpr, psm, clear_border, debug, save, estado_patente):

    # Chequeamos si se presionó ESC
    #if keyboard.is_pressed('esc'):
    #    print("ESC presionado. Saliendo del programa.")
    #    matar_proceso()
    if args.CalidadProces == False:
        image = imutils.resize(frame, width=400)
    else:
        image=frame    

    image = cv2.bilateralFilter(image, 3, 105, 105)

    #if debug:
        #anpr.debug_imshow("Filtro Bilateral", image,waitKey=False )

    lp_text, lp_cnt = anpr.find_and_ocr(iteration, image, psm=psm, clearBorder=clear_border)

    if lp_text and len(lp_text) > 5 and  lp_cnt is not None:
        box = cv2.boxPoints(cv2.minAreaRect(lp_cnt)).astype("int")
        cv2.drawContours(image, [box], -1, (0, 255, 0), 2)
        x, y, w, h = cv2.boundingRect(lp_cnt)
        cv2.putText(image, cleanup_text(lp_text), (x, y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        
        lp_text = cleanup_text(lp_text).upper()

        if not patente_valida(lp_text):
            return image


        if lp_text != estado_patente['ultima']:
            print(f"[INFO] Patente detectada: {lp_text}")
            logger.info(f"Patente detectada: {lp_text}")
            estado_patente['ultima'] = lp_text

            if debug:
                anpr.debug_imshow("Patente prev", anpr.LP_cap)
                print(anpr.LP_cap_balance)
                anpr.debug_imshow("Resultado ANPR", anpr.LP)

        if save:
            anpr.save_result(f"FrameDetectado_LP-{lp_text}_{iteration}.jpg", image)

    return image





args = parse_arguments()

def main():
    
    estado_patente = {'ultima': None}
    rtsp_url = args.rtsp
    input_dir = "rtsp_live/"
    iteration = 0
    minAR_=2.5
    maxAR_=minAR_*2
    last_frame = None


    algo = args.algorithm
    if algo == 1:
        anpr = SobelANPR(algo, input_dir, args.morphology, minAR=minAR_, maxAR=maxAR_, debug=bool(args.debug), save=bool(args.save))
    elif algo == 2:
        anpr = CannyANPR(algo, input_dir, args.morphology, minAR=minAR_, maxAR=maxAR_, debug=bool(args.debug), save=bool(args.save))
    elif algo == 3:
        anpr = EdgelessANPR(algo, input_dir, args.morphology, minAR=minAR_, maxAR=maxAR_, debug=bool(args.debug), save=bool(args.save))
    else:
        print('Invalid algorithm choice')
        sys.exit()

    cap = cv2.VideoCapture(rtsp_url,cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("Error: No se pudo abrir el stream RTSP.")
        return

    print("[INFO] Iniciando procesamiento del stream...")
    if args.display:
        cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)
        #cv2.resizeWindow("Stream", 800, 600)

    frame_queue = Queue(maxsize=3)  # No saturar la memoria si se atrasa el worker

    # Lanza el proceso para procesar frames
    worker = Process(target=frame_worker, args=(
        frame_queue, anpr, args.psm, bool(args.clear_border),
        bool(args.debug), bool(args.save), estado_patente
    ))
    worker.start()


    while True:

        # Chequeamos si se presionó ESC
        #if keyboard.is_pressed('esc'):
        #    print("ESC presionado. Saliendo del programa.")
        #    matar_proceso()

        if cap is None or not cap.isOpened():
            print("[WARN] Stream no disponible. Reintentando en 2 segundos...")
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url)  # cv2.CAP_FFMPEG
            continue


        ret, frame = cap.read()

        
        if not ret:
            print("[WARN] Fallo al leer frame. Cerrando y reintentando...")
            cap.release()
            cap = None
            continue

        #Colocamos un fultro para evitar falsos positivos con la hora del reloj
        
        if args.CalidadProces == False:
            frame = imutils.resize(frame, width=400)

            # Recuadro negro relleno  16:9
            frame[13:18, 7:103] = (255, 255, 255)
            frame[201:206, 298:335] = (255, 255, 255)


            # Recuadro negro relleno  4:6   
        #_    frame[19:25, 7:103] = (255, 255, 255)
        #_    frame[292:298, 298:335] = (255, 255, 255)    
        
        if args.display:
            
            cv2.imshow("Stream", frame)
            if cv2.waitKey(1) == 27:  # ESC para salir
                break

        
        # Redimensionar para acelerar el cálculo y estandarizar
        resized = cv2.resize(frame, (320, 240))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        

        
        if args.CalidadProces == False:
            #rango de 80% para cambios en frames de baja calidad
            Rango = 0.8 
        else:
            #bajar el rango si se esta probando alta calidad
            Rango = 0.68 

        if last_frame is not None:
            score, _ = ssim(last_frame, gray, full=True)
            print(f"Frame  ({score:.2f}). ")
            if score > 0.8:
                #print(f"[WARN] Frame similar al anterior ({score:.2f}). ")
#                time.sleep(2)
                continue
        # Guardar para la siguiente comparación
        last_frame = gray



        iteration += 1
        #result_img = 
    #_    process_frame(frame, iteration, anpr,
    #_                               psm=args.psm,
    #_                               clear_border=bool(args.clear_border),
    #_                               debug=bool(args.debug),
    #_                               save=bool(args.save), estado_patente=estado_patente)
        
        if not frame_queue.full():
            frame_queue.put((frame.copy(), iteration))

        
        
    cap.release()

    if args.display:
        cv2.destroyAllWindows()
    print("[INFO] Stream finalizado.")


logger = UptimeLoggerAdapter(logging.getLogger(__name__), {})

if __name__ == "__main__":
    
    main()


