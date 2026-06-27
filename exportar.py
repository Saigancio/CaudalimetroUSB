#!/usr/bin/env python3
"""Exporta datos de InfluxDB a CSV en el primer USB montado disponible."""

import csv
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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
    """Devuelve el primer punto de montaje USB disponible con escritura."""
    base = Path(config.MOUNT_POINT_BASE)
    if not base.exists():
        return None
    for entry in sorted(base.iterdir()):
        if entry.is_dir() and os.access(entry, os.W_OK):
            # Descarta el home del usuario y mounts del sistema
            if entry.name.startswith(("sd", "mmcblk", "sda", "sdb", "sdc", "usb")):
                return entry
    # Fallback: cualquier directorio montado con escritura (excluye / y /boot)
    for entry in sorted(base.iterdir()):
        if entry.is_dir() and os.access(entry, os.W_OK) and entry.name not in ("root", "boot"):
            return entry
    return None


def exportar():
    ultimo_ts = _leer_ultimo_timestamp()
    log.info("Exportando desde timestamp %d ns", ultimo_ts)

    rows = influx.consultar_desde(ultimo_ts)
    if not rows:
        log.info("Sin datos nuevos para exportar.")
        return

    usb = _encontrar_usb()
    if usb is None:
        log.error("No se encontró USB montado en %s", config.MOUNT_POINT_BASE)
        sys.exit(1)

    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    nombre = f"caudal_{ts_str}.csv"
    destino = usb / nombre

    with open(destino, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "flujo_m3h", "temperatura_C", "flujo_acumulado_m3"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "timestamp": row["time"].isoformat(),
                "flujo_m3h": row["flujo"],
                "temperatura_C": row["temperatura"],
                "flujo_acumulado_m3": row["flujo_acumulado"],
            })

    log.info("Exportado %d registros → %s", len(rows), destino)

    # Guarda el timestamp del último registro + 1ns para no repetirlo
    ultimo = rows[-1]["time"]
    ultimo_ns = int(ultimo.timestamp() * 1e9) + 1
    _guardar_ultimo_timestamp(ultimo_ns)


if __name__ == "__main__":
    exportar()
