#include "almacenamiento.h"
#include <SdFat.h>

#define SD_CS   10
#define SD_MOSI 11
#define SD_MISO 13
#define SD_SCK  12

#define CSV_PATH "/datos.csv"

SdFat sd;

void sd_init() {
    SPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
    if (!sd.begin(SdSpiConfig(SD_CS, DEDICATED_SPI, SD_SCK_MHZ(20)))) {
        Serial.println("ERROR: SD no encontrada");
        while (1);
    }
    // Crear encabezado si el archivo no existe
    if (!sd.exists(CSV_PATH)) {
        FsFile f = sd.open(CSV_PATH, O_WRITE | O_CREAT);
        if (f) {
            f.println("timestamp,flujo_slm,temperatura_C,flujo_acumulado_sl");
            f.close();
        }
    }
    Serial.println("SD lista.");
}

void sd_escribir(const String& timestamp, float flujo, float temperatura, uint64_t acumulado) {
    FsFile f = sd.open(CSV_PATH, O_WRITE | O_APPEND);
    if (!f) {
        Serial.println("ERROR: no se pudo abrir CSV");
        return;
    }
    char linea[80];
    snprintf(linea, sizeof(linea), "%s,%.3f,%.1f,%llu\n",
        timestamp.c_str(), flujo, temperatura, acumulado);
    f.print(linea);
    f.close();
}
