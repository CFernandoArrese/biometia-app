import streamlit as st
import cv2
import numpy as np
import requests
import base64
from PIL import Image

# URL de tu Google App Script (Pégala aquí entre las comillas)
URL_EXCEL = "https://script.google.com/macros/s/AKfycbzQ9VQSvari9Gue-fMTL34OK3mXlNY7pdeIFlZqLaoSVzXntxTvFSxs6-JUWVlty1Oa/exec"

st.set_page_config(page_title="Biometría Eterna", layout="centered")

# Función para convertir imagen a texto (para enviarla al Excel)
def img_to_base64(img_array):
    _, buffer = cv2.imencode('.jpg', img_array)
    return base64.b64encode(buffer).decode('utf-8')

st.title("👤 Sistema Biométrico (Nube)")

menu = ["Registrar en Google Sheets", "Verificar"]
opcion = st.sidebar.selectbox("Seleccione", menu)

if opcion == "Registrar en Google Sheets":
    nombre = st.text_input("Nombre:")
    foto = st.camera_input("Toma la foto de registro")
    
    if st.button("Guardar para siempre") and foto and nombre:
        img = np.array(Image.open(foto))
        foto_b64 = img_to_base64(img)
        
        # Enviamos los datos al Excel
        datos = {"nombre": nombre, "foto": foto_b64}
        respuesta = requests.post(URL_EXCEL, json=datos)
        
        if respuesta.status_code == 200:
            st.success(f"✅ {nombre} guardado en Google Sheets")
            st.balloons()

elif opcion == "Verificar":
    st.warning("Nota: Para verificar, el sistema leerá los datos desde tu Google Sheet.")
    # (Aquí iría el código para descargar los datos del Excel y comparar)
    # Por ahora, ¡asegúrate de que el registro funcione!

            status.error("🚫 ACCESO DENEGADO: Rostro no reconocido")
