# Wiring — Sentinel Twin (Aegis)

> **Power everything down before changing any wire.**

---

## 1. Read this before touching anything

Three problems in the original sketch will destroy hardware or prevent boot.

### 1.1 `GPIO12` must not drive a motor input

GPIO12 (`MTDI`) is a **strapping pin**. If it is HIGH when the ESP32 boots, the chip configures its flash regulator for 1.8 V and **the board does not boot**. An L298N input pin sitting on GPIO12 will do this intermittently, producing "random" boot failures.

`config.h` contains a compile-time `#error` that refuses to build if any motor pin is on GPIO12.

### 1.2 5 V signals must not enter 3.3 V pins

The ESP32 is **not 5 V tolerant**. These three signals are 5 V and each needs a divider:

| Signal | Source | Goes to |
|---|---|---|
| HC-SR04 `ECHO` | 5 V logic | GPIO18 |
| MQ-2 `AOUT` | 0–5 V analog | GPIO34 |
| Battery `+` | pack voltage | GPIO35 |

Connecting them directly may appear to work for hours, then kill the pin.

### 1.3 `ADC2` is unusable while WiFi is on

The ESP32's ADC2 block is used by the WiFi radio. Any `analogRead()` on an ADC2 pin returns garbage (usually `0`) once WiFi associates. Because this project requires WiFi for MQTT, **every analog sensor must be on ADC1**: `GPIO 32, 33, 34, 35, 36, 39`.

That is only six pins. This project needs MQ-2 + battery + flame (3) *and* two PWM outputs. It fits — barely. **MQ-7 and MQ-135 have been dropped**; there is no pin for them. If you need them, add an **ADS1115** (I²C, 4-channel, ~₹150) and move all analog sensors onto it.

---

## 2. Pin map

| Function | GPIO | Notes |
|---|---|---|
| MQ-2 `AOUT` | 34 | input-only, ADC1. **10k/20k divider** |
| Battery sense | 35 | input-only, ADC1. **100k/22k divider** |
| Flame (analog) | 36 | input-only, ADC1. divider if 5 V |
| DHT22 `DATA` | 4 | 4.7 kΩ pull-up to 3.3 V |
| HC-SR04 `TRIG` | 5 | 3.3 V out is accepted |
| HC-SR04 `ECHO` | 18 | **1k/2k divider** |
| IR left `OUT` | 19 | active-LOW typical |
| IR right `OUT` | 21 | |
| Buzzer `+` | 23 | active buzzer |
| L298N `ENA` | 32 | LEDC PWM ch 0 |
| L298N `IN1` | 25 | |
| L298N `IN2` | 26 | |
| L298N `ENB` | 33 | LEDC PWM ch 1 |
| L298N `IN3` | 27 | |
| L298N `IN4` | 14 | **not 12** |

---

## 3. Voltage dividers

### 3.1 HC-SR04 ECHO → GPIO18

```
HC-SR04 ECHO ────┬──── R1 (1 kΩ) ────┬──── GPIO18
                 │                   │
                 │                 R2 (2 kΩ)
                 │                   │
                GND ─────────────────┴──── GND

Vout = 5.0 × 2000 / (1000 + 2000) = 3.33 V   ✓
```

### 3.2 MQ-2 AOUT → GPIO34

```
MQ-2 AOUT ───┬──── R1 (10 kΩ) ────┬──── GPIO34
             │                    │
             │                  R2 (20 kΩ)
             │                    │
            GND ──────────────────┴──── GND

Vout = 5.0 × 20 / (10 + 20) = 3.33 V   ✓
```

### 3.3 Battery → GPIO35

```
PACK + ───┬──── R1 (100 kΩ) ────┬──── GPIO35
          │                     │
          │                   R2 (22 kΩ)
          │                     │
        PACK − ─────────────────┴──── GND (common)

BATTERY_DIVIDER = (100 + 22) / 22 = 5.545
```
Check at **full charge**: an 8.4 V (2S) pack gives 1.51 V at the ADC. Safe. A 12.6 V (3S) pack gives 2.27 V. Also safe.

Use ≥ 100 kΩ total so the divider does not slowly drain the pack.

---

## 4. Power

**This is where most robot projects fail.**

```
                  ┌─────────────────────────────┐
   BATTERY ───────┤ L298N  +12V                 │
   (2S/3S LiPo)   │        GND ────┐            ├──► M1 M2 (left)
                  │        +5V  ✗  │            ├──► M3 M4 (right)
                  └────────────────┼────────────┘
        │                          │
        │                          │
        └──► BUCK CONVERTER        │
             (5 V, ≥ 3 A)          │
                 │                 │
                 ├──► MQ-2 VCC     │   (heater ≈ 150 mA)
                 ├──► HC-SR04 VCC  │
                 ├──► IR VCC       │
                 └──► ESP32 VIN    │
                       │           │
                      GND ─────────┴──── COMMON GROUND
```

