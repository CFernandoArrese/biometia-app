import streamlit as st
import cv2
import numpy as np
import requests
import base64
from PIL import Image
import os

# --- CONFIGURACIÓN ---
# ¡IMPORTANTE! NO BORRES TU URL DE GOOGLE. Pégala aquí abajo si se borró.
URL_EXCEL = "https://script.google.com/macros/s/AKfycbzQ9VQSvari9Gue-fMTL34OK3mXlNY7pdeIFlZqLaoSVzXntxTvFSxs6-JUWVlty1Oa/exec" # <--- REVISA ESTA LÍNEA

st.set_page_config(page_title="Biometría Pro", layout="centered")

# --- FUNCIONES DE UTILIDAD ---

# Función para obtener el detector de rostros (lo descarga si no existe)
@st.cache_resource
def obtener_detector():
    nombre_archivo = 'haarcascade_frontalface_default.xml'
    # Si no tenemos el archivo en la nube, lo descargamos de OpenCV
    if not os.path.exists(nombre_archivo):
        url_xml = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        response = requests.get(url_xml)
        with open(nombre_archivo, 'wb') as f:
            f.write(response.content)
    detector = cv2.CascadeClassifier(nombre_archivo)
    return detector

# Función NUEVA: Recorta solo la cara de la imagen completa
def recortar_rostro(img_array):
    detector = obtener_detector()
    # Convertimos a escala de grises para la detección
    gris = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    # Detectamos rostros (pueden ser varios)
    rostros = detector.detectMultiScale(gris, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    if len(rostros) == 0:
        return None # No se encontró ninguna cara
    
    # Si hay varios, tomamos el más grande (el principal)
    (x, y, w, h) = max(rostros, key=lambda r: r[2] * r[3])
    
    # Recortamos el cuadrado de la cara (añadimos un pequeño margen)
    margen = int(h * 0.1) # 10% de margen
    y1 = max(0, y - margen)
    x1 = max(0, x - margen)
    y2 = min(img_array.shape[0], y + h + margen)
    x2 = min(img_array.shape[1], x + w + margen)
    
    rostro_recortado = img_array[y1:y2, x1:x2]
    return rostro_recortado

def img_to_base64(img_array):
    # Convertimos a RGB antes de guardar para asegurar colores correctos
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    _, buffer = cv2.imencode('.jpg', img_rgb)
    return base64.b64encode(buffer).decode('utf-8')

def base64_to_img(base64_string):
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

# Función de comparación (ahora funciona mejor porque compara caras recortadas)
def comparar_rostros(img1, img2):
    # Convertimos a grises
    gris1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gris2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
    
    # Redimensionamos ambas al mismo tamaño exacto (ej. 100x100 píxeles)
    tamano = (100, 100)
    gris1 = cv2.resize(gris1, tamano)
    gris2 = cv2.resize(gris2, tamano)

    # Calculamos la diferencia matemática (MSE)
    error = np.sum((gris1.astype("float") - gris2.astype("float")) ** 2)
    error /= float(gris1.shape[0] * gris1.shape[1])
    
    # Umbral: cuanto más bajo, más estricto.
    # Con caras recortadas, podemos ser más estrictos.
    return error < 1500 

# --- INTERFAZ PRINCIPAL ---

st.title("👤 Sistema Biométrico Inteligente")

menu = ["Registrar", "Verificar Acceso"]
opcion = st.sidebar.selectbox("Seleccione", menu)

if opcion == "Registrar":
    st.header("Nuevo Registro")
    nombre = st.text_input("Nombre:")
    foto = st.camera_input("Foto de Registro (Intenta que tu cara esté centrada)")
    
    if st.button("Guardar en la Nube") and foto and nombre:
        with st.spinner("Procesando imagen..."):
            img_completa = np.array(Image.open(foto))
            # PASO CLAVE: Recortamos la cara antes de guardar
            rostro_crop = recortar_rostro(img_completa)
            
            if rostro_crop is not None:
                # Guardamos solo el recorte
                datos = {"nombre": nombre, "foto": img_to_base64(rostro_crop)}
                try:
                    r = requests.post(URL_EXCEL, json=datos)
                    if r.status_code == 200:
                        st.success(f"✅ {nombre} registrado con éxito. (Se guardó solo el rostro recortado)")
                        # Mostramos qué fue lo que se guardó
                        st.image(rostro_crop, caption="Rostro guardado", width=150)
                    else:
                        st.error("Error al conectar con Google Sheets")
                except:
                    st.error("Error de conexión. Revisa tu URL.")
            else:
                st.warning("⚠️ No se detectó un rostro claro. Asegúrate de tener buena luz y mirar de frente.")

elif opcion == "Verificar Acceso":
    st.header("Verificación")
    foto_v = st.camera_input("Mire a la cámara")
    
    if foto_v:
        with st.spinner("Analizando rostro y buscando en la nube..."):
            img_actual_completa = np.array(Image.open(foto_v))
            # PASO CLAVE: Recortamos la cara actual
            rostro_actual_crop = recortar_rostro(img_actual_completa)
            
            if rostro_actual_crop is not None:
                # Mostramos el recorte que estamos usando para comparar
                st.image(rostro_actual_crop, caption="Tu rostro detectado", width=150)
                
                # Pedimos los datos al Excel
                try:
                    r = requests.get(URL_EXCEL)
                    usuarios = r.json()
                    
                    encontrado = False
                    coincidencia_nombre = ""
                    
                    # Comparamos tu cara recortada con las caras recortadas guardadas
                    for u in usuarios:
                        img_db_crop = base64_to_img(u['foto'])
                        if comparar_rostros(rostro_actual_crop, img_db_crop):
                            encontrado = True
                            coincidencia_nombre = u['nombre']
                            break
                            
                    if encontrado:
                        st.success(f"🔓 ¡ACCESO CONCEDIDO! Bienvenido, {coincidencia_nombre}")
                        st.balloons()
                    else:
                        st.error("🚫 Acceso Denegado: Rostro no reconocido en la base de datos.")
                except:
                     st.error("Error al leer Google Sheets. Revisa tu URL o la conexión.")
            else:
                st.warning("⚠️ No se detectó un rostro claro en la cámara.")
