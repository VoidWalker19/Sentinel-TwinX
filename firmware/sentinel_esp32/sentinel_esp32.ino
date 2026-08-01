/*
 * ==========================================================================
 *  SENTINEL TWIN X  -  ESP32 Firmware (Modular Refactored Phase 2A Rebuild)
 *  Orchestrator for config, logging, sensors, motors, communication,
 *  non-blocking alert indicators, and diagnostics.
 *
 *  Board:  ESP32 Dev Module
 *  IDE:    Arduino IDE / PlatformIO
 *  Version: 2.0.0
 * ==========================================================================
 */

#include "config.h"
#include "logging.h"
#include "sensors.h"
#include "motors.h"
#include "indicators.h"
#include "communication.h"
#include "commands.h"
#include "diagnostics.h"

// ---------------------------------------------------------------------------
// NAVIGATION STATE MACHINE VARIABLES
// ---------------------------------------------------------------------------
enum RoverState {
  ROVER_FORWARD,
  ROVER_STOPPING_BEFORE_BACK,
  ROVER_BACKWARD,
  ROVER_TURNING,
  ROVER_STOPPING_AFTER_TURN
};

RoverState roverState = ROVER_FORWARD;
unsigned long navTimer = 0;
unsigned long navDuration = 0;

// ---------------------------------------------------------------------------
// MOTOR MOVEMENT HELPER FUNCTIONS
// ---------------------------------------------------------------------------
void moveForward() {
  int speed = configSystem.getConfig().motorSpeed;
  motorController.setDirectionAndSpeed(true, true, speed, speed);
}

void moveBackward() {
  int speed = configSystem.getConfig().motorSpeed;
  motorController.setDirectionAndSpeed(false, false, speed, speed);
}

void turnRight() {
  int speed = configSystem.getConfig().motorSpeed;
  motorController.setDirectionAndSpeed(true, false, speed, speed);
}

void stopMotors() {
  motorController.setDirectionAndSpeed(true, true, 0, 0);
}

void updateRoverNavigation(bool obstacle) {
  unsigned long now = millis();

  switch (roverState) {
    case ROVER_FORWARD:
      if (obstacle) {
        stopMotors();
        roverState = ROVER_STOPPING_BEFORE_BACK;
        navTimer = now;
        navDuration = 200;
      } else {
        moveForward();
      }
      break;

    case ROVER_STOPPING_BEFORE_BACK:
      stopMotors();
      if (now - navTimer >= navDuration) {
        moveBackward();
        roverState = ROVER_BACKWARD;
        navTimer = now;
        navDuration = 400;
      }
      break;

    case ROVER_BACKWARD:
      moveBackward();
      if (now - navTimer >= navDuration) {
        turnRight();
        roverState = ROVER_TURNING;
        navTimer = now;
        navDuration = 400;
      }
      break;

    case ROVER_TURNING:
      turnRight();
      if (now - navTimer >= navDuration) {
        stopMotors();
        roverState = ROVER_STOPPING_AFTER_TURN;
        navTimer = now;
        navDuration = 200;
      }
      break;

    case ROVER_STOPPING_AFTER_TURN:
      stopMotors();
      if (now - navTimer >= navDuration) {
        roverState = ROVER_FORWARD;
      }
      break;
  }
}

// ---------------------------------------------------------------------------
// SETUP
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);

  LOG_INFO("Booting Sentinel Twin X Firmware (v2.0.0)...");
  
  // 1. Initialize core configurations
  configSystem.init();
  configSystem.printConfig();

  // 2. Initialize hardware modules
  sensorManager.init();
  motorController.init();
  indicatorManager.init();

  // Additional pin configurations for IR obstacle sensors
  pinMode(IR_LEFT_PIN, INPUT);
  pinMode(IR_RIGHT_PIN, INPUT);

  // 3. Warm up gas sensors (indicating startup status)
  LOG_INFO("Warming up gas sensors...");
  for (int i = 0; i < 20; i++) {
    digitalWrite(LED_PIN, i % 2);
    delay(100); // 2 seconds total warmup blinking
  }
  digitalWrite(LED_PIN, LOW);
  LOG_INFO("Warmup complete.");

  // 4. Initialize communications & diagnostics loops
  initCommunication();
  initDiagnostics();

  LOG_INFO("Initialization complete. Rover loops dispatched successfully.");
}

// ---------------------------------------------------------------------------
// MAIN EXECUTION LOOP
// ---------------------------------------------------------------------------
void loop() {
  // 1. Update background hardware modules
  sensorManager.update();
  motorController.update();
  indicatorManager.update();

  // 2. Update network linkages and reconnect state machine
  updateCommunication();

  // 3. Evaluate navigation constraints (non-blocking)
  long distance = readDistanceCM();
  bool irLeft   = (digitalRead(IR_LEFT_PIN) == LOW);
  bool irRight  = (digitalRead(IR_RIGHT_PIN) == LOW);
  bool obstacle = (distance > 0 && distance < OBSTACLE_CM) || irLeft || irRight;

  updateRoverNavigation(obstacle);

  // 4. Update telemetry and heartbeat reports
  updateDiagnostics();

  // 5. Handle incoming Serial CLI commands
  handleSerialCommands();
}