**Rules:**

1. **Never** power sensors from the L298N's onboard `+5V` pin. Its regulator is rated ~500 mA and will sag when the motors draw current, browning out the ESP32.
2. **Never** power motors from the ESP32's 3.3 V rail.
3. **Common ground everywhere.** Battery −, L298N GND, ESP32 GND, and every sensor GND must be the same node. Without it, the ECHO/analog readings are noise.
4. Remove the L298N's `+5V-EN` jumper if your supply is above 12 V.

### 4.1 Do not use 9 V block batteries

A 9 V alkaline delivers roughly **500 mAh** and only **50–100 mA** before its internal resistance (several ohms) collapses the terminal voltage. Four gear motors need **0.8–2 A**. Two in series gives 18 V and the same useless current — the pack will sag to near zero the instant the motors start, the ESP32 will brown out and reboot, and you will spend days debugging "random resets" that are a power problem.

They also run flat in about 15 minutes.

| Option | Voltage | Verdict |
|---|---|---|
| 2S LiPo, 1500–2200 mAh, 20C+ | 7.4 V | **Recommended** |
| 3× 18650 + BMS | 11.1 V | Cheapest reliable |
| 6× AA NiMH | 7.2 V | Works, mediocre |
| 12 V 7 Ah SLA | 12 V | Heavy; fine for a bench demo |
| 9 V block | 9 V | **Will not work** |

### 4.2 Motor voltage — do the arithmetic

The L298N drops roughly **2 V** internally.

```
motor_volts = (pack_volts − 2.0) × (MOTOR_PWM_MAX / 255)
```

Most yellow TT and N20 gear motors are rated **3–6 V**. On an 18 V pack they see ~16 V and burn.

| Pack | Motor rating | `MOTOR_PWM_MAX` |
|---|---|---|
| 7.4 V (2S) | 6 V | `255` |
| 11.1 V (3S) | 6 V | `168` |
| 12 V SLA | 12 V | `255` |

`MOTOR_PWM_MAX` ships as **`0`**, and `motors.cpp` **refuses to drive** while it is zero. Measure your pack, read your motor's rating, compute the number, then set it. This is deliberate: any value I could guess for you can destroy your motors.

---

## 5. Camera

A **USB webcam plugs into the Raspberry Pi**, not the ESP32. There is no ESP32-CAM in this build.

Consequences:
- OpenCV reads frames locally with `cv2.VideoCapture(0)`. No MJPEG-over-WiFi hop, no second board to debug.
- YOLO runs on frames already in RAM.
- **The camera does not move with the rover** unless the Pi rides on it.

Check the device:
```bash
ls /dev/video*
v4l2-ctl --list-devices
```

---

## 6. Bring-up order

Never wire everything and hope. Each step must pass before the next.

| Step | Wire | Test |
|---|---|---|
| 1 | ESP32 + USB only | Serial banner prints at 115200 |
| 2 | + DHT22 | `temp_c` is a plausible number, not `NO DATA` |
| 3 | + HC-SR04 **with divider** | distance tracks your hand |
| 4 | + IR sensors | flags flip when you block them |
| 5 | + MQ-2 **with divider** | `mq2_raw` moves near a lighter (unlit) |
| 6 | + WiFi/MQTT | `mosquitto_sub` shows JSON |
| 7 | + L298N, **wheels off the ground** | each direction, correct rotation |
| 8 | Set `MOTOR_PWM_MAX`, wheels down | drives; obstacle stops it |
| 9 | + battery divider | `battery_v` matches a multimeter ±0.1 V |

**Step 7 is not optional.** With the chassis on a stand, a reversed motor lead is a two-second fix. On the floor, it drives into a wall.

---

## 7. Verifying the honesty rule

The system is built so a broken sensor **looks broken**. Confirm it:

1. Start everything; dashboard shows live values.
2. **Unplug the DHT22.** Within 2 s, Temperature and Humidity turn grey and read `NO DATA`. Everything else keeps working.
3. **Unplug the ESP32.** Within 5 s a yellow `NO TELEMETRY` banner appears. Within ~22 s the broker fires the Last Will and the banner turns red: `ROVER OFFLINE`.
4. Plug it back in. Everything recovers on its own.

If any step instead shows a plausible-looking number, something is broken — and that is the most dangerous kind of bug this system can have.
