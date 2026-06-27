# Modbus RTU
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
BYTESIZE = 8
STOPBITS = 1
PARITY = "N"
TIMEOUT = 1.0
SLAVE_ADDRESS = 1

# Registros Modbus (dirección base 0-indexed para pymodbus)
REG_TEMPERATURA = 0x0015   # int16
REG_FLUJO_HI    = 0x0016   # float32 word alto
REG_FLUJO_LO    = 0x0017   # float32 word bajo
REG_ACUM_W3     = 0x0018   # uint64 acumulado word 3 (más significativo)
REG_ACUM_W2     = 0x0019   # uint64 acumulado word 2
REG_ACUM_W1     = 0x001A   # uint64 acumulado word 1
REG_ACUM_W0     = 0x001B   # uint64 acumulado word 0 (menos significativo)

# MAX485: pin GPIO para control DE/RE (BCM). None = sin control SW (jumper fijo a TX)
RS485_DE_PIN = None

# Muestreo
INTERVALO_SEGUNDOS = 10

# InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = ""           # vacío = auth deshabilitado (InfluxDB OSS sin auth)
INFLUX_ORG = "lab"
INFLUX_BUCKET = "caudalimetro"

# Exportación CSV
CSV_DIR_LOCAL = "/var/lib/caudalimetro"   # directorio de trabajo local
MOUNT_POINT_BASE = "/media"               # busca USB aquí
TIMESTAMP_FILE = f"{CSV_DIR_LOCAL}/.last_export"
