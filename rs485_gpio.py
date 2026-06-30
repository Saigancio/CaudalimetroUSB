"""Control del pin DE/RE del MAX485 vía libgpiod (interfaz de carácter /dev/gpiochipN)."""

import time

import gpiod
from gpiod.line import Direction, Value

CHIP_PATH = "/dev/gpiochip0"

_request = None


def _abrir(linea: int):
    global _request
    if _request is None:
        _request = gpiod.request_lines(
            CHIP_PATH,
            consumer="caudalimetro-rs485",
            config={
                linea: gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.INACTIVE
                )
            },
        )
    return _request


def envolver_cliente(client, linea: int):
    """Envuelve client.socket.write para activar DE antes de transmitir
    y volver a modo recepción justo después."""
    req = _abrir(linea)
    socket = client.socket
    write_original = socket.write

    def write_con_de(data):
        req.set_value(linea, Value.ACTIVE)
        n = write_original(data)
        socket.flush()
        time.sleep(0.002)
        req.set_value(linea, Value.INACTIVE)
        return n

    socket.write = write_con_de
