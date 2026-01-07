import streamlit as st
import cv2
import numpy as np
import sqlite3
from PIL import Image

# Configuración de la página
st.set_page_config(page_title="Sistema Biométrico", layout="centered")

# Base de Datos
conn = sqlite3.connect("biometria.db", check_same_thread=False)
c = conn.cursor()
# Guardamos la foto completa en lugar de solo el código
c.execute('CREATE TABLE IF NOT EXISTS usuarios (nombre TEXT, foto BLOB)')
conn.commit()

# Función para comparar imágenes (Similitud matemática)
def comparar_rostros(img1, img2):
    # Convertir a escala de grises y al mismo tamaño
    gris1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gris2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
    
    # Reducimos tamaño para facilitar comparación
    gris1 = cv2.resize(gris1, (200, 200))
    gris2 = cv2.resize(gris2, (200, 200))

    # Calcular diferencia matemática (Error Cuadrático Medio)
    error = np.sum((gris1.astype("float") - gris2.astype("float")) ** 2)
    error /= float(gris1.shape[0] * gris1.shape[1])
    
    # Si el error es bajo, las caras se parecen
    return error < 3000  # Umbral de sensibilidad

st.title("👤 Sistema de Acceso Facial")
st.info("Modo: Python 3.13 Compatible (Sin librerías antiguas)")

menu = ["Registrar Nuevo Usuario", "Verificar Acceso"]
opcion = st.sidebar.selectbox("Seleccione una opción", menu)

if opcion == "Registrar Nuevo Usuario":
    st.header("📝 Registro")
    nombre = st.text_input("Ingrese su nombre completo:")
    foto = st.camera_input("Tome una foto clara de su rostro")
    
    if st.button("Guardar Registro") and foto and nombre:
        # Procesar imagen
        bytes_foto = foto.getvalue()
        c.execute("INSERT INTO usuarios (nombre, foto) VALUES (?, ?)", (nombre, bytes_foto))
        conn.commit()
        st.success(f"✅ ¡Usuario {nombre} registrado exitosamente!")
        st.balloons()

elif opcion == "Verificar Acceso":
    st.header("🔐 Verificación")
    foto_v = st.camera_input("Mire a la cámara para validar")
    
    if foto_v:
        # Convertir foto actual para comparar
        img_actual = np.array(Image.open(foto_v))
        
        # Buscar en base de datos
        c.execute("SELECT nombre, foto FROM usuarios")
        usuarios = c.fetchall()
        encontrado = False
        
        status = st.empty()
        status.info("🔍 Analizando rostro...")
        
        for nombre_db, foto_blob in usuarios:
            # Convertir foto guardada de bytes a imagen
            nparr = np.frombuffer(foto_blob, np.uint8)
            img_guardada = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img_guardada = cv2.cvtColor(img_guardada, cv2.COLOR_BGR2RGB)
            
            # Comparar
            if comparar_rostros(img_actual, img_guardada):
                status.success(f"🔓 ¡ACCESO CONCEDIDO! Bienvenido, {nombre_db}")
                st.balloons()
                encontrado = True
                break
        
        if not encontrado:
            status.error("🚫 ACCESO DENEGADO: Rostro no reconocido")