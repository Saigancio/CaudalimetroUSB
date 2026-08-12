#pragma once
#include <Arduino.h>
#include <SdFat.h>

extern SdFat sd;

void sd_init();
void sd_escribir(const String& timestamp, float flujo, float temperatura, uint64_t acumulado);
