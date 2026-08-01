#include "logging.h"
#include <stdarg.h>

void logMsg(const char* level, const char* format, ...) {
  char buf[256];
  va_list args;
  va_start(args, format);
  vsnprintf(buf, sizeof(buf), format, args);
  va_end(args);
  Serial.printf("[%6.1f] [%s] %s\n", millis() / 1000.0, level, buf);
}
