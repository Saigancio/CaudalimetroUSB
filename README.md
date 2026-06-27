# CaudalimetroUSB

Sistema industrial de adquisición de datos para caudalímetro en laboratorio.

**Stack:** Orange Pi Zero 3 (Arch Linux ARM) · RS485/Modbus RTU · InfluxDB · CSV automático en USB

---

## Dependencias

```
pacman -S python python-pip influxdb2
pip install pymodbus influxdb-client
```

## Instalación

```bash
# 1. Crear usuario de sistema
useradd -r -s /sbin/nologin -d /opt/caudalimetro caudalimetro

# 2. Copiar archivos
mkdir -p /opt/caudalimetro /var/lib/caudalimetro
cp *.py /opt/caudalimetro/
chown -R caudalimetro:caudalimetro /opt/caudalimetro /var/lib/caudalimetro

# 3. Entorno virtual
python -m venv /opt/caudalimetro/venv
/opt/caudalimetro/venv/bin/pip install pymodbus influxdb-client

# 4. Servicio systemd
cp service/caudalimetro.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now caudalimetro

# 5. Regla udev (exportación automática al conectar USB)
cp service/99-usb-export.rules /etc/udev/rules.d/
udevadm control --reload-rules
```

## Configuración

Editar `config.py` antes de instalar:

| Parámetro | Descripción |
|---|---|
| `SERIAL_PORT` | Puerto serie (`/dev/ttyUSB0` o `/dev/ttyS0`) |
| `SLAVE_ADDRESS` | Dirección Modbus del caudalímetro (default: 1) |
| `INFLUX_TOKEN` | Token InfluxDB (vacío si sin autenticación) |
| `MOUNT_POINT_BASE` | Ruta base donde el sistema monta USBs |

## Verificar lectura manual

```bash
/opt/caudalimetro/venv/bin/python lector.py
```

## Logs

```bash
journalctl -u caudalimetro -f
```

## Exportación manual

```bash
/opt/caudalimetro/venv/bin/python exportar.py
```

## Registros Modbus

| Dirección | Contenido | Tipo | Acceso |
|---|---|---|---|
| 0x0015 | Temperatura | int16 | R |
| 0x0016–0x0017 | Flujo | float32 big-endian | R |
| 0x0018–0x001B | Flujo acumulado | uint64 big-endian (4 palabras) | R/W |

> Resetear acumulado: escribir 0x0000 en los 4 registros 0x0018–0x001B.
