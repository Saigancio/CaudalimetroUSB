# Control DE/RE del MAX485 vía GPIO en Orange Pi Zero 3 (Arch Linux ARM)

Guía de diagnóstico para el problema "el maestro Modbus RTU transmite pero el MAX485
no logra dirigir correctamente el bus RS485 half-duplex", en un Orange Pi Zero 3
(SoC Allwinner H616) corriendo Arch Linux ARM (Orange Pi OS Arch).

Este documento existe porque la combinación específica de síntomas (sysfs GPIO
roto, numeración de pines no obvia, regla udev que no se aplica a un nodo ya
creado) es difícil de encontrar documentada en un solo lugar.

## Contexto del problema

El MAX485 es un transceptor RS485 **sin auto-dirección**: requiere que el
maestro controle activamente el pin DE/RE (Driver Enable / Receiver Enable,
normalmente puenteados entre sí en un único pin de control) para alternar
entre transmitir y recibir en cada transacción Modbus.

- DE/RE en HIGH → transmisor habilitado, receptor deshabilitado (modo TX).
- DE/RE en LOW → transmisor en alta impedancia, receptor habilitado (modo RX).

Sin este control activo, el maestro puede enviar la consulta pero nunca logra
poner el MAX485 en modo recepción para escuchar la respuesta del esclavo
(o nunca logra transmitir si el pin quedó flotante/en GND fijo).

## Paso 1 — Elegir el pin GPIO de control

En el header de 26 pines del Orange Pi Zero 3 (v1.2), los pines UART5
(PH2/PH3, usados para el bus Modbus en `/dev/ttyS5`) ya están ocupados.
Se usó **PC9** como línea de control DE/RE, libre en este layout.

### Numeración de líneas GPIO (Allwinner H616/H618)

La numeración de bancos es: A=0, B=1, C=2, D=3 ... I=8.

```
línea = banco*32 + pin
PC9 = 2*32 + 9 = 73
```

Esta fórmula aplica a la numeración de **líneas dentro de `/dev/gpiochip0`**
(interfaz de carácter / libgpiod), confirmada empíricamente: `gpiochip0` expone
exactamente 288 líneas (9 bancos × 32), lo cual valida que es un único chip
contiguo PA..PI.

**Ojo:** esta fórmula NO es necesariamente válida para la interfaz sysfs
legacy (`/sys/class/gpio/`) en este kernel — ver más abajo.

## Paso 2 — Por qué sysfs GPIO falla (y por qué hay que usar libgpiod)

Un primer intento usando el sysfs legacy (`/sys/class/gpio/export`,
`/sys/class/gpio/gpio73/direction`, etc.) falló con:

```
FileNotFoundError: /sys/class/gpio/gpio73/direction
```

Causas combinadas:

1. El export a sysfs puede fallar silenciosamente si el código que lo
   invoca atrapa `OSError` de forma demasiado amplia (`except OSError: pass`),
   ocultando el error real.
2. Kernels modernos (este sistema mostraba `gpiochip0` y `gpiochip352`
   simultáneamente vía sysfs) rompen el supuesto de que existe un único
   chip GPIO contiguo numerado de forma simple — el offset sysfs de un pin
   puede no coincidir con `banco*32+pin`.
3. Distribuciones recientes de Arch Linux ARM priorizan/exponen mejor la
   interfaz de carácter (`/dev/gpiochipN`) sobre sysfs, que está deprecada
   en el kernel.

**Solución: usar `libgpiod` (paquete Python `gpiod`, API v2) contra
`/dev/gpiochip0` en vez de sysfs.** Ver `rs485_gpio.py` en este repo —
usa `gpiod.request_lines()` para tomar la línea 73 como salida y
`req.set_value()` para alternar DE/RE antes/después de cada escritura
en el socket serie del cliente Modbus.

### Verificar la numeración de líneas

```bash
sudo gpioinfo /dev/gpiochip0
```

Confirma cuántas líneas tiene el chip (288 = 9×32 en este caso) y permite
ubicar la línea correspondiente a PC9 contando offsets. Algunas versiones
de las herramientas CLI de libgpiod no incluyen `gpiofind`; en ese caso usar
`gpioinfo` con `sudo` para enumerar manualmente.

