#!/usr/bin/env python3
"""Daemon de lectura Modbus RTU → InfluxDB."""

import logging
import signal
import struct
import sys
import time

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

import config
import influx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

_running = True


def _stop(sig, frame):
    global _running
    log.info("Señal %s recibida, parando...", sig)
    _running = False


def _regs_a_float32(hi: int, lo: int) -> float:
    """Convierte dos registros de 16 bits (big-endian) a float32."""
    raw = struct.pack(">HH", hi, lo)
    return struct.unpack(">f", raw)[0]


def _regs_a_uint64(w3: int, w2: int, w1: int, w0: int) -> int:
    """Convierte cuatro registros de 16 bits (big-endian) a uint64."""
    raw = struct.pack(">HHHH", w3, w2, w1, w0)
    return struct.unpack(">Q", raw)[0]


def _leer_datos(client: ModbusSerialClient) -> tuple[float, int, int] | None:
    # Leer bloque 0x0015..0x001B (7 registros) en una sola trama
    resp = client.read_holding_registers(
        address=0x0015, count=7, slave=config.SLAVE_ADDRESS
    )
    if resp.isError():
        log.warning("Error Modbus: %s", resp)
        return None

    regs = resp.registers  # [0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B]
    temperatura = regs[0]
    flujo = _regs_a_float32(regs[1], regs[2])
    flujo_acumulado = _regs_a_uint64(regs[3], regs[4], regs[5], regs[6])
    return flujo, temperatura, flujo_acumulado


def resetear_acumulado(client: ModbusSerialClient):
    """Escribe cero en los 4 registros del acumulado (R/W)."""
    valores = [0, 0, 0, 0]
    resp = client.write_registers(
        address=0x0018, values=valores, slave=config.SLAVE_ADDRESS
    )
    if resp.isError():
        log.error("Error al resetear acumulado: %s", resp)
    else:
        log.info("Acumulado reseteado a 0.")


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    client = ModbusSerialClient(
        port=config.SERIAL_PORT,
        baudrate=config.BAUDRATE,
        bytesize=config.BYTESIZE,
        stopbits=config.STOPBITS,
        parity=config.PARITY,
        timeout=config.TIMEOUT,
    )

    if not client.connect():
        log.error("No se pudo conectar a %s", config.SERIAL_PORT)
        sys.exit(1)

    log.info("Conectado a %s, muestreando cada %ds", config.SERIAL_PORT, config.INTERVALO_SEGUNDOS)

    errores_consecutivos = 0
    MAX_ERRORES = 10

    while _running:
        t0 = time.monotonic()
        try:
            datos = _leer_datos(client)
            if datos:
                flujo, temperatura, acumulado = datos
                influx.escribir(flujo, temperatura, acumulado)
                log.info("flujo=%.3f m³/h  temp=%d°C  acum=%d", flujo, temperatura, acumulado)
                errores_consecutivos = 0
            else:
                errores_consecutivos += 1
        except ModbusException as e:
            log.error("ModbusException: %s", e)
            errores_consecutivos += 1
        except Exception as e:
            log.error("Error inesperado: %s", e)
            errores_consecutivos += 1

        if errores_consecutivos >= MAX_ERRORES:
            log.error("%d errores consecutivos, reconectando...", MAX_ERRORES)
            client.close()
            time.sleep(5)
            client.connect()
            errores_consecutivos = 0

        elapsed = time.monotonic() - t0
        sleep_time = max(0.0, config.INTERVALO_SEGUNDOS - elapsed)
        time.sleep(sleep_time)

    client.close()
    influx.cerrar()
    log.info("Parado.")


if __name__ == "__main__":
    main()
