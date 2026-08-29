import os
import re
import cv2
import shutil
import pytesseract
import pandas as pd

from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Carpeta raíz de entrada
INPUT_ROOT = Path(r"D:\3. Imágenes_reescaladas")

# Carpeta raíz de salida
OUTPUT_ROOT = Path(r"D:\4. Imágenes_renombradas")

# Ruta a Tesseract OCR en Windows
# CAMBIA ESTA RUTA SI EN TU ORDENADOR ESTÁ EN OTRA UBICACIÓN
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Extensiones válidas
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Si quieres probar primero con pocas imágenes por carpeta, cambia a un número como 10
MAX_IMAGES_PER_FOLDER = None  # None = todas

# Si quieres solo simular sin copiar archivos, cambia a True
DRY_RUN = False

# Crear también carpeta de fallos OCR
SAVE_FAIL_IMAGES = True

# CSV final
CSV_PATH = OUTPUT_ROOT / "registro_renombrado.csv"

# Carpeta para fallos
FAIL_ROOT = OUTPUT_ROOT / "_fallos_ocr"

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_dirs():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if SAVE_FAIL_IMAGES:
        FAIL_ROOT.mkdir(parents=True, exist_ok=True)


def get_candidate_regions(width, height):
    """
    Devuelve regiones candidatas cercanas a esquinas y bandas,
    usando coordenadas relativas para adaptarse a distintos tamaños.
    Cada región se define como (nombre, x1, y1, x2, y2)
    """
    regions = []

    # Franja superior completa
    regions.append(("top_band", 0, 0, width, int(height * 0.18)))

    # Franja inferior completa
    regions.append(("bottom_band", 0, int(height * 0.82), width, height))

    # Esquinas superiores
    regions.append(("top_left", 0, 0, int(width * 0.42), int(height * 0.22)))
    regions.append(("top_right", int(width * 0.58), 0, width, int(height * 0.22)))

    # Esquinas inferiores
    regions.append(("bottom_left", 0, int(height * 0.78), int(width * 0.42), height))
    regions.append(("bottom_right", int(width * 0.58), int(height * 0.78), width, height))

    # Mitades altas y bajas más cerradas
    regions.append(("upper_right_small", int(width * 0.65), 0, width, int(height * 0.16)))
    regions.append(("upper_left_small", 0, 0, int(width * 0.35), int(height * 0.16)))
    regions.append(("lower_left_small", 0, int(height * 0.84), int(width * 0.35), height))
    regions.append(("lower_right_small", int(width * 0.65), int(height * 0.84), width, height))

    return regions


def preprocess_variants(pil_img):
    """
    Genera varias versiones preprocesadas para mejorar OCR.
    No se guardan en disco.
    """
    variants = []

    # Escala de grises
    gray = ImageOps.grayscale(pil_img)

    # Aumentar tamaño
    scale_factor = 3
    gray_big = gray.resize((gray.width * scale_factor, gray.height * scale_factor), Image.Resampling.LANCZOS)

    # Contraste
    contrast = ImageEnhance.Contrast(gray_big).enhance(2.5)

    # Nitidez leve
    sharp = ImageEnhance.Sharpness(contrast).enhance(2.0)

    variants.append(("gray_big", gray_big))
    variants.append(("contrast", contrast))
    variants.append(("sharp", sharp))

    # Umbrales binarios con OpenCV
    cv_img = cv2.cvtColor(np.array(sharp), cv2.COLOR_GRAY2BGR)
    gray_cv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # Umbral fijo
    _, th1 = cv2.threshold(gray_cv, 180, 255, cv2.THRESH_BINARY)
    variants.append(("th_fixed", Image.fromarray(th1)))

    # Otsu
    _, th2 = cv2.threshold(gray_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("th_otsu", Image.fromarray(th2)))

    # Invertida por si acaso
    inv = ImageOps.invert(Image.fromarray(th2))
    variants.append(("th_otsu_inv", inv))

    return variants


