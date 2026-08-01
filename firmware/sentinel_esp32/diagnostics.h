#ifndef SENTINEL_DIAGNOSTICS_H
#define SENTINEL_DIAGNOSTICS_H

#include <Arduino.h>

extern unsigned int loopHz;

void initDiagnostics();
void updateDiagnostics();

#endif // SENTINEL_DIAGNOSTICS_H
