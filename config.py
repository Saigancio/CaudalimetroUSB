# Modbus RTU
SERIAL_PORT = "/dev/ttyS5"
BAUDRATE = 9600
BYTESIZE = 8
STOPBITS = 1
PARITY = "N"
TIMEOUT = 1.0
SLAVE_ADDRESS = 1

# Registros Modbus (dirección base 0-indexed para pymodbus)
REG_TEMPERATURA = 0x0015   # int16
REG_FLUJO_HI    = 0x0016   # uint32 word alto (valor en centésimas de SLM)
REG_FLUJO_LO    = 0x0017   # uint32 word bajo
REG_ACUM_W3     = 0x0018   # uint64 acumulado word 3 (más significativo)
REG_ACUM_W2     = 0x0019   # uint64 acumulado word 2
REG_ACUM_W1     = 0x001A   # uint64 acumulado word 1
REG_ACUM_W0     = 0x001B   # uint64 acumulado word 0 (menos significativo)

# MAX485: línea GPIO para control DE/RE vía libgpiod, en /dev/gpiochip0.
# Numeración: banco*32+pin (banco A=0..I=8). PC9 = 2*32+9 = línea 73.
# None = sin control SW (jumper fijo a TX)
RS485_DE_PIN = 73

# Muestreo
INTERVALO_SEGUNDOS = 10

# InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "aaeVhSnGzZe-8oT94dJT54Rab2i6xGCacJXZO6PBmpYyKk09NHWSAgAh-oYA25oD0UQM-zbMhKpzM7noBF7wog=="
INFLUX_ORG = "lab"
INFLUX_BUCKET = "caudalimetro"

# Exportación CSV
CSV_DIR_LOCAL = "/var/lib/caudalimetro"   # directorio de trabajo local
MOUNT_POINT_USB = "/mnt/caudalimetro-usb"  # path fijo donde el script monta el USB
TIMESTAMP_FILE = f"{CSV_DIR_LOCAL}/.last_export"
