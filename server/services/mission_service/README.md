# Mission Service

Maintains autonomous priority-queued tasks for the mobile inspection rover.

## Priorities
- Battery Return: Priority 4 (Critical)
- Emergency Inspection / Alarms: Priority 3
- Restricted Area Checks: Priority 2
- Routine patrols: Priority 1 (Idle baseline)

## Features
- Dynamic pre-emption of active patrols.
- Auto-routing when battery falls below 25%.
