"""Control del pin DE/RE del MAX485 vía sysfs GPIO."""

import time

GPIO_BASE = "/sys/class/gpio"


def exportar(pin: int):
    path = f"{GPIO_BASE}/gpio{pin}"
    try:
        with open(f"{GPIO_BASE}/export", "w") as f:
            f.write(str(pin))
        time.sleep(0.1)
    except OSError:
        pass  # ya exportado
    with open(f"{path}/direction", "w") as f:
        f.write("out")
    set_valor(pin, 0)


def set_valor(pin: int, valor: int):
    with open(f"{GPIO_BASE}/gpio{pin}/value", "w") as f:
        f.write("1" if valor else "0")


def envolver_cliente(client, pin: int):
    """Envuelve client.socket.write para activar DE antes de transmitir
    y volver a modo recepción justo después."""
    exportar(pin)
    socket = client.socket
    write_original = socket.write

    def write_con_de(data):
        set_valor(pin, 1)
        n = write_original(data)
        socket.flush()
        time.sleep(0.002)
        set_valor(pin, 0)
        return n

    socket.write = write_con_de
