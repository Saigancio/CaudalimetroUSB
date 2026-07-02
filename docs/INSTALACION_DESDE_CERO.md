# Instalación desde cero — CaudalimetroUSB

Guía completa para reinstalar el sistema en un Orange Pi Zero 3 con SD nueva.
Incluye todos los pasos de configuración de hardware y software, en orden correcto.

## Hardware necesario

- Orange Pi Zero 3 (SoC Allwinner H616/H618)
- Tarjeta SD nueva (mínimo 8GB, marca reconocida: Samsung, SanDisk, Kingston)
- Módulo MAX485 conectado a:
  - UART5: PH2 (TX, pin 8) / PH3 (RX, pin 10) → `/dev/ttyS5`
  - DE/RE: PC9 (pin libre del header) → línea GPIO 73 de `/dev/gpiochip0`
- Caudalímetro con RS485/Modbus RTU: 9600-8N1, dirección esclavo 1

---

## 1. Flashear SD y primer boot

1. Descargar imagen **Orange Pi OS (Arch)** para Zero 3 desde el sitio oficial de Orange Pi.
2. Flashear con `dd` o Balena Etcher a la SD nueva.
3. Insertar SD, conectar al Orange Pi, bootear.
4. Conectar por SSH o terminal local. Usuario por defecto: `orangepi` / `orangepi`.

---

## 2. Activar UART5 (PH2/PH3)

UART5 no viene activo por defecto — hay que habilitarlo en el bootloader.

```bash
sudo nano /boot/orangepiEnv.txt
```

Agregar o verificar que exista la línea:

```
overlays=uart5
```

> **Nota**: en algunos sistemas el archivo es `/boot/extlinux/extlinux.conf`.
> En ese caso buscar la línea `fdtoverlays` y agregar `/overlays/sun50i-h616-uart5.dtbo`.

Guardar y reiniciar:

```bash
sudo reboot
```

Verificar que el puerto existe:

```bash
ls /dev/ttyS5
```

---

## 3. Instalar dependencias del sistema

```bash
sudo pacman -Syu
sudo pacman -S python python-pip influxdb influx-cli git libgpiod
```

> El paquete `influxdb` en Arch Linux ARM aarch64 es InfluxDB 2.x.

Habilitar InfluxDB:

```bash
sudo systemctl enable --now influxdb
```

---

## 4. Configurar InfluxDB

Crear la organización, bucket y token que usa el código:

```bash
influx setup \
  --username admin \
  --password adminadmin \
  --org lab \
  --bucket caudalimetro \
  --token aaeVhSnGzZe-8oT94dJT54Rab2i6xGCacJXZO6PBmpYyKk09NHWSAgAh-oYA25oD0UQM-zbMhKpzM7noBF7wog== \
  --force
```

Verificar:

```bash
curl http://localhost:8086/health
# debe responder: {"status":"pass",...}
```

---

## 5. Crear usuario del sistema

```bash
sudo useradd -r -s /sbin/nologin -d /opt/caudalimetro caudalimetro
sudo groupadd -f gpio
sudo usermod -aG uucp gpio caudalimetro
```

> **Importante**: crear el grupo `gpio` ANTES de `usermod -aG gpio`.
> Verificar con `groups caudalimetro` que aparezcan tanto `uucp` como `gpio`.

---

## 6. Clonar el repositorio e instalar

El repositorio es público, no requiere autenticación para clonar. Si git no está
instalado, instalarlo primero (debería haber quedado del paso 3).

```bash
sudo mkdir -p /opt/caudalimetro /var/lib/caudalimetro
sudo git clone https://github.com/saigancio/caudalimetrousb.git /opt/caudalimetro
```

> Si el repo tiene ramas, el código de producción está en la rama
> `claude/caudalimetro-usb-system-9wug68`. Cambiar a ella:
> ```bash
> cd /opt/caudalimetro
> sudo git checkout claude/caudalimetro-usb-system-9wug68
> ```

Dar ownership al usuario del servicio:

```bash
sudo chown -R caudalimetro:caudalimetro /opt/caudalimetro /var/lib/caudalimetro
```

> **Nota**: si más adelante hacés `git pull` para actualizar el código, hay que
> correrlo como root o con sudo desde `/opt/caudalimetro`, y volver a hacer
> `chown` si los archivos nuevos quedan con otro dueño. Alternativamente:
> ```bash
> sudo git -C /opt/caudalimetro pull
> sudo chown -R caudalimetro:caudalimetro /opt/caudalimetro
> ```

Crear entorno virtual e instalar dependencias Python:

> **Por qué un entorno virtual**: Arch Linux no permite instalar paquetes Python
> con `pip` de forma global (da error `externally-managed-environment`). El entorno
> virtual (`venv`) es una carpeta aislada con su propio Python y pip donde sí se
> puede instalar sin tocar el sistema. Todo el código del servicio usa el Python
> de este venv, no el del sistema.

