# Sentinel Twin X — Mission Control System

This document outlines the FSM (Finite State Machine) states and priority preemption structure of the mission manager service.

## Mission FSM States

The Mission Service maintains the high-level operational state of the rover simulator:

*   **`IDLE`**: Stationary at base hub. Ready to receive commands.
*   **`PATROL`**: Sweeping the building zones sequentially.
*   **`INSPECTION`**: Performing scheduled non-emergency safety assessments.
*   **`EMERGENCY`**: Interrogating high-risk anomalies (e.g. fire/gas events).
*   **`RETURN_HOME`**: Traveling back to base charging station (e.g. battery low recall).

## Preemption Priority Table

Missions are dispatched based on priority values. Higher-priority missions immediately suspend lower-priority ones:

| Priority | Mission Type | FSM State | Description |
| :---: | :--- | :--- | :--- |
| **4** | `BATTERY_RETURN` | `RETURN_HOME` | Preempts all. Recalls rover to base for charging. |
| **3** | `FIRE_VERIFICATION` | `EMERGENCY` | Preempts inspections/patrols to scan active flames. |
| **3** | `GAS_LEAK_INSPECTION` | `EMERGENCY` | Preempts inspections/patrols to audit toxic gas. |
| **3** | `EMERGENCY_INSPECTION` | `EMERGENCY` | Triggered by general high-risk zone alerts. |
| **2** | `RESTRICTED_AREA_CHECK` | `INSPECTION` | Scheduled manual room security checks. |
| **1** | `ROUTINE_PATROL` | `PATROL` | Default building sweeps when queue is empty. |

## Transition Logging

Every state transition:
1. Logs `info` logs to terminal outputs.
2. Appends audit events to the operations SQLite database.
3. Broadcasts timeline messages to the Operator's Dashboard.
