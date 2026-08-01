#ifndef SENTINEL_LOGGING_H
#define SENTINEL_LOGGING_H

#include <Arduino.h>

void logMsg(const char* level, const char* format, ...);

#define LOG_INFO(fmt, ...)  logMsg("INFO", fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...)  logMsg("WARN", fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...) logMsg("ERROR", fmt, ##__VA_ARGS__)
#define LOG_DEBUG(fmt, ...) logMsg("DEBUG", fmt, ##__VA_ARGS__)

#endif // SENTINEL_LOGGING_H