```bash
sudo -u caudalimetro python -m venv /opt/caudalimetro/venv
sudo -u caudalimetro /opt/caudalimetro/venv/bin/pip install pymodbus influxdb-client gpiod
```

Verificar que los paquetes quedaron instalados en el venv:

```bash
/opt/caudalimetro/venv/bin/pip list | grep -E "pymodbus|influxdb|gpiod"
```

---

## 7. Instalar reglas udev y servicio systemd

```bash
# Regla GPIO (permisos para /dev/gpiochip0)
sudo cp /opt/caudalimetro/service/99-gpio-permisos.rules /etc/udev/rules.d/

# Regla USB export (ejecuta exportar.py al conectar USB)
sudo cp /opt/caudalimetro/service/99-usb-export.rules /etc/udev/rules.d/

# Servicio systemd
sudo cp /opt/caudalimetro/service/caudalimetro.service /etc/systemd/system/

sudo udevadm control --reload-rules
sudo systemctl daemon-reload
```

---

## 8. Reiniciar el sistema

**Este paso es obligatorio** para que la regla udev de GPIO tome efecto sobre
`/dev/gpiochip0`. El nodo se crea muy temprano en el boot y `udevadm trigger`
solo no es suficiente — el nodo debe recrearse desde cero.

```bash
sudo reboot
```

Después del reboot, verificar permisos:

```bash
ls -l /dev/gpiochip0
# debe mostrar: crw-rw---- 1 root gpio ...
```

---

## 9. Habilitar e iniciar el servicio

```bash
sudo systemctl enable --now caudalimetro
```

Si da error `is masked`:
```bash
sudo systemctl unmask caudalimetro
sudo cp /opt/caudalimetro/service/caudalimetro.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now caudalimetro
```

Ver logs en tiempo real:
```bash
journalctl -u caudalimetro -f
```

Ver errores del servicio si no arranca:
```bash
systemctl status caudalimetro
journalctl -u caudalimetro -n 50 --no-pager
```

El log debe mostrar, en orden:
1. `Control DE/RE activo en GPIO 73`
2. `Conectado a /dev/ttyS5, muestreando cada 10s`
3. Lecturas de flujo/temperatura/acumulado (con el caudalímetro encendido y A/B conectados)

---

## 10. Verificar lectura manual (opcional)

```bash
sudo systemctl stop caudalimetro
cd /opt/caudalimetro
sudo -u caudalimetro /opt/caudalimetro/venv/bin/python lector.py
```

---

## 11. Configurar exportación a USB

La regla udev `99-usb-export.rules` ya dispara `exportar.py` automáticamente
al conectar un USB. Verificar manualmente:

```bash
sudo -u caudalimetro /opt/caudalimetro/venv/bin/python /opt/caudalimetro/exportar.py
```

---

## Troubleshooting rápido

| Síntoma | Causa | Fix |
|---|---|---|
| `PermissionError` en `/dev/gpiochip0` | Grupo `gpio` no existe o regla udev no aplicada | `groupadd -f gpio`, `usermod -aG gpio caudalimetro`, reboot |
| `PermissionError` en `/dev/ttyS5` | Usuario no en grupo `uucp` | `usermod -aG uucp caudalimetro` |
| `No response received after 3 retries` | A/B invertidos, esclavo apagado, dirección/baudrate incorrectos | Verificar cableado A/B, encender esclavo, confirmar config Modbus |
| `Could not exclusively lock port` | El servicio ya tiene el puerto abierto | `systemctl stop caudalimetro` antes de correr manualmente |
| `ModuleNotFoundError: No module named 'config'` | Script corrido desde directorio incorrecto | `cd /opt/caudalimetro` antes de correr |
| `Connection refused` en InfluxDB | InfluxDB no está corriendo | `systemctl start influxdb` |
| `authorization not found` en InfluxDB | Setup inicial no realizado | Correr `influx setup ...` del paso 4 |
| `/dev/ttyS5` no existe después del reboot | Overlay UART5 no activo | Verificar `overlays=uart5` en `/boot/orangepiEnv.txt` |

## Referencia de pines (header 26 pines, Orange Pi Zero 3 v1.2)

| Pin | Función | Uso |
|---|---|---|
| 8 | PH2 / UART5-TX | TX Modbus → MAX485 DI |
| 10 | PH3 / UART5-RX | RX Modbus ← MAX485 RO |
| Libre | PC9 / GPIO línea 73 | DE/RE del MAX485 |
| A | MAX485 A (D+) | RS485 bus positivo → caudalímetro |
| B | MAX485 B (D-) | RS485 bus negativo → caudalímetro |
