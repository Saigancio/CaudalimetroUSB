#pragma once
#include <Arduino.h>

struct DatosCaudal {
    float flujo;
    float temperatura;
    uint64_t acumulado;
};

void modbus_init();
bool modbus_leer(DatosCaudal* datos);
