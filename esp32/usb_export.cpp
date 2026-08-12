#include "usb_export.h"
#include <Arduino.h>
#include <SdFat.h>
#include <USB.h>
#include <USBMSC.h>

#define PIN_LED  4
#define SD_CS   10
#define SD_MOSI 11
#define SD_MISO 13
#define SD_SCK  12

extern SdFat sd;

static USBMSC msc;

static int32_t onRead(uint32_t lba, uint32_t offset, void* buffer, uint32_t bufsize) {
    uint32_t sector = lba + offset / 512;
    if (!sd.card()->readSectors(sector, (uint8_t*)buffer, bufsize / 512)) return -1;
    return bufsize;
}

static int32_t onWrite(uint32_t lba, uint32_t offset, uint8_t* buffer, uint32_t bufsize) {
    uint32_t sector = lba + offset / 512;
    if (!sd.card()->writeSectors(sector, (uint8_t*)buffer, bufsize / 512)) return -1;
    // Forzar re-mount del volumen después de escritura del host
    sd.volumeBegin();
    return bufsize;
}

static bool onStartStop(uint8_t power_condition, bool start, bool load_eject) {
    if (load_eject && !start) {
        // Host eyectó — LED apagado
        digitalWrite(PIN_LED, LOW);
    }
    return true;
}

void usb_init() {
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    uint32_t sectores = sd.card()->sectorCount();

    msc.vendorID("CAUDAL");
    msc.productID("DATOS");
    msc.productRevision("1.0");
    msc.onRead(onRead);
    msc.onWrite(onWrite);
    msc.onStartStop(onStartStop);
    msc.mediaPresent(true);
    msc.begin(sectores, 512);

    USB.begin();
    Serial.println("USB MSC listo.");
}

void usb_led_ok() {
    digitalWrite(PIN_LED, HIGH);
}

void usb_loop() {
    // El stack USB maneja la transferencia automáticamente.
    // El LED verde se enciende desde almacenamiento.cpp cuando termina de escribir.
}
