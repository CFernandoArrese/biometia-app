import streamlit as st
import cv2
import numpy as np
import requests
import base64
from PIL import Image

# 1. PEGA TU URL AQUÍ
URL_EXCEL = "https://script.google.com/macros/s/AKfycbzQ9VQSvari9Gue-fMTL34OK3mXlNY7pdeIFlZqLaoSVzXntxTvFSxs6-JUWVlty1Oa/exec"

st.set_page_config(page_title="Biometría Eterna", layout="centered")

def img_to_base64(img_array):
    _, buffer = cv2.imencode('.jpg', img_array)
    return base64.b64encode(buffer).decode('utf-8')

def base64_to_img(base64_string):
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def comparar_rostros(img1, img2):
    gris1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gris2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    gris1 = cv2.resize(gris1, (200, 200))
    gris2 = cv2.resize(gris2, (200, 200))
    error = np.sum((gris1.astype("float") - gris2.astype("float")) ** 2)
    error /= float(gris1.shape[0] * gris1.shape[1])
    return error < 3500 

st.title("👤 Sistema Biométrico (Nube)")

menu = ["Registrar", "Verificar Acceso"]
opcion = st.sidebar.selectbox("Seleccione", menu)

if opcion == "Registrar":
    nombre = st.text_input("Nombre:")
    foto = st.camera_input("Foto de Registro")
    if st.button("Guardar en la Nube") and foto and nombre:
        img = np.array(Image.open(foto))
        datos = {"nombre": nombre, "foto": img_to_base64(img)}
        requests.post(URL_EXCEL, json=datos)
        st.success(f"✅ {nombre} registrado para siempre")

elif opcion == "Verificar Acceso":
    foto_v = st.camera_input("Mire a la cámara")
    if foto_v:
        img_actual = np.array(Image.open(foto_v))
        with st.spinner("Buscando en Google Sheets..."):
            # Pedimos los datos al Excel
            r = requests.get(URL_EXCEL)
            usuarios = r.json()
            
            encontrado = False
            for u in usuarios:
                img_db = base64_to_img(u['foto'])
                if comparar_rostros(img_actual, img_db):
                    st.success(f"🔓 Acceso Concedido: Bienvenido {u['nombre']}")
                    st.balloons()
                    encontrado = True
                    break
            if not encontrado:
                st.error("🚫 Usuario no reconocido")
