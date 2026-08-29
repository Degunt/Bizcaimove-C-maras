import shutil
from pathlib import Path
from datetime import datetime, timedelta
import re

# ===============================
# RUTAS
# ===============================

INPUT_FOLDER = Path(r"D:\3. Imágenes_reescaladas\3. Larrondo_reescalada")
OUTPUT_FOLDER = Path(r"D:\4. Imagenes_renombradas\4. Larrondo_renombrada")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ===============================
# REGEX PARA LEER EL NOMBRE
# ===============================

pattern = re.compile(r".*_(\d{8})_(\d{4})")

# ===============================
# CONTADORES POR HORA
# ===============================

counters = {}

# ===============================
# PROCESAR ARCHIVOS
# ===============================

files = sorted(INPUT_FOLDER.iterdir())

for file in files:

    if not file.is_file():
        continue

    match = pattern.match(file.stem)

    if not match:
        print("Nombre no reconocido:", file.name)
        continue

    date_str = match.group(1)
    time_str = match.group(2)

    year = int(date_str[0:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    hour = int(time_str[0:2])
    minute = int(time_str[2:4])

    # Fecha en UTC
    dt = datetime(year, month, day, hour, minute)

    # Día del año
    day_of_year = dt.timetuple().tm_yday

    # ===============================
    # AJUSTE HORARIO ESPAÑA
    # ===============================

    if year == 2026 and day_of_year >= 87:
        dt = dt + timedelta(hours=2)
    else:
        dt = dt + timedelta(hours=1)

    # recalcular día del año si cambió de día
    day_of_year = dt.timetuple().tm_yday

    hour_local = dt.hour

    # ===============================
    # CONTADOR
    # ===============================

    key = (dt.year, day_of_year, hour_local)

    counters[key] = counters.get(key, 0) + 1

    counter = counters[key]

    # ===============================
    # NUEVO NOMBRE
    # ===============================

    new_name = f"{dt.year}_{day_of_year:03d}_{hour_local:02d}_{counter}{file.suffix}"

    shutil.copy2(file, OUTPUT_FOLDER / new_name)

    print(file.name, "->", new_name)

print("Proceso terminado")
