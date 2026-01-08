import streamlit as st
import cv2
import numpy as np
import requests
import base64
from PIL import Image
import mediapipe as mp

# --- CONFIGURACIÓN ---
# ¡IMPORTANTE! PEGA AQUÍ TU URL DE GOOGLE APPS SCRIPT
URL_EXCEL = "https://script.google.com/macros/s/AKfycbzQ9VQSvari9Gue-fMTL34OK3mXlNY7pdeIFlZqLaoSVzXntxTvFSxs6-JUWVlty1Oa/exec"

st.set_page_config(page_title="Biometría Google MediaPipe", layout="centered")

# --- INICIALIZAR MEDIAPIPE (La magia de Google) ---
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- FUNCIONES ---

def procesar_rostro(img_array):
    """
    Detecta el rostro usando malla 3D, dibuja la malla y recorta la cara.
    """
    # MediaPipe necesita imágenes en RGB
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    
    # Iniciamos el detector de malla
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5) as face_mesh:
        
        results = face_mesh.process(img_rgb)
        
        if not results.multi_face_landmarks:
            return None, None # No se encontró cara
            
        # Tomamos la primera cara detectada
        face_landmarks = results.multi_face_landmarks[0]
        
        # 1. Dibujamos la malla sobre la imagen original (Efecto visual)
        img_con_malla = img_array.copy()
        mp_drawing.draw_landmarks(
            image=img_con_malla,
            landmark_list=face_landmarks,
            connections=mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())
            
        # 2. Calculamos el rectángulo para recortar la cara
        h, w, _ = img_array.shape
        x_min, x_max = w, 0
        y_min, y_max = h, 0
        
        for lm in face_landmarks.landmark:
            x, y = int(lm.x * w), int(lm.y * h)
            if x < x_min: x_min = x
            if x > x_max: x_max = x
            if y < y_min: y_min = y
            if y > y_max: y_max = y
            
        # Damos un margen del 10%
        margen_x = int((x_max - x_min) * 0.1)
        margen_y = int((y_max - y_min) * 0.1)
        
        x_min = max(0, x_min - margen_x)
        x_max = min(w, x_max + margen_x)
        y_min = max(0, y_min - margen_y)
        y_max = min(h, y_max + margen_y)
        
        # Recortamos
        rostro_recortado = img_array[y_min:y_max, x_min:x_max]
        
        return rostro_recortado, img_con_malla

def comparar_histogramas(img1, img2):
    # Convertimos a HSV (Mejor manejo de luz)
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_RGB2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_RGB2HSV)
    
    # Calculamos histograma
    hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])
    
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
    
    similitud = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return similitud

def img_to_base64(img_array):
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    _, buffer = cv2.imencode('.jpg', img_rgb)
    return base64.b64encode(buffer).decode('utf-8')

def base64_to_img(base64_string):
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

# --- INTERFAZ ---
st.title("🤖 Biometría con IA Google")
st.caption("Usando MediaPipe Face Mesh para precisión geométrica")

menu = ["Registrar", "Acceder"]
opcion = st.sidebar.selectbox("Opciones", menu)

if opcion == "Registrar":
    st.write("Mira a la cámara. El sistema creará una malla 3D de tu rostro.")
    nombre = st.text_input("Nombre de usuario:")
    foto = st.camera_input("Registro")
    
    if st.button("Guardar en Nube") and foto and nombre:
        img = np.array(Image.open(foto))
        
        # Procesamos con MediaPipe
        rostro_crop, img_malla = procesar_rostro(img)
        
        if rostro_crop is not None:
            # Mostramos la malla para que el usuario vea la tecnología
            st.image(img_malla, caption="Malla Facial Detectada", width=200)
            
            datos = {"nombre": nombre, "foto": img_to_base64(rostro_crop)}
            try:
                requests.post(URL_EXCEL, json=datos)
                st.success(f"✅ {nombre} registrado exitosamente.")
            except:
                st.error("Error de conexión.")
        else:
            st.error("❌ No se detectó rostro. Intenta quitarte el pelo de la cara.")

elif opcion == "Acceder":
    foto_v = st.camera_input("Verificación")
    
    if foto_v:
        img_actual = np.array(Image.open(foto_v))
        rostro_actual, img_malla = procesar_rostro(img_actual)
        
        if rostro_actual is not None:
            st.image(img_malla, caption="Escaneando puntos faciales...", width=200)
            
            with st.spinner("Consultando base de datos mundial..."):
                try:
                    r = requests.get(URL_EXCEL)
                    usuarios = r.json()
                    
                    mejor_score = 0
                    usuario_final = None
                    
                    for u in usuarios:
                        rostro_db = base64_to_img(u['foto'])
                        
                        # Comparamos el recorte perfecto de MediaPipe
                        score = comparar_histogramas(rostro_actual, rostro_db)
                        if score > mejor_score:
                            mejor_score = score
                            usuario_final = u['nombre']
                    
                    # Umbral de decisión
                    if mejor_score > 0.60:
                        st.balloons()
                        st.success(f"🔓 ACCESO PERMITIDO: {usuario_final}")
                        st.info(f"Confianza del sistema: {int(mejor_score*100)}%")
                    else:
                        st.error("🚫 ACCESO DENEGADO")
                        st.warning(f"Similitud encontrada: {int(mejor_score*100)}% (Muy baja)")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("⚠️ El sistema no detecta una cara humana válida.")

