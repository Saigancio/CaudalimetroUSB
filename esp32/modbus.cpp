#include "modbus.h"

#define RS485_TX    17
#define RS485_RX    18
#define RS485_DE    16
#define SLAVE_ADDR  1
#define BAUDRATE    9600

// Registros (0-indexed)
#define REG_TEMP     0x0015
#define REG_FLUJO_HI 0x0016
#define REG_FLUJO_LO 0x0017
#define REG_ACUM_W3  0x0018

static HardwareSerial rs485(1);

static void _de_tx() { digitalWrite(RS485_DE, HIGH); }
static void _de_rx() { digitalWrite(RS485_DE, LOW); }

static uint16_t _crc16(uint8_t* buf, uint8_t len) {
    uint16_t crc = 0xFFFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= buf[i];
        for (uint8_t j = 0; j < 8; j++)
            crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1;
    }
    return crc;
}

static bool _leer_registros(uint16_t reg, uint8_t count, uint16_t* out) {
    uint8_t req[8];
    req[0] = SLAVE_ADDR;
    req[1] = 0x03;
    req[2] = reg >> 8;
    req[3] = reg & 0xFF;
    req[4] = 0x00;
    req[5] = count;
    uint16_t crc = _crc16(req, 6);
    req[6] = crc & 0xFF;
    req[7] = crc >> 8;

    _de_tx();
    rs485.write(req, 8);
    rs485.flush();
    _de_rx();

    uint8_t resp[5 + count * 2];
    uint32_t t = millis();
    uint8_t idx = 0;
    while (millis() - t < 1000 && idx < sizeof(resp)) {
        if (rs485.available())
            resp[idx++] = rs485.read();
    }

    if (idx < sizeof(resp)) return false;
    uint16_t crc_recv = resp[idx-2] | (resp[idx-1] << 8);
    if (_crc16(resp, idx-2) != crc_recv) return false;

    for (uint8_t i = 0; i < count; i++)
        out[i] = (resp[3 + i*2] << 8) | resp[4 + i*2];

    return true;
}

void modbus_init() {
    pinMode(RS485_DE, OUTPUT);
    _de_rx();
    rs485.begin(BAUDRATE, SERIAL_8N1, RS485_RX, RS485_TX);
}

bool modbus_leer(DatosCaudal* datos) {
    uint16_t regs[7];
    if (!_leer_registros(REG_TEMP, 7, regs)) return false;

    datos->temperatura = (int16_t)regs[0] / 10.0f;
    uint32_t flujo_raw = ((uint32_t)regs[1] << 16) | regs[2];
    datos->flujo = flujo_raw / 100.0f;
    datos->acumulado = ((uint64_t)regs[3] << 48) |
                       ((uint64_t)regs[4] << 32) |
                       ((uint64_t)regs[5] << 16) |
                        (uint64_t)regs[6];
    return true;
}
