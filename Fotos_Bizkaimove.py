"""
Created on Fri Oct 24 16:15:58 2025

@author: deben
"""

import os
import requests
from datetime import datetime

# ==============================
# CONFIGURACIÓN
# ==============================

# Carpeta principal donde se guardarán todas las imágenes
# 💡 Puedes cambiar esta ruta si lo prefieres (por ejemplo, a Documents o Desktop)
carpeta_base = os.path.join(os.getcwd(), "imagenes")

# Diccionario con las cámaras y sus identificadores (IDs de Bizkaimove)
camaras = {
    "Zaramillo": 80,
    "LaArena": 85,
    "Erletxe": 87,
    "Larrabetxu": 75,
    "Asua": 52,
    "Cadagua": 232,
    "Abadino": 403,
    "Artea": 41
}

# ==============================
# DESCARGA DE IMÁGENES
# ==============================

# Crea la carpeta principal si no existe
os.makedirs(carpeta_base, exist_ok=True)

# Marca de tiempo actual (para nombres únicos)
timestamp = datetime.now().strftime("%Y%m%d_%H%M")

# Recorre todas las cámaras
for nombre, cam_id in camaras.items():
    # Crea la subcarpeta de cada cámara dentro de la carpeta principal
    carpeta_camara = os.path.join(carpeta_base, nombre)
    os.makedirs(carpeta_camara, exist_ok=True)

    # URL directa de la imagen de la cámara
    url = f"https://www.bizkaimove.com/camaras/cam{cam_id}.jpg"

    # Nombre del archivo de salida (ejemplo: Zaramillo_20251024_0800.jpg)
    nombre_archivo = f"{nombre}_{timestamp}.jpg"
    ruta_archivo = os.path.join(carpeta_camara, nombre_archivo)

    # Descarga la imagen
    try:
        respuesta = requests.get(url, timeout=10)
        respuesta.raise_for_status()  # lanza error si no es código 200
        with open(ruta_archivo, "wb") as f:
            f.write(respuesta.content)
        print(f"✅ Guardada: {ruta_archivo}")
    except Exception as e:
        print(f"❌ Error al descargar {nombre}: {e}")


print("\nDescarga completada con éxito ✅")

