import cv2

# Reemplaza con tu URL RTSP
rtsp_url = 'udp://127.0.0.1:8554'

# Abrir el stream
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("❌ No se pudo abrir el stream RTSP.")
    exit(1)

print("✅ Stream abierto correctamente. Presiona ESC para salir.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Error al leer el frame.")
        continue

    cv2.imshow("Stream de la cámara", frame)

    if cv2.waitKey(1) == 27:  # Tecla ESC para salir
        break

cap.release()
cv2.destroyAllWindows()