## Paso 3 — Permisos: por qué un usuario sin privilegios no puede abrir `/dev/gpiochipN`

Por defecto, `/dev/gpiochip0` pertenece a `root:root` con modo `0660` —
solo root puede leer/escribir. El servicio systemd corre como usuario
`caudalimetro` sin privilegios, así que falla con:

```
PermissionError: [Errno 13] Permission denied
```

### Fix de permisos

1. Crear el grupo `gpio` **antes** de añadir el usuario (paso que se saltó
   y causó `usermod: el grupo «gpio» no existe`):
   ```bash
   sudo groupadd -f gpio
   sudo usermod -aG gpio caudalimetro
   ```

2. Regla udev (`service/99-gpio-permisos.rules`):
   ```
   SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
   ```

3. Agregar `gpio` a `SupplementaryGroups=` en el `.service` (ya incluido
   en `service/caudalimetro.service`, junto con `uucp` para el puerto serie).

4. Recargar reglas:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

### El problema que no documenta nadie: la regla "correcta" no se aplica al nodo existente

Después de todo lo anterior, `/dev/gpiochip0` seguía mostrando:
```
crw-rw---- 1 root root 254, 0 jun 30 02:05 /dev/gpiochip0
```

Diagnóstico:

- `udevadm info -a -p $(udevadm info -q path -n /dev/gpiochip0)` confirmó
  que `KERNEL=="gpiochip0"` y `SUBSYSTEM=="gpio"` son exactamente los
  valores que matchea la regla — el matching en sí estaba bien escrito.
- `sudo udevadm test <devpath>` confirmó que la regla **se evalúa
  correctamente** y produce el resultado esperado (`Device node group: gpio
  (gid=1001)`, `Device node permission: 0660`) — pero `udevadm test` solo
  **simula**, no modifica el nodo real.
- `udevadm trigger` (sin reinicio) **no siempre re-crea el nodo con los
  nuevos permisos** si el nodo fue creado muy temprano en el boot por
  devtmpfs, antes de que la regla existiera en disco.

**Fix: reiniciar el sistema (`sudo reboot`).** Es la única forma confiable
de que el nodo `/dev/gpiochip0` se recree desde cero ya con la regla
udev (que para entonces sí existe en `/etc/udev/rules.d/`) aplicada desde
el primer `ACTION=add`.

Después del reinicio:
```bash
ls -l /dev/gpiochip0
# crw-rw---- 1 root gpio 254, 0 ... /dev/gpiochip0
```

## Resumen / checklist

- [ ] Confirmar pin GPIO libre en el header y su número de línea
      (`banco*32+pin`) contra `/dev/gpiochip0` con `gpioinfo`.
- [ ] Usar `libgpiod` (`gpiod` v2 API), no sysfs.
- [ ] `groupadd -f gpio` antes de `usermod -aG gpio <usuario>`.
- [ ] Regla udev `SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"`
      en `/etc/udev/rules.d/`.
- [ ] `SupplementaryGroups=gpio` en el `.service`.
- [ ] Reiniciar el sistema — no confiar en `udevadm trigger` solo para
      nodos GPIO ya existentes desde boot temprano.
- [ ] Verificar `ls -l /dev/gpiochip0` muestra grupo `gpio` antes de
      reiniciar el servicio.

## Después de resolver permisos: si Modbus sigue sin responder

Si el servicio arranca sin `PermissionError` pero sigue dando
`No response received after 3 retries`, el problema ya no es de Linux/GPIO
sino de la capa física RS485:

- Esclavo (caudalímetro) apagado o A/B no conectados → produce exactamente
  este mismo error (el maestro transmite, nadie responde).
- A/B (D+/D-) invertidos entre el MAX485 y el instrumento.
- Dirección Modbus (`SLAVE_ADDRESS`) o baudrate/paridad no coinciden con
  la configuración real del instrumento (no asumir, confirmar contra
  datasheet o menú del equipo).
