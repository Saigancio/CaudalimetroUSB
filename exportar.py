#!/usr/bin/env python3
"""Exporta datos de InfluxDB a CSV en el primer USB montado disponible."""

import csv
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Garantizar que los módulos del proyecto se encuentren sin importar el CWD
sys.path.insert(0, "/opt/caudalimetro")

import config
import influx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def _leer_ultimo_timestamp() -> int:
    """Devuelve timestamp en ns de la última exportación, o 0 si no existe."""
    try:
        return int(Path(config.TIMESTAMP_FILE).read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _guardar_ultimo_timestamp(ts_ns: int):
    Path(config.CSV_DIR_LOCAL).mkdir(parents=True, exist_ok=True)
    Path(config.TIMESTAMP_FILE).write_text(str(ts_ns))


def _encontrar_usb() -> Path | None:
    """Busca en /proc/mounts un filesystem FAT/exFAT sobre /dev/sd* (USB).
    Funciona independientemente del mount namespace del proceso."""
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            partes = line.split()
            if len(partes) < 3:
                continue
            dispositivo, punto, fstype = partes[0], partes[1], partes[2]
            if fstype.lower() not in ("vfat", "exfat", "ntfs", "fuseblk"):
                continue
            if not dispositivo.startswith("/dev/sd"):
                continue
            p = Path(punto)
            if p.is_dir() and os.access(p, os.W_OK):
                return p
    except OSError:
        pass
    return None


def _esperar_usb(intentos: int = 10, pausa: float = 1.0) -> "Path | None":
    """Reintenta encontrar el USB hasta que se monte (udisksd tarda ~1s tras udev)."""
    for i in range(intentos):
        usb = _encontrar_usb()
        if usb is not None:
            return usb
        log.info("Esperando mount USB... intento %d/%d", i + 1, intentos)
        time.sleep(pausa)
    return None


def exportar():
    usb = _esperar_usb()
    if usb is None:
        log.error("No se encontró USB montado en %s tras esperar", config.MOUNT_POINT_BASE)
        sys.exit(1)

    ultimo_ts = _leer_ultimo_timestamp()
    log.info("Exportando desde timestamp %d ns", ultimo_ts)

    rows = influx.consultar_desde(ultimo_ts)
    if not rows:
        log.info("Sin datos nuevos para exportar.")
        return

    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    nombre = f"caudal_{ts_str}.csv"
    destino = usb / nombre

    with open(destino, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "flujo_slm", "temperatura_C", "flujo_acumulado_sl"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "timestamp": row["time"].isoformat(),
                "flujo_slm": row["flujo"],
                "temperatura_C": row["temperatura"],
                "flujo_acumulado_sl": row["flujo_acumulado"],
            })

    log.info("Exportado %d registros → %s", len(rows), destino)

    # Guarda el timestamp del último registro + 1ns para no repetirlo
    ultimo = rows[-1]["time"]
    ultimo_ns = int(ultimo.timestamp() * 1e9) + 1
    _guardar_ultimo_timestamp(ultimo_ns)


if __name__ == "__main__":
    exportar()
