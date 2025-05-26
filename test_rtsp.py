import cv2
import os
from dotenv import load_dotenv

load_dotenv()

# URL del flujo RTSP (puede requerir usuario/contraseña)
rtsp_url = os.getenv('url_rstp')

# Conectar al flujo
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("Error: No se pudo conectar al flujo RTSP")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: No se pudo leer el frame")
        break

    # Mostrar el frame en una ventana
    cv2.imshow('RTSP Stream', frame)

    # Salir con la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
