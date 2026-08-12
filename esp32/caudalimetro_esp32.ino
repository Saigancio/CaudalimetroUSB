/**
 * Caudalímetro ESP32-S3
 * Lee Modbus RTU cada 10s, guarda en SD, expone la SD como USB MSC al conectar.
 *
 * Hardware:
 *   MAX485  → UART1 (TX=GPIO17, RX=GPIO18, DE/RE=GPIO16)
 *   DS3231  → I2C   (SDA=GPIO8,  SCL=GPIO9)
 *   SD      → SPI   (MOSI=GPIO11, MISO=GPIO13, SCK=GPIO12, CS=GPIO10)
 *   LED     → GPIO4 (enciende cuando la SD está lista para desconectar)
 *
 * Librerías necesarias (Library Manager):
 *   - RTClib (Adafruit)
 *   - SdFat (Bill Greiman)
 *
 * Placa: ESP32S3 Dev Module
 * USB Mode: USB-OTG (Tools → USB Mode → USB-OTG)
 */

#include <Arduino.h>
#include "modbus.h"
#include "reloj.h"
#include "almacenamiento.h"
#include "usb_export.h"

#define INTERVALO_MS 10000UL

unsigned long ultimo_muestreo = 0;

void setup() {
    Serial.begin(115200);
    delay(1000);

    reloj_init();
    sd_init();
    usb_init();   // debe ir después de sd_init — usa el objeto sd
    modbus_init();

    Serial.println("Sistema listo.");
}

void loop() {
    usb_loop();

    if (millis() - ultimo_muestreo >= INTERVALO_MS) {
        ultimo_muestreo = millis();

        DatosCaudal datos;
        if (modbus_leer(&datos)) {
            String ts = reloj_timestamp();
            sd_escribir(ts, datos.flujo, datos.temperatura, datos.acumulado);
            Serial.printf("%s  flujo=%.3f SLM  temp=%.1f°C  acum=%llu\n",
                ts.c_str(), datos.flujo, datos.temperatura, datos.acumulado);
        } else {
            Serial.println("ERROR: sin respuesta Modbus");
        }
    }
}