def clean_ocr_text(text):
    """
    Limpia el texto OCR manteniendo números, espacios, guiones, dos puntos y slash.
    """
    if text is None:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # Quitar caracteres raros, pero mantener separadores útiles
    text = re.sub(r"[^0-9:\-\/ ]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_datetime_from_text(text):
    """
    Busca y convierte fechas en formatos como:
    - YYYY-MM-DD HH:MM:SS
    - DD-MM-YYYY HH:MM:SS
    - YYYY/MM/DD HH:MM:SS
    - DD/MM/YYYY HH:MM:SS

    Devuelve datetime o None
    """
    text = clean_ocr_text(text)

    patterns = [
        # YYYY-MM-DD HH:MM:SS o YYYY/MM/DD HH:MM:SS
        r"(?P<y>\d{4})[-/](?P<m>\d{2})[-/](?P<d>\d{2})\s+(?P<h>\d{2}):(?P<min>\d{2}):(?P<s>\d{2})",
        # DD-MM-YYYY HH:MM:SS o DD/MM/YYYY HH:MM:SS
        r"(?P<d>\d{2})[-/](?P<m>\d{2})[-/](?P<y>\d{4})\s+(?P<h>\d{2}):(?P<min>\d{2}):(?P<s>\d{2})",
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                dt = datetime(
                    year=int(m.group("y")),
                    month=int(m.group("m")),
                    day=int(m.group("d")),
                    hour=int(m.group("h")),
                    minute=int(m.group("min")),
                    second=int(m.group("s"))
                )
                return dt
            except ValueError:
                pass

    return None


def ocr_image_region(pil_region):
    """
    Ejecuta OCR sobre varias versiones preprocesadas del recorte.
    Devuelve el mejor datetime detectado, el texto OCR y el nombre de la variante.
    """
    best_dt = None
    best_text = ""
    best_variant = ""

    variants = preprocess_variants(pil_region)

    # PSM 6 y 7 suelen ir bien para líneas cortas
    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 7",
    ]

    for variant_name, img_variant in variants:
        for config in configs:
            text = pytesseract.image_to_string(img_variant, config=config)
            cleaned = clean_ocr_text(text)
            dt = parse_datetime_from_text(cleaned)
            if dt is not None:
                return dt, cleaned, f"{variant_name} | {config}"

            # Guardar el último texto como referencia, aunque no haya parseado
            if len(cleaned) > len(best_text):
                best_text = cleaned
                best_variant = f"{variant_name} | {config}"

    return None, best_text, best_variant


def extract_datetime_from_image(image_path):
    """
    Abre una imagen, prueba OCR sobre múltiples regiones candidatas
    y devuelve el primer datetime válido encontrado.
    """
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return None, "", "", f"Error abriendo imagen: {e}"

    width, height = pil_img.size
    regions = get_candidate_regions(width, height)

    attempts = []

    for region_name, x1, y1, x2, y2 in regions:
        cropped = pil_img.crop((x1, y1, x2, y2))
        dt, ocr_text, variant_used = ocr_image_region(cropped)

        attempts.append({
            "region": region_name,
            "ocr_text": ocr_text,
            "variant": variant_used
        })

        if dt is not None:
            return dt, ocr_text, region_name, ""

    # Si no encuentra nada, devolver el texto más útil
    best_attempt_text = ""
    best_region = ""
    for att in attempts:
        if len(att["ocr_text"]) > len(best_attempt_text):
            best_attempt_text = att["ocr_text"]
            best_region = att["region"]

    return None, best_attempt_text, best_region, "No se detectó una fecha/hora válida"


def build_output_name(dt, counter, original_suffix):
    """
    Formato final:
    YYYY_DDD_HH_COUNTER.ext
    """
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour

    return f"{year}_{day_of_year:03d}_{hour:02d}_{counter}{original_suffix.lower()}"


def copy_failed_image(src_path, relative_folder):
    """
    Copia la imagen fallida a la carpeta de fallos manteniendo estructura.
    """
    fail_dir = FAIL_ROOT / relative_folder
    fail_dir.mkdir(parents=True, exist_ok=True)
    dst = fail_dir / src_path.name
    if not DRY_RUN:
        shutil.copy2(src_path, dst)


# ============================================================
# IMPORT NECESARIO PARA preprocess_variants
# ============================================================
import numpy as np

# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def process_all_images():
    ensure_dirs()

    records = []

    # Contador por cámara y por timestamp horario
    # clave: (camera_folder_name, year, day_of_year, hour)
    counters = {}

    subfolders = [p for p in INPUT_ROOT.iterdir() if p.is_dir()]
    subfolders = sorted(subfolders)

    for folder in subfolders:
        image_files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS]
        image_files = sorted(image_files)

        if MAX_IMAGES_PER_FOLDER is not None:
            image_files = image_files[:MAX_IMAGES_PER_FOLDER]

        relative_folder = folder.relative_to(INPUT_ROOT)
        output_folder = OUTPUT_ROOT / relative_folder
        output_folder.mkdir(parents=True, exist_ok=True)

        print(f"\nProcesando carpeta: {folder}")
        print(f"Imágenes encontradas: {len(image_files)}")

        for img_path in image_files:
            print(f"  -> {img_path.name}")

            dt, ocr_text, region_used, error_msg = extract_datetime_from_image(img_path)

            if dt is None:
                status = "FAIL"
                new_name = ""
                datetime_detected = ""
                year = ""
                day_of_year = ""
                hour = ""
                counter = ""
                if SAVE_FAIL_IMAGES:
                    copy_failed_image(img_path, relative_folder)
            else:
                year = dt.year
                day_of_year = dt.timetuple().tm_yday
                hour = dt.hour

                counter_key = (str(relative_folder), year, day_of_year, hour)
                counters[counter_key] = counters.get(counter_key, 0) + 1
                counter = counters[counter_key]

                new_name = build_output_name(dt, counter, img_path.suffix)
                datetime_detected = dt.strftime("%Y-%m-%d %H:%M:%S")
                status = "OK"

                dst_path = output_folder / new_name

                if not DRY_RUN:
                    shutil.copy2(img_path, dst_path)

            records.append({
                "camera_folder": str(relative_folder),
                "original_filename": img_path.name,
                "output_filename": new_name,
                "ocr_text_raw": ocr_text,
                "datetime_detected": datetime_detected,
                "year": year,
                "day_of_year": day_of_year,
                "hour": hour,
                "counter": counter,
                "region_used": region_used,
                "status": status,
                "error_message": error_msg
            })

    df = pd.DataFrame(records)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    print("\nProceso terminado.")
    print(f"CSV guardado en: {CSV_PATH}")


if __name__ == "__main__":
    process_all_images()