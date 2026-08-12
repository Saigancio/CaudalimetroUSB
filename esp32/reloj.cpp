#include "reloj.h"
#include <RTClib.h>

static RTC_DS3231 rtc;

void reloj_init() {
    if (!rtc.begin()) {
        Serial.println("ERROR: DS3231 no encontrado");
        while (1);
    }
    if (rtc.lostPower()) {
        Serial.println("RTC perdió la hora, ajustando a fecha de compilación");
        rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
}

String reloj_timestamp() {
    DateTime now = rtc.now();
    char buf[20];
    snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d",
        now.year(), now.month(), now.day(),
        now.hour(), now.minute(), now.second());
    return String(buf);
}
