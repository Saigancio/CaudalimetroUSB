#!/usr/bin/env python3
"""Exporta datos de InfluxDB a CSV en el USB indicado por argumento."""

import csv
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/caudalimetro")

import config
import influx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

MOUNT_PATH = Path(config.MOUNT_POINT_USB)


def _leer_ultimo_timestamp() -> int:
    try:
        return int(Path(config.TIMESTAMP_FILE).read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _guardar_ultimo_timestamp(ts_ns: int):
    Path(config.CSV_DIR_LOCAL).mkdir(parents=True, exist_ok=True)
    Path(config.TIMESTAMP_FILE).write_text(str(ts_ns))


def _esta_montado() -> bool:
    """Devuelve True si MOUNT_PATH ya tiene algo montado."""
    result = subprocess.run(["mountpoint", "-q", str(MOUNT_PATH)])
    return result.returncode == 0


def _montar(dispositivo: str) -> bool:
    """Monta dispositivo en MOUNT_PATH. Devuelve True si tuvo éxito."""
    if _esta_montado():
        log.warning("Ya hay algo montado en %s, desmontando primero", MOUNT_PATH)
        _desmontar()

    MOUNT_PATH.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["mount", dispositivo, str(MOUNT_PATH)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error("mount falló: %s", result.stderr.strip())
        return False
    log.info("Montado %s en %s", dispositivo, MOUNT_PATH)
    return True


def _desmontar():
    subprocess.run(["sync"], capture_output=True)
    result = subprocess.run(["umount", str(MOUNT_PATH)], capture_output=True, text=True)
    if result.returncode != 0:
        log.error("umount falló: %s", result.stderr.strip())
    else:
        log.info("Desmontado %s", MOUNT_PATH)


def exportar(dispositivo: str):
    time.sleep(2)

    if not _montar(dispositivo):
        sys.exit(1)

    try:
        ultimo_ts = _leer_ultimo_timestamp()
        log.info("Exportando desde timestamp %d ns", ultimo_ts)

        rows = influx.consultar_desde(ultimo_ts)
        if not rows:
            log.info("Sin datos nuevos para exportar.")
            return

        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        destino = MOUNT_PATH / f"caudal_{ts_str}.csv"

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

        ultimo = rows[-1]["time"]
        _guardar_ultimo_timestamp(int(ultimo.timestamp() * 1e9) + 1)

    finally:
        _desmontar()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        log.error("Uso: exportar.py <dispositivo>  (ej: /dev/sda1)")
        sys.exit(1)
    exportar(sys.argv[1])
