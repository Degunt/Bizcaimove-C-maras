import os
import shutil
import pandas as pd

# ==========================
# CONFIGURACIÓN: Previo al uso de este código es necesario haber anotado en un Excel los nombres de todas las imágenes que desees eliminar. La carpeta 2. Selected es realmente un copia y pega de la carpera 1. ImágenesOriginal,
solo que cuando usemos este código, las imágenes se repartirán entre las carpetas 2. Selected y 2. Deleted
# ==========================

# Ruta del archivo Excel
ruta_excel = r"ruta de tu excel con las imágenes a eliminar"

# Nombre de la columna donde están los nombres de las imágenes
columna_imagenes = "DeletedImage"   # <-- Cambia esto si tu columna se llama diferente

# Carpeta origen (donde están actualmente)
carpeta_origen = r"D:\2. Imágenes\2. Selected\2.Selected_imagenes\2.Selected_Salida Gernika_fin_muestreo"

# Carpeta destino (a donde se moverán)
carpeta_destino = r"D:\2. Imágenes\2. Deleted\2.Deleted_imagenes\2.Deleted_Salida_Gernika"

# ==========================
# LEER EXCEL
# ==========================

df = pd.read_excel(ruta_excel)
nombres_excel = df[columna_imagenes].astype(str).str.strip().tolist()

# ==========================
# INDEXAR ARCHIVOS REALES
# ==========================

archivos_reales = os.listdir(carpeta_origen)

# Crear diccionario: nombre_sin_extension -> nombre_real_con_extension
mapa_archivos = {}

for archivo in archivos_reales:
    nombre_base, extension = os.path.splitext(archivo)
    mapa_archivos[nombre_base.lower()] = archivo


# ==========================
# MOVER ARCHIVOS
# ==========================

movidas = 0
no_encontradas = []

for nombre in nombres_excel:

    nombre_normalizado = nombre.strip().lower()

    if nombre_normalizado in mapa_archivos:
        archivo_real = mapa_archivos[nombre_normalizado]

        ruta_origen = os.path.join(carpeta_origen, archivo_real)
        ruta_destino = os.path.join(carpeta_destino, archivo_real)

        if os.path.exists(ruta_origen):
            shutil.move(ruta_origen, ruta_destino)
            movidas += 1
        else:
            print(f"No existe: {ruta_origen}")
            no_encontradas.append(nombre)

# ==========================
# RESULTADO
# ==========================

print(f"\nImágenes movidas correctamente: {movidas}")

if no_encontradas:
    print("\nNo encontradas:")
    for img in no_encontradas:
        print(img)
        
print("\nResumen")
print("Imágenes movidas:", movidas)
print("Imágenes no encontradas:", len(no_encontradas))
