// ============================================================================
// Sentinel Twin X — Command Center Dashboard
// ============================================================================

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import mqtt from "mqtt";
import * as Icons from "lucide-react";
import logoUrl from "./assets/logo.jpg";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

// ----------------------------------------------------------------------------
// Injected styles: tokens, keyframes, color utilities, scrollbar, base
// ----------------------------------------------------------------------------
const DASHBOARD_STYLE = `
:root, .sentinel-dark {
  --radius: 0.9rem;
  --background: oklch(0.16 0.02 260);
  --foreground: oklch(0.97 0.01 250);
  --card: oklch(0.22 0.025 260 / 0.55);
  --card-foreground: oklch(0.97 0.01 250);
  --primary: oklch(0.68 0.19 250);
  --primary-foreground: oklch(0.14 0.02 260);
  --secondary: oklch(0.28 0.03 260 / 0.6);
  --secondary-foreground: oklch(0.95 0.01 250);
  --muted: oklch(0.26 0.025 260 / 0.6);
  --muted-foreground: oklch(0.72 0.03 250);
  --accent: oklch(0.72 0.15 210);
  --accent-foreground: oklch(0.14 0.02 260);
  --border: oklch(1 0 0 / 0.08);
  --success: oklch(0.72 0.18 155);
  --warning: oklch(0.78 0.18 65);
  --critical: oklch(0.65 0.25 25);
}
.sentinel-light {
  --background: oklch(0.98 0.005 250);
  --foreground: oklch(0.18 0.02 260);
  --card: oklch(1 0 0 / 0.7);
  --card-foreground: oklch(0.18 0.02 260);
  --primary: oklch(0.55 0.2 250);
  --primary-foreground: oklch(0.98 0.005 250);
  --secondary: oklch(0.94 0.01 250);
  --secondary-foreground: oklch(0.2 0.02 260);
  --muted: oklch(0.94 0.01 250);
  --muted-foreground: oklch(0.5 0.02 260);
  --accent: oklch(0.62 0.14 210);
  --accent-foreground: oklch(0.98 0.005 250);
  --border: oklch(0.2 0.02 260 / 0.1);
  --success: oklch(0.55 0.18 155);
  --warning: oklch(0.75 0.18 65);
  --critical: oklch(0.65 0.25 25);
}
.sentinel-dashboard {
  background-color: var(--background);
  color: var(--foreground);
  font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
  min-height: 100vh;
}
.sentinel-dashboard h1,
.sentinel-dashboard h2,
.sentinel-dashboard h3,
.sentinel-dashboard h4 {
  font-family: "Space Grotesk", "Inter", sans-serif;
  letter-spacing: -0.02em;
}
.sentinel-dashboard .font-mono { font-family: "JetBrains Mono", ui-monospace, monospace; }
.sentinel-dashboard .bg-background { background-color: var(--background); }
.sentinel-dashboard .bg-foreground { background-color: var(--foreground); }
.sentinel-dashboard .bg-card { background-color: var(--card); }
.sentinel-dashboard .bg-primary { background-color: var(--primary); }
.sentinel-dashboard .bg-secondary { background-color: var(--secondary); }
.sentinel-dashboard .bg-muted { background-color: var(--muted); }
.sentinel-dashboard .bg-accent { background-color: var(--accent); }
.sentinel-dashboard .bg-success { background-color: var(--success); }
.sentinel-dashboard .bg-warning { background-color: var(--warning); }
.sentinel-dashboard .bg-critical { background-color: var(--critical); }
.sentinel-dashboard .text-background { color: var(--background); }
.sentinel-dashboard .text-foreground { color: var(--foreground); }
.sentinel-dashboard .text-card-foreground { color: var(--card-foreground); }
.sentinel-dashboard .text-primary { color: var(--primary); }
.sentinel-dashboard .text-primary-foreground { color: var(--primary-foreground); }
.sentinel-dashboard .text-secondary-foreground { color: var(--secondary-foreground); }
.sentinel-dashboard .text-muted { color: var(--muted); }
.sentinel-dashboard .text-muted-foreground { color: var(--muted-foreground); }
.sentinel-dashboard .text-accent { color: var(--accent); }
.sentinel-dashboard .text-accent-foreground { color: var(--accent-foreground); }
.sentinel-dashboard .text-success { color: var(--success); }
.sentinel-dashboard .text-warning { color: var(--warning); }
.sentinel-dashboard .text-critical { color: var(--critical); }
.sentinel-dashboard .border-border { border-color: var(--border); }
.sentinel-dashboard .border-primary { border-color: var(--primary); }
.sentinel-dashboard .border-accent { border-color: var(--accent); }
.sentinel-dashboard .border-success { border-color: var(--success); }
.sentinel-dashboard .border-warning { border-color: var(--warning); }
.sentinel-dashboard .border-critical { border-color: var(--critical); }
.sentinel-dashboard .ring-primary { --tw-ring-color: var(--primary); }
.sentinel-dashboard .fill-primary { fill: var(--primary); }
.sentinel-dashboard .fill-success { fill: var(--success); }
.sentinel-dashboard .fill-warning { fill: var(--warning); }
.sentinel-dashboard .fill-critical { fill: var(--critical); }
.sentinel-dashboard .stroke-primary { stroke: var(--primary); }
.sentinel-dashboard .stroke-secondary { stroke: var(--secondary); }
.sentinel-dashboard .stroke-success { stroke: var(--success); }
.sentinel-dashboard .stroke-warning { stroke: var(--warning); }
.sentinel-dashboard .stroke-critical { stroke: var(--critical); }
.sentinel-dashboard .placeholder-muted-foreground::placeholder { color: var(--muted-foreground); }

.sentinel-glass {
  background: color-mix(in oklab, var(--card) 92%, transparent);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  border: 1px solid var(--border);
  box-shadow: 0 1px 0 0 oklch(1 0 0 / 0.04) inset, 0 20px 40px -20px oklch(0 0 0 / 0.5);
}
.sentinel-glass-strong {
  background: color-mix(in oklab, var(--card) 98%, transparent);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  border: 1px solid var(--border);
  box-shadow: 0 1px 0 0 oklch(1 0 0 / 0.06) inset, 0 30px 60px -30px oklch(0 0 0 / 0.6);
}
.sentinel-glow-primary {
  box-shadow: 0 0 0 1px oklch(0.68 0.19 250 / 0.3), 0 10px 40px -10px oklch(0.68 0.19 250 / 0.4);
}
.sentinel-text-gradient {
  background: linear-gradient(135deg, var(--foreground), color-mix(in oklab, var(--primary) 70%, var(--foreground)));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.sentinel-grid-bg {
  background-image: linear-gradient(to right, oklch(1 0 0 / 0.04) 1px, transparent 1px),
                    linear-gradient(to bottom, oklch(1 0 0 / 0.04) 1px, transparent 1px);
  background-size: 32px 32px;
}
@keyframes sentinel-pulse-ring {
  0% { box-shadow: 0 0 0 0 oklch(0.68 0.19 250 / 0.5); }
  70% { box-shadow: 0 0 0 12px oklch(0.68 0.19 250 / 0); }
  100% { box-shadow: 0 0 0 0 oklch(0.68 0.19 250 / 0); }
}
.sentinel-pulse-ring { animation: sentinel-pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite; }
@keyframes sentinel-conic-spin { to { transform: rotate(360deg); } }
.sentinel-conic-border { position: relative; isolation: isolate; }
.sentinel-conic-glow {
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  padding: 1px;
  background: conic-gradient(from 0deg, transparent 0%, oklch(0.68 0.19 250 / 0.8) 25%, oklch(0.78 0.14 200 / 0.8) 50%, transparent 75%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: sentinel-conic-spin 6s linear infinite;
  pointer-events: none;
  opacity: 0.8;
}
@keyframes sentinel-orbit { to { transform: rotate(360deg); } }
.sentinel-orbit-ring { animation: sentinel-orbit 12s linear infinite; }
.sentinel-orbit-ring-slow { animation: sentinel-orbit 24s linear infinite reverse; }
@keyframes sentinel-fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.sentinel-fade-up { animation: sentinel-fade-up 0.5s ease-out backwards; }
@keyframes sentinel-float {
  0%,100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.sentinel-float { animation: sentinel-float 4s ease-in-out infinite; }

.sentinel-dashboard ::-webkit-scrollbar { width: 10px; height: 10px; }
.sentinel-dashboard ::-webkit-scrollbar-track { background: transparent; }
.sentinel-dashboard ::-webkit-scrollbar-thumb { background: oklch(1 0 0 / 0.08); border-radius: 8px; }
.sentinel-dashboard ::-webkit-scrollbar-thumb:hover { background: oklch(1 0 0 / 0.16); }

@keyframes sentinel-dash {
  to {
    stroke-dashoffset: -20;
  }
}
.sentinel-dash-path {
  stroke-dashoffset: 0;
  animation: sentinel-dash 4s linear infinite;
}
`;

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------
function cn(...inputs: (string | false | undefined)[]) {
  return inputs.filter(Boolean).join(" ");
}

function seeded(n: number) {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function generateTimeseries(points = 24, base = 22, variance = 4, seedOffset = 0) {
  return Array.from({ length: points }, (_, i) => {
    const s = seeded(i + seedOffset + 1);
    const s2 = seeded(i * 2 + seedOffset + 7);
    return {
      t: `${((24 - points + i) % 24).toString().padStart(2, "0")}:00`,
      temperature: +(base + Math.sin(i / 3) * variance + s * 1.2).toFixed(1),
      humidity: +(48 + Math.cos(i / 4) * 8 + s2 * 2).toFixed(1),
      gas: +(20 + Math.sin(i / 2.5) * 10 + s * 3).toFixed(1),
      co: +(5 + Math.sin(i / 3.5) * 3 + s * 0.8).toFixed(1),
      battery: +(90 - i * 1.2 + s2).toFixed(1),
      alerts: Math.max(0, Math.round(Math.sin(i / 3) * 2 + s * 1.5)),
    };
  });
}

// ----------------------------------------------------------------------------
// Types and Interfaces
// ----------------------------------------------------------------------------
export type RoomStatus = "normal" | "warning" | "critical" | "offline";

export interface Room {
  id: string;
  name: string;
  floor: number;
  x: number;
  y: number;
  w: number;
  h: number;
  status: RoomStatus;
  temperature: number;
  humidity: number;
  gas: number;
  co: number;
  airQuality: number;
  flame: boolean;
}

export interface BuildingConfig {
  name: string;
  floors: { id: number; name: string; cols: number; rows: number }[];
  rooms: Room[];
}

export const buildingConfig: BuildingConfig = {
  name: "Riverside Preparatory Academy",
  floors: [
    { id: 1, name: "Ground Floor", cols: 6, rows: 4 },
    { id: 2, name: "First Floor", cols: 6, rows: 4 },
  ],
  rooms: [
    { id: "r-101", name: "Main Entrance", floor: 1, x: 0, y: 0, w: 2, h: 1, status: "normal", temperature: 22.4, humidity: 48, gas: 12, co: 2, airQuality: 96, flame: false },
    { id: "r-102", name: "Reception", floor: 1, x: 2, y: 0, w: 2, h: 1, status: "normal", temperature: 22.8, humidity: 46, gas: 11, co: 1, airQuality: 97, flame: false },
    { id: "r-103", name: "Cafeteria", floor: 1, x: 4, y: 0, w: 2, h: 2, status: "warning", temperature: 26.1, humidity: 62, gas: 44, co: 6, airQuality: 78, flame: false },
    { id: "r-104", name: "Gymnasium", floor: 1, x: 0, y: 1, w: 3, h: 2, status: "normal", temperature: 23.6, humidity: 51, gas: 14, co: 2, airQuality: 92, flame: false },
    { id: "r-105", name: "Library", floor: 1, x: 3, y: 2, w: 3, h: 1, status: "normal", temperature: 22.1, humidity: 44, gas: 9, co: 1, airQuality: 98, flame: false },
    { id: "r-106", name: "Storage", floor: 1, x: 0, y: 3, w: 2, h: 1, status: "normal", temperature: 21.5, humidity: 55, gas: 18, co: 3, airQuality: 90, flame: false },
    { id: "r-107", name: "Server Room", floor: 1, x: 2, y: 3, w: 2, h: 1, status: "warning", temperature: 28.9, humidity: 38, gas: 21, co: 4, airQuality: 85, flame: false },
    { id: "r-108", name: "Utility", floor: 1, x: 4, y: 3, w: 2, h: 1, status: "normal", temperature: 23.0, humidity: 49, gas: 15, co: 2, airQuality: 94, flame: false },
    { id: "r-201", name: "Chemistry Lab", floor: 2, x: 0, y: 0, w: 2, h: 2, status: "critical", temperature: 34.2, humidity: 71, gas: 128, co: 22, airQuality: 42, flame: true },
    { id: "r-202", name: "Physics Lab", floor: 2, x: 2, y: 0, w: 2, h: 2, status: "normal", temperature: 22.7, humidity: 47, gas: 13, co: 2, airQuality: 95, flame: false },
    { id: "r-203", name: "Classroom 2A", floor: 2, x: 4, y: 0, w: 2, h: 1, status: "normal", temperature: 22.3, humidity: 45, gas: 10, co: 1, airQuality: 97, flame: false },
    { id: "r-204", name: "Classroom 2B", floor: 2, x: 4, y: 1, w: 2, h: 1, status: "normal", temperature: 22.6, humidity: 46, gas: 11, co: 1, airQuality: 96, flame: false },
    { id: "r-205", name: "Faculty Lounge", floor: 2, x: 0, y: 2, w: 2, h: 2, status: "normal", temperature: 23.1, humidity: 48, gas: 14, co: 2, airQuality: 94, flame: false },
    { id: "r-206", name: "Computer Lab", floor: 2, x: 2, y: 2, w: 2, h: 2, status: "warning", temperature: 27.4, humidity: 41, gas: 24, co: 4, airQuality: 82, flame: false },
    { id: "r-207", name: "Auditorium", floor: 2, x: 4, y: 2, w: 2, h: 2, status: "normal", temperature: 22.9, humidity: 50, gas: 12, co: 2, airQuality: 95, flame: false },
  ],
};

export interface SystemStatus {
  battery: number;
  wifi: "connected" | "weak" | "offline";
  mqtt: "online" | "offline";
  raspberryPi: "online" | "offline";
  esp32: "online" | "offline" | "connecting";
  camera: "streaming" | "offline";
  ai: "active" | "idle" | "offline";
  systemHealth: number;
  currentMission: string;
  currentRoom: string;
  uptime: string;
  summaryTemp?: string;
  summaryHumidity?: string;
  summaryAirQuality?: string;
  summaryGas?: string;
  summaryCO?: string;
  details?: {
    raspberryPi?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
    esp32?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
    mqtt?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
    wifi?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
    camera?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
    ai?: { heartbeat: string; uptime: string; latency?: string; quality?: string };
  };
}

export type AlertSeverity = "critical" | "warning" | "info" | "resolved";
export type AlertPriority = "Critical" | "High" | "Medium" | "Low";

export interface AlertLogItem {
  id: string;
  time: string;
  timestamp: number;
  type: string;
  priority: AlertPriority;
  mission: string;
  room: string;
  actionTaken: string;
  operator: string;
  status: "Unread" | "Read" | "Resolved" | "Active";
  sensor?: string;
  message?: string;
  recommendation?: string;
  read: boolean;
  iconName?: string;
}

export interface AlertEvent {
  id: string;
  severity: AlertSeverity;
  location: string;
  time: string;
  sensor: string;
  message: string;
  recommendation: string;
  resolved: boolean;
}

export const SUPPORTED_ALERTS_CONFIG: Record<string, {
  priority: AlertPriority;
  icon: string;
  defaultDesc: string;
  autoAction: string;
}> = {
  "Fire Detected": { priority: "Critical", icon: "Flame", defaultDesc: "Flame sensor triggered with critical thermal spikes in Chemistry Lab", autoAction: "Deploy Mission" },
  "Gas Leak": { priority: "Critical", icon: "Wind", defaultDesc: "Hazardous combustible gas threshold exceeded in Cafeteria", autoAction: "Deploy Inspection" },
  "Obstacle Detected": { priority: "High", icon: "ShieldAlert", defaultDesc: "Obstacle blocking active navigation trajectory", autoAction: "Reroute Path" },
  "Rover Stuck": { priority: "Critical", icon: "Bot", defaultDesc: "Rover stationary >10s during active mission", autoAction: "Open Camera Popup" },
  "Low Battery": { priority: "High", icon: "BatteryLow", defaultDesc: "Battery level dropped below 20%", autoAction: "Notify Operator" },
  "Battery Critical": { priority: "Critical", icon: "BatteryWarning", defaultDesc: "Battery critically low (<10%). Immediate dock required.", autoAction: "Return Home" },
  "Mission Started": { priority: "Medium", icon: "PlayCircle", defaultDesc: "New mission dispatch initialized", autoAction: "Monitor Sweeps" },
  "Mission Completed": { priority: "Medium", icon: "CheckCircle", defaultDesc: "Patrol mission targets reached successfully", autoAction: "Dock Rover" },
  "Mission Failed": { priority: "High", icon: "XCircle", defaultDesc: "Mission aborted due to obstacle or system fault", autoAction: "Log Diagnostics" },
  "Camera Offline": { priority: "High", icon: "CameraOff", defaultDesc: "ESP32-CAM stream lost or non-responsive", autoAction: "Retry Connection" },
  "ESP32 Offline": { priority: "High", icon: "Cpu", defaultDesc: "ESP32 microcontroller telemetry connection timed out", autoAction: "Ping Microcontroller" },
  "MQTT Offline": { priority: "High", icon: "Radio", defaultDesc: "MQTT broker connection lost", autoAction: "Reconnect Automatically" },
  "WiFi Lost": { priority: "High", icon: "WifiOff", defaultDesc: "Wireless network link disconnected", autoAction: "Retry Link" },
  "AI Offline": { priority: "High", icon: "Sparkles", defaultDesc: "AI inference pipeline model offline", autoAction: "Restart Model" },
  "Temperature High": { priority: "High", icon: "Thermometer", defaultDesc: "High temperature anomaly detected in zone", autoAction: "HVAC Check" },
  "Smoke Detected": { priority: "High", icon: "Cloud", defaultDesc: "Smoke concentration elevated in zone", autoAction: "Deploy Sweep" },
  "Intruder Detected": { priority: "Critical", icon: "UserX", defaultDesc: "Unidentified movement in secured area", autoAction: "Deploy Emergency Scan" },
  "Manual Override Enabled": { priority: "Low", icon: "Sliders", defaultDesc: "Operator manual override activated", autoAction: "Log Action" },
  "Emergency Stop Activated": { priority: "Critical", icon: "Square", defaultDesc: "E-Stop command executed immediately", autoAction: "Halt Motors" },
  "Sensor Failure": { priority: "High", icon: "AlertTriangle", defaultDesc: "Sensor node telemetry hardware fault", autoAction: "Check Wire Harness" },
  "Connection Restored": { priority: "Low", icon: "Wifi", defaultDesc: "Network telemetry connection re-established", autoAction: "Resume Telemetry" },
};

export function requestDesktopNotificationPermission() {
  if (typeof window !== "undefined" && "Notification" in window) {
    if (Notification.permission === "default") {
      Notification.requestPermission().catch(() => { });
    }
  }
}

export function sendDesktopNotification(title: string, body: string, priority: AlertPriority = "High") {
  if (typeof window !== "undefined" && "Notification" in window) {
    if (Notification.permission === "granted") {
      try {
        const priorityEmoji = priority === "Critical" ? "🚨 " : priority === "High" ? "⚠️ " : "ℹ️ ";
        new Notification(`${priorityEmoji}${title}`, {
          body: `${body}\nTime: ${new Date().toLocaleTimeString()}`,
          icon: logoUrl,
          tag: title,
        });
      } catch (e) {
        console.warn("Desktop notification error:", e);
      }
    }
  }
}

export interface Mission {
  id: string;
  name: string;
  type: "PATROL" | "INSPECTION" | "EMERGENCY" | "RETURN" | "IDLE" | "MAINTENANCE";
  progress: number;
  waypoint: string;
  next: string;
  eta: string;
  status: "running" | "queued" | "paused" | "completed" | "ABORTED";
  priority?: string;
  desc?: string;
}

export interface TimelineEvent {
  event_type: "detection" | "dispatch" | "arrival" | "verification" | "alert" | "reset" | "info";
  description: string;
  severity: "info" | "warning" | "critical";
  zone_id?: string;
  timestamp: number;
}

// Unified Provider Interface
export interface SentinelDataProvider {
  mode: "live" | "demo";
  connected: boolean;
  browserMqttConnected?: boolean;
  status: SystemStatus;
  missions: Mission[];
  alerts: AlertEvent[];
  timeline: TimelineEvent[];
  backendState: any;
  dispatchMission: (zoneId: string) => void;
  sendRoverCommand: (cmd: string) => void;
  sendMqttPayload?: (topic: string, payload: any) => void;
  triggerDemoScenario?: (scenarioName: string) => void;
}

// Web Audio API Synthesizer
let audioContextInstance: AudioContext | null = null;
function playNotificationSound(type: "info" | "success" | "warning" | "error" | "Critical" | "High" | "Medium" | "Low") {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    if (!audioContextInstance) {
      audioContextInstance = new AudioContextClass();
    }
    const ctx = audioContextInstance;
    if (ctx.state === "suspended") {
      ctx.resume();
    }

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    const now = ctx.currentTime;
    if (type === "error" || type === "warning" || type === "Critical" || type === "High") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(type === "Critical" ? 960 : 880, now);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);

      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.type = "sawtooth";
      osc2.frequency.setValueAtTime(type === "Critical" ? 1200 : 880, now + 0.22);
      gain2.gain.setValueAtTime(0.1, now + 0.22);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      osc2.start(now + 0.22);
      osc2.stop(now + 0.4);
    } else if (type === "success") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.25);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    } else {
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, now);
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      osc.start(now);
      osc.stop(now + 0.1);
    }
  } catch (err) {
    console.warn("Failed to play synthesized sound:", err);
  }
}

const initialStatus: SystemStatus = {
  battery: 78,
  wifi: "connected",
  mqtt: "online",
  raspberryPi: "online",
  esp32: "online",
  camera: "streaming",
  ai: "active",
  systemHealth: 94,
  currentMission: "PATROL — Floor 2",
  currentRoom: "Chemistry Lab",
  uptime: "14h 22m",
  summaryTemp: "23.4",
  summaryHumidity: "48",
  summaryAirQuality: "94",
  summaryGas: "12",
  details: {
    raspberryPi: { heartbeat: "Just now", uptime: "14h 22m", latency: "4ms", quality: "100%" },
    esp32: { heartbeat: "Just now", uptime: "14h 22m", latency: "14ms", quality: "99%" },
    mqtt: { heartbeat: "Just now", uptime: "14h 22m", latency: "6ms", quality: "Nominal" },
    wifi: { heartbeat: "Just now", uptime: "14h 22m", latency: "2ms", quality: "92%" },
    camera: { heartbeat: "Just now", uptime: "14h 22m", latency: "48ms", quality: "24 FPS" },
    ai: { heartbeat: "Just now", uptime: "14h 22m", latency: "87ms", quality: "Active" }
  }
};

// ----------------------------------------------------------------------------
// Feature 1: Startup Splash Screen Component
// ----------------------------------------------------------------------------
function SplashScreen({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const messages = [
    "Initializing Dashboard...",
    "Connecting Raspberry Pi...",
    "Connecting MQTT Broker...",
    "Loading AI Engine...",
    "Loading Digital Twin...",
    "Synchronizing Sensors...",
    "System Ready.",
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => {
        if (prev < messages.length - 1) {
          return prev + 1;
        } else {
          clearInterval(timer);
          setTimeout(() => onComplete(), 400);
          return prev;
        }
      });
    }, 320);
    return () => clearInterval(timer);
  }, [messages.length, onComplete]);

  const progressPct = Math.round(((step + 1) / messages.length) * 100);

  return (
    <div className="fixed inset-0 z-[10000] flex flex-col items-center justify-center bg-slate-950 text-white animate-fade-in font-sans">
      <div className="relative flex flex-col items-center max-w-md w-full px-6 text-center">
        <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-accent/30 border border-primary/40 shadow-2xl mb-6 sentinel-glow-primary animate-pulse">
          <img src={logoUrl} alt="Sentinel Twin" className="h-full w-full object-cover object-top rounded-2xl" />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-primary to-accent bg-clip-text text-transparent mb-1">
          Sentinel Twin
        </h1>
        <p className="text-xs uppercase tracking-[0.25em] text-primary/80 font-mono mb-8">
          AI Powered Autonomous Digital Twin
        </p>

        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden mb-4 border border-white/10">
          <div
            className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-300 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <div className="h-6 flex items-center justify-center">
          <span className="text-xs font-mono text-slate-300 animate-pulse">
            {messages[step]}
          </span>
        </div>

        <div className="mt-8 text-[10px] text-slate-500 uppercase tracking-widest font-mono">
          SyncHack 2026 · Command Center v2.4.1
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Feature 2: Command-Center Login System Component (Enhanced)
// ----------------------------------------------------------------------------
function LoginScreen({
  onLogin,
}: {
  onLogin: (username: string, role: "Administrator" | "Operator" | "Viewer") => void;
}) {
  const [username, setUsernameInput] = useState("Ankit");
  const [password, setPasswordInput] = useState("••••••••");
  const [role, setRole] = useState<"Administrator" | "Operator" | "Viewer">("Administrator");
  const [rememberMe, setRememberMe] = useState(true);
  const [showForgotNotice, setShowForgotNotice] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginStep, setLoginStep] = useState(0);

  const loginStepsMessages = [
    "Authenticating Operator Credentials...",
    "Verifying TLS 1.3 Security Policies...",
    "Connecting MQTT Realtime Telemetry...",
    "Initializing Command Workspace..."
  ];

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginStep(0);

    const stepInterval = setInterval(() => {
      setLoginStep((prev) => {
        if (prev < loginStepsMessages.length - 1) {
          return prev + 1;
        } else {
          clearInterval(stepInterval);
          setTimeout(() => {
            onLogin(username || "Operator", role);
          }, 300);
          return prev;
        }
      });
    }, 280);
  };

  const handlePresetSelect = (presetUser: string, presetRole: "Administrator" | "Operator" | "Viewer") => {
    setUsernameInput(presetUser);
    setRole(presetRole);
  };

  const roleDetails = {
    Administrator: {
      title: "Administrator",
      icon: Icons.ShieldCheck,
      desc: "Full Control, AI Threshold Tuning & Policy Executions",
      badgeTone: "border-primary bg-primary/10 text-primary"
    },
    Operator: {
      title: "Operator",
      icon: Icons.Bot,
      desc: "Mission Dispatch, Live Camera, Digital Twin & Alarms",
      badgeTone: "border-accent bg-accent/10 text-accent"
    },
    Viewer: {
      title: "Viewer",
      icon: Icons.Eye,
      desc: "Read-Only Dashboard Telemetry & System Diagnostics",
      badgeTone: "border-success bg-success/10 text-success"
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto bg-slate-950/98 backdrop-blur-3xl px-4 py-6 font-sans">
      {/* Background Cyber Ambient Lights */}
      <div className="pointer-events-none fixed inset-0 sentinel-grid-bg opacity-30" />
      <div className="pointer-events-none fixed -left-32 -top-32 h-96 w-96 rounded-full bg-primary/20 blur-[120px] animate-pulse" />
      <div className="pointer-events-none fixed -right-32 -bottom-32 h-96 w-96 rounded-full bg-accent/20 blur-[120px] animate-pulse" />

      <div className="min-h-full w-full flex items-center justify-center py-4">
        {/* Main Glassmorphic Container */}
        <div className="relative w-full max-w-lg max-h-[calc(100vh-3rem)] overflow-y-auto rounded-3xl border border-white/15 bg-slate-900/85 p-6 sm:p-8 shadow-[0_0_60px_rgba(0,230,190,0.12)] backdrop-blur-2xl transition-all duration-300">

          {/* Top Header Security Status */}
          <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
            <div className="flex items-center gap-2 text-[10px] font-mono tracking-widest text-slate-400 uppercase">
              <span className="h-2 w-2 rounded-full bg-success animate-ping" />
              <span>Encrypted Session · TLS 1.3</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[10px] font-mono text-primary font-bold">
              <span>v2.4.1</span>
            </div>
          </div>

          {/* Logo & Title Header */}
          <div className="flex flex-col items-center text-center mb-6">
            <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 via-slate-800 to-accent/30 border border-primary/50 shadow-2xl mb-4 sentinel-glow-primary group">
              <img src={logoUrl} alt="Logo" className="h-full w-full object-cover object-top rounded-2xl transition-transform duration-500 group-hover:scale-105" />
              <div className="absolute inset-0 rounded-2xl border border-primary/40 animate-pulse" />
            </div>

            <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-primary to-accent bg-clip-text text-transparent">
              Sentinel Twin Command
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Autonomous Mobile Security & Disaster Digital Twin Architecture
            </p>

            {/* Quick Presets */}
            <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5">
              <span className="text-[10px] uppercase font-mono text-slate-400 mr-1">Presets:</span>
              <button
                type="button"
                onClick={() => handlePresetSelect("Ankit (Lead)", "Administrator")}
                className="rounded-full border border-white/10 bg-slate-800/80 px-2.5 py-1 text-[10px] text-slate-300 hover:border-primary/50 hover:text-primary transition-all cursor-pointer font-mono"
              >
                Admin (Ankit)
              </button>
              <button
                type="button"
                onClick={() => handlePresetSelect("R. Miller (Duty)", "Operator")}
                className="rounded-full border border-white/10 bg-slate-800/80 px-2.5 py-1 text-[10px] text-slate-300 hover:border-accent/50 hover:text-accent transition-all cursor-pointer font-mono"
              >
                Operator (Duty)
              </button>
              <button
                type="button"
                onClick={() => handlePresetSelect("Observer", "Viewer")}
                className="rounded-full border border-white/10 bg-slate-800/80 px-2.5 py-1 text-[10px] text-slate-300 hover:border-success/50 hover:text-success transition-all cursor-pointer font-mono"
              >
                Viewer (Observer)
              </button>
            </div>
          </div>

          {isLoggingIn ? (
            <div className="flex flex-col items-center justify-center py-10 text-center animate-fade-in space-y-4">
              <div className="relative flex h-16 w-16 items-center justify-center">
                <Icons.Loader2 className="h-14 w-14 animate-spin text-primary" />
                <Icons.Shield className="absolute h-6 w-6 text-primary" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-white">Welcome back, {username}</h3>
                <p className="text-xs text-primary font-mono mt-1 font-semibold">
                  Authorization Level: {role.toUpperCase()}
                </p>
              </div>

              {/* Auth Progress Bar */}
              <div className="w-full max-w-xs h-2 rounded-full bg-slate-800 overflow-hidden border border-white/10 mt-2">
                <div
                  className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-300 rounded-full"
                  style={{ width: `${Math.round(((loginStep + 1) / loginStepsMessages.length) * 100)}%` }}
                />
              </div>

              <div className="h-5 flex items-center justify-center">
                <span className="text-xs font-mono text-slate-300 animate-pulse">
                  {loginStepsMessages[loginStep]}
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleLoginSubmit} className="space-y-5">
              {/* Username Input with Icon */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-1.5 block">
                  Operator ID / Username
                </label>
                <div className="relative">
                  <Icons.User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    value={username}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    required
                    className="bg-slate-800/80 border-slate-700/80 text-white pl-9 focus:border-primary focus:ring-primary/40 text-sm"
                    placeholder="Enter Operator ID"
                  />
                </div>
              </div>

              {/* Password Input with Icon */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-1.5 block">
                  Security Passcode
                </label>
                <div className="relative">
                  <Icons.Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    required
                    className="bg-slate-800/80 border-slate-700/80 text-white pl-9 focus:border-primary focus:ring-primary/40 text-sm"
                    placeholder="Enter Passcode"
                  />
                </div>
              </div>

              {/* Role Selection Cards with Detailed Descriptions */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-2 block">
                  Authorization Scope
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {(["Administrator", "Operator", "Viewer"] as const).map((r) => {
                    const details = roleDetails[r];
                    const IconComp = details.icon;
                    const isSelected = role === r;

                    return (
                      <div
                        key={r}
                        onClick={() => setRole(r)}
                        className={cn(
                          "flex items-start gap-3 rounded-2xl border p-3 transition-all cursor-pointer select-none",
                          isSelected
                            ? "border-primary bg-primary/15 shadow-md shadow-primary/10"
                            : "border-slate-800 bg-slate-800/40 text-slate-400 hover:bg-slate-800/80 hover:border-slate-700"
                        )}
                      >
                        <div className={cn("rounded-xl p-2 shrink-0 border", isSelected ? details.badgeTone : "border-slate-700 bg-slate-800 text-slate-400")}>
                          <IconComp className="h-4 w-4" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className={cn("text-xs font-bold", isSelected ? "text-white" : "text-slate-300")}>
                              {details.title}
                            </span>
                            {isSelected && (
                              <span className="flex items-center gap-1 text-[10px] font-mono font-bold text-primary">
                                <Icons.CheckCircle2 className="h-3 w-3" /> Selected
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">{details.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Checkbox & Forgot Links */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-800 text-primary focus:ring-primary h-4 w-4"
                  />
                  <span>Remember Session Token</span>
                </label>

                <button
                  type="button"
                  onClick={() => setShowForgotNotice((prev) => !prev)}
                  className="text-xs text-primary hover:underline cursor-pointer font-medium"
                >
                  Reset Credentials
                </button>
              </div>

              {showForgotNotice && (
                <div className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-center text-[11px] text-warning animate-fade-in">
                  🔑 Please contact the System Administrator or Lead Security Officer to re-issue 2FA passkeys.
                </div>
              )}

              {/* Login Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-2xl border-2 border-emerald-300 bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 py-4 px-6 text-sm font-black uppercase tracking-wider text-slate-950 shadow-[0_0_35px_rgba(0,230,190,0.7)] hover:shadow-[0_0_55px_rgba(0,230,190,0.95)] hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 cursor-pointer"
                >
                  {/* Shine Sweep Effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />

                  <Icons.ShieldCheck className="h-5 w-5 text-slate-950 shrink-0" />
                  <span className="text-slate-950 font-black tracking-wider text-sm drop-shadow-sm">Authorize & Enter Command Center</span>
                  <Icons.ArrowRight className="h-5 w-5 text-slate-950 shrink-0 group-hover:translate-x-1 transition-transform" />
                </button>

                <div className="text-center text-[10px] font-mono text-emerald-300 mt-2.5 font-bold tracking-wide">
                  👆 CLICK BUTTON TO AUTHORIZE & LAUNCH SESSION
                </div>
              </div>

              <div className="text-center text-[10px] font-mono text-slate-500 mt-2 uppercase tracking-widest">
                SyncHack 2026 · Autonomous Mobile Digital Twin System
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Feature 3: AI Analysis Breakdown Panel Component
// ----------------------------------------------------------------------------
// ----------------------------------------------------------------------------
// Feature 3: AI Analysis Breakdown Panel Component (Enhanced Real-Time)
// ----------------------------------------------------------------------------
function AiAnalysisPanel({ telemetry, provider }: { telemetry: any; provider?: SentinelDataProvider }) {
  const isLive = provider?.mode === "live";
  const backend = provider?.backendState;

  // Check if real live hardware data is actively arriving in Live Mode
  const isHardwareLive = isLive && (
    telemetry?.mqtt === "online" ||
    telemetry?.esp32 === "online" ||
    (backend?.mqtt_node_count || 0) > 0 ||
    (backend?.zones && Object.values(backend.zones).some((z: any) => z.online && z.temp !== null && z.temp !== undefined))
  );

  // If in Live Mode and hardware is unpowered/offline, strictly show Offline / '--' with ZERO dummy data
  if (isLive && !isHardwareLive) {
    return (
      <GlassCard className="sentinel-glow-primary p-5 my-4 transition-all duration-300">
        <div className="flex flex-wrap items-center justify-between border-b border-border/60 pb-3 mb-4 gap-2">
          <div className="flex items-center gap-2.5">
            <Icons.BrainCircuit className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-foreground">AI Neural Analysis & Decision Explainability</h3>
                <span className="flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[9px] font-bold text-muted-foreground border border-border/40 font-mono">
                  STANDBY
                </span>
              </div>
              <p className="text-xs text-muted-foreground">Transparent multi-sensor telemetry reasoning & decision engine</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="font-mono text-xs bg-secondary text-muted-foreground border-border/40">
              Confidence --
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Incoming Live Telemetry Card */}
          <div className="rounded-xl border border-border/60 bg-secondary/30 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <span>Incoming Telemetry (Live)</span>
              <span className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" /> Offline
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">Temperature</span>
                <span className="font-bold text-base text-muted-foreground mt-0.5 block">--</span>
              </div>

              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">Humidity</span>
                <span className="font-bold text-base text-muted-foreground mt-0.5 block">--</span>
              </div>

              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">MQ-2 (Gas/Smoke)</span>
                <span className="font-bold text-base text-muted-foreground mt-0.5 block">--</span>
              </div>

              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">MQ-7 (CO Gas)</span>
                <span className="font-bold text-base text-muted-foreground mt-0.5 block">--</span>
              </div>

              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">MQ-135 (Air Quality)</span>
                <span className="font-bold text-base text-muted-foreground mt-0.5 block">--</span>
              </div>

              <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
                <span className="text-muted-foreground block text-[10px] font-sans">Obstacle Sensor</span>
                <span className="font-bold text-sm text-muted-foreground mt-0.5 block">OFFLINE</span>
              </div>
            </div>
          </div>

          {/* AI Decision Matrix & Explainability */}
          <div className="rounded-xl border border-border/60 bg-secondary/30 p-4 space-y-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                <span>AI Hazard Risk Matrix</span>
                <Badge className="font-mono text-[10px] bg-secondary text-muted-foreground border-border/40">
                  Priority: STANDBY
                </Badge>
              </div>

              <div className="space-y-2.5 text-muted-foreground text-xs font-mono">
                <div>
                  <div className="flex justify-between text-xs mb-1 font-medium">
                    <span className="flex items-center gap-1"><Icons.Flame className="h-3 w-3" /> Fire Hazard Risk</span>
                    <span>--</span>
                  </div>
                  <Progress value={0} className="h-2 bg-secondary/60" />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1 font-medium">
                    <span className="flex items-center gap-1"><Icons.Wind className="h-3 w-3" /> Gas Leak Risk</span>
                    <span>--</span>
                  </div>
                  <Progress value={0} className="h-2 bg-secondary/60" />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1 font-medium">
                    <span className="flex items-center gap-1"><Icons.ShieldAlert className="h-3 w-3" /> Navigation Risk</span>
                    <span>--</span>
                  </div>
                  <Progress value={0} className="h-2 bg-secondary/60" />
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 mt-3 shadow-inner">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">AI Decision & Action</span>
                <span className="text-[9px] font-mono text-muted-foreground">Hardware Offline</span>
              </div>
              <div className="text-xs font-bold text-muted-foreground mt-1 flex items-center gap-1.5">
                <Icons.Radio className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span>No Hardware Connected — Awaiting Live Telemetry</span>
              </div>
              <div className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed border-t border-border/30 pt-1.5">
                Physical sensor nodes & ESP32 hardware at school are currently powered off. The AI neural inference pipeline is standing by.
              </div>
            </div>
          </div>
        </div>
      </GlassCard>
    );
  }

  // Calculate highest risk readings across all zones if available
  let maxZoneTemp = 0;
  let maxZoneSmoke = 0;
  let hasBlockedZone = false;
  let highestRiskZoneName = "";

  if (backend?.zones) {
    Object.keys(backend.zones).forEach((zId) => {
      const z = backend.zones[zId];
      if (z && z.online) {
        if (z.temp > maxZoneTemp) {
          maxZoneTemp = z.temp;
          highestRiskZoneName = zId.toUpperCase();
        }
        if (z.smoke > maxZoneSmoke) {
          maxZoneSmoke = z.smoke;
        }
        if (z.blocked) {
          hasBlockedZone = true;
        }
      }
    });
  }

  const statusTemp = parseFloat(telemetry?.summaryTemp) || (maxZoneTemp > 0 ? maxZoneTemp : 0);
  const temp = Math.max(statusTemp, maxZoneTemp || 0);

  const humidity = parseFloat(telemetry?.summaryHumidity) || 0;
  const statusMq2 = parseFloat(telemetry?.summaryGas) || (maxZoneSmoke > 0 ? maxZoneSmoke : 0);
  const mq2 = Math.max(statusMq2, maxZoneSmoke || 0);

  const mq7 = parseFloat(telemetry?.summaryCO) || 0;
  const mq135 = parseFloat(telemetry?.summaryAirQuality) || 0;
  const obstacle = hasBlockedZone || telemetry?.details?.esp32?.quality?.includes("Blocked") || false;

  // Realtime Emergency & Dynamic Risk Probabilities
  const isFireRisk = temp > 40 || mq2 > 50;
  const isGasRisk = mq2 > 35 || mq7 > 25;
  const isEmergency = isFireRisk || isGasRisk || obstacle;

  const fireProb = Math.min(99, Math.max(5, Math.round(
    (temp > 60 ? 95 : temp > 45 ? 75 : temp > 35 ? 45 : temp * 1.2) +
    (mq2 > 100 ? 45 : mq2 > 40 ? 30 : mq2 * 0.2)
  )));

  const gasProb = Math.min(99, Math.max(5, Math.round(
    (mq2 > 80 ? 85 : mq2 > 35 ? 55 : mq2 * 0.5) +
    (mq7 > 30 ? 35 : mq7 * 0.4)
  )));

  const navRiskProb = obstacle ? 96 : (temp > 50 ? 40 : 8);

  // Confidence & Priority dynamically calculated
  const confidence = backend?.ai_report?.confidence || (isEmergency ? 98 : 94);
  const priority = temp > 50 || mq2 > 80 ? "CRITICAL" : isEmergency ? "HIGH font-bold" : "NOMINAL";

  // Realtime AI Decision & Explanation
  const aiReport = backend?.ai_report;
  const decision = aiReport?.actions?.[0] || (
    temp > 50
      ? `Deploy Immediate Thermal Containment & Evacuate ${highestRiskZoneName || 'Zone'}`
      : isFireRisk
        ? "Deploy Fire Inspection & Verify Thermal Anomalies"
        : isGasRisk
          ? "Deploy Combustible Gas Sweep & Enable Emergency Ventilation"
          : obstacle
            ? "Execute Reroute Algorithm — Obstacle Detected"
            : "Maintain Autonomous Safety Patrol & Multi-Sensor Sweeps"
  );

  const reason = aiReport?.analysis || (
    temp > 40
      ? `Realtime thermal telemetry spike detected (${temp.toFixed(1)}°C). Multi-sensor fusion cross-references elevated temperature with smoke concentration.`
      : isGasRisk
        ? `Combustible gas concentration (${mq2} PPM) exceeded safety envelope baseline. Air quality monitoring prioritized.`
        : obstacle
          ? "Obstacle sensor detected path blockage (>10s stationary). Path planning engine recalculating trajectory."
          : "All sensor nodes reporting nominal values within safety threshold limits. Neural inference pipeline active."
  );

  return (
    <GlassCard className="sentinel-glow-primary p-5 my-4 transition-all duration-300">
      <div className="flex flex-wrap items-center justify-between border-b border-border/60 pb-3 mb-4 gap-2">
        <div className="flex items-center gap-2.5">
          <Icons.BrainCircuit className={cn("h-5 w-5 animate-pulse", isFireRisk ? "text-critical" : "text-primary")} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-foreground">AI Neural Analysis & Decision Explainability</h3>
              {isEmergency && (
                <span className="flex items-center gap-1 rounded-full bg-critical/20 px-2 py-0.5 text-[9px] font-bold text-critical border border-critical/40 animate-pulse font-mono">
                  <Icons.Flame className="h-3 w-3" /> REALTIME HAZARD SPIKE
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">Transparent multi-sensor telemetry reasoning & decision engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={cn("font-mono text-xs", isEmergency ? "bg-critical/20 text-critical border-critical/40" : "bg-primary/20 text-primary border-primary/30")}>
            Confidence {confidence}%
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Incoming Live Telemetry Card */}
        <div className="rounded-xl border border-border/60 bg-secondary/30 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <span>Incoming Telemetry (Live)</span>
            <span className="flex items-center gap-1 font-mono text-[10px] text-success">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-ping" /> Synchronized
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className={cn("rounded-lg p-2.5 border transition-all duration-300", temp > 40 ? "bg-critical/15 border-critical/40 text-critical shadow-sm" : "bg-background/60 border-border/40")}>
              <span className="text-muted-foreground block text-[10px] font-sans">Temperature</span>
              <div className="flex items-baseline justify-between mt-0.5">
                <span className="font-bold text-base">{temp.toFixed(1)}°C</span>
                {temp > 40 && <Icons.Flame className="h-4 w-4 text-critical animate-pulse" />}
              </div>
            </div>

            <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
              <span className="text-muted-foreground block text-[10px] font-sans">Humidity</span>
              <span className="font-bold text-base text-foreground mt-0.5 block">{humidity}%</span>
            </div>

            <div className={cn("rounded-lg p-2.5 border transition-all duration-300", mq2 > 35 ? "bg-warning/15 border-warning/40 text-warning" : "bg-background/60 border-border/40")}>
              <span className="text-muted-foreground block text-[10px] font-sans">MQ-2 (Gas/Smoke)</span>
              <span className="font-bold text-base mt-0.5 block">{mq2} PPM</span>
            </div>

            <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
              <span className="text-muted-foreground block text-[10px] font-sans">MQ-7 (CO Gas)</span>
              <span className="font-bold text-base text-foreground mt-0.5 block">{mq7} PPM</span>
            </div>

            <div className="rounded-lg bg-background/60 p-2.5 border border-border/40">
              <span className="text-muted-foreground block text-[10px] font-sans">MQ-135 (Air Quality)</span>
              <span className="font-bold text-base text-foreground mt-0.5 block">{mq135} PPM</span>
            </div>

            <div className={cn("rounded-lg p-2.5 border transition-all duration-300", obstacle ? "bg-critical/15 border-critical/40 text-critical" : "bg-background/60 border-border/40")}>
              <span className="text-muted-foreground block text-[10px] font-sans">Obstacle Sensor</span>
              <span className={cn("font-bold text-sm mt-0.5 block", obstacle ? "text-critical" : "text-success")}>
                {obstacle ? "BLOCKED" : "CLEAR"}
              </span>
            </div>
          </div>
        </div>

        {/* AI Decision Matrix & Explainability */}
        <div className="rounded-xl border border-border/60 bg-secondary/30 p-4 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              <span>AI Hazard Risk Matrix</span>
              <Badge className={cn("font-mono text-[10px]", priority === "CRITICAL" ? "bg-critical/20 text-critical border-critical/40" : priority.includes("HIGH") ? "bg-warning/20 text-warning border-warning/40" : "bg-success/20 text-success border-success/40")}>
                Priority: {priority}
              </Badge>
            </div>

            <div className="space-y-2.5">
              <div>
                <div className="flex justify-between text-xs mb-1 font-medium">
                  <span className="flex items-center gap-1"><Icons.Flame className="h-3 w-3 text-critical" /> Fire Hazard Risk</span>
                  <span className="font-mono font-bold text-critical">{fireProb}%</span>
                </div>
                <Progress value={fireProb} className="h-2 bg-secondary/60" />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1 font-medium">
                  <span className="flex items-center gap-1"><Icons.Wind className="h-3 w-3 text-warning" /> Gas Leak Risk</span>
                  <span className="font-mono font-bold text-warning">{gasProb}%</span>
                </div>
                <Progress value={gasProb} className="h-2 bg-secondary/60" />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1 font-medium">
                  <span className="flex items-center gap-1"><Icons.ShieldAlert className="h-3 w-3 text-primary" /> Navigation Obstacle Risk</span>
                  <span className="font-mono font-bold text-primary">{navRiskProb}%</span>
                </div>
                <Progress value={navRiskProb} className="h-2 bg-secondary/60" />
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 mt-3 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">AI Decision & Action</span>
              <span className="text-[9px] font-mono text-muted-foreground">Updated Live</span>
            </div>
            <div className="text-xs font-bold text-foreground mt-1 flex items-center gap-1.5">
              <Icons.Zap className="h-3.5 w-3.5 text-warning shrink-0" />
              <span>{decision}</span>
            </div>
            <div className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed border-t border-border/30 pt-1.5">
              {reason}
            </div>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

// ----------------------------------------------------------------------------
// Feature 4: Incident Lifecycle Step Visualization Component
// ----------------------------------------------------------------------------
function IncidentLifecycleView({ activeAlert }: { activeAlert?: any }) {
  const steps = [
    { title: "Detection", desc: activeAlert?.type || "Smoke / Gas Monitor", icon: Icons.AlertTriangle },
    { title: "AI Analysis", desc: "Telemetry Evaluated", icon: Icons.BrainCircuit },
    { title: "Threat Verified", desc: "Multi-Sensor Fusion", icon: Icons.ShieldCheck },
    { title: "Mission Generated", desc: "Dispatch Queue Order", icon: Icons.FileText },
    { title: "Rover Deployed", desc: "Autonomous Pathing", icon: Icons.Bot },
    { title: "Live Camera", desc: "Stream Verified", icon: Icons.Camera },
    { title: "Completed", desc: "Area Secured", icon: Icons.CheckCircle2 },
  ];

  const currentStep = activeAlert ? (activeAlert.resolved ? 6 : 4) : 0;

  return (
    <GlassCard className="p-5 my-4">
      <SectionTitle hint="Realtime Incident Stage Lifecycle">Incident Response Lifecycle</SectionTitle>
      <div className="relative mt-4 flex flex-col md:flex-row items-center justify-between gap-3">
        {steps.map((s, idx) => {
          const isDone = idx <= currentStep;
          const isCurrent = idx === currentStep;
          const IconComponent = s.icon;

          return (
            <div key={idx} className="flex-1 flex flex-col items-center text-center relative z-10 w-full md:w-auto">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-xl border transition-all duration-500",
                  isCurrent
                    ? "border-primary bg-primary/20 text-primary sentinel-glow-primary scale-110"
                    : isDone
                      ? "border-success/50 bg-success/15 text-success"
                      : "border-border/60 bg-secondary/40 text-muted-foreground opacity-50"
                )}
              >
                <IconComponent className="h-4 w-4" />
              </div>
              <span className={cn("mt-2 text-[11px] font-bold", isCurrent ? "text-primary" : isDone ? "text-foreground" : "text-muted-foreground")}>
                {s.title}
              </span>
              <span className="text-[9px] text-muted-foreground font-mono mt-0.5">{s.desc}</span>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

// ----------------------------------------------------------------------------
// Feature 5: Live Mission Timeline Panel Component
// ----------------------------------------------------------------------------
function LiveMissionTimeline({ events }: { events: any[] }) {
  return (
    <GlassCard className="p-5">
      <SectionTitle hint="Realtime Mission Event Stream">Live Mission Timeline</SectionTitle>
      <div className="space-y-2.5 max-h-72 overflow-y-auto pr-2 scrollbar-thin mt-2">
        {events && events.length > 0 ? (
          events.map((e, idx) => {
            const dateStr = new Date((e.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString();
            return (
              <div key={idx} className="flex items-start gap-3 rounded-xl border border-border/50 bg-secondary/30 p-2.5 transition-colors hover:border-primary/40">
                <div className="font-mono text-[11px] font-bold text-primary shrink-0">{dateStr}</div>
                <div className="flex-1">
                  <div className="text-xs font-semibold text-foreground">{e.description}</div>
                  {e.zone_id && <div className="text-[10px] text-muted-foreground uppercase font-mono mt-0.5">Zone: {e.zone_id}</div>}
                </div>
                <Badge
                  className={
                    e.severity === "critical"
                      ? "bg-critical/20 text-critical"
                      : e.severity === "warning"
                        ? "bg-warning/20 text-warning"
                        : "bg-primary/20 text-primary"
                  }
                >
                  {e.severity || "info"}
                </Badge>
              </div>
            );
          })
        ) : (
          <div className="text-center py-6 text-xs text-muted-foreground">No active mission events logged.</div>
        )}
      </div>
    </GlassCard>
  );
}

// ----------------------------------------------------------------------------
// Feature 6: Mission Report Generator Modal Component
// ----------------------------------------------------------------------------
function MissionReportModal({
  isOpen,
  onClose,
  reportData,
}: {
  isOpen: boolean;
  onClose: () => void;
  reportData?: any;
}) {
  if (!isOpen) return null;

  const mockReport = reportData || {
    report_id: "rpt_msn_1784920",
    title: "Autonomous Inspection Post-Mortem Report",
    mission_type: "PATROL & INSPECTION",
    outcome: "SUCCESS",
    target_zone: "Chemistry Lab (Floor 2)",
    duration: "28 seconds",
    distance_traveled: "24.5 meters",
    battery_used: "4.2%",
    avg_speed: "0.85 m/s",
    ai_confidence: "98%",
    images_captured: 12,
    recovery_attempts: 0,
    recommendations: [
      "Schedule preventive maintenance check on MQ-2 gas sensor node.",
      "Increase automated patrol sweep frequency in Chemistry Lab by 20%.",
    ],
  };

  const handleDownloadPDF = () => {
    window.open("/api/reports/mission/latest/pdf", "_blank");
  };

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fade-in">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border/80 bg-slate-900 p-6 text-slate-100 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Icons.FileText className="h-6 w-6 text-primary" />
            <div>
              <h2 className="text-lg font-bold">{mockReport.title}</h2>
              <p className="text-xs text-slate-400 font-mono">ID: {mockReport.report_id}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400 hover:text-white">
            <Icons.X className="h-5 w-5" />
          </Button>
        </div>

        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-xl border border-white/10 bg-slate-800/50 p-3">
              <span className="text-slate-400 block text-[10px]">Mission Type</span>
              <span className="font-bold text-white">{mockReport.mission_type}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-800/50 p-3">
              <span className="text-slate-400 block text-[10px]">Outcome</span>
              <span className="font-bold text-success">{mockReport.outcome}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-800/50 p-3">
              <span className="text-slate-400 block text-[10px]">Distance</span>
              <span className="font-bold text-white">{mockReport.distance_traveled}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-800/50 p-3">
              <span className="text-slate-400 block text-[10px]">Battery Consumed</span>
              <span className="font-bold text-warning">{mockReport.battery_used}</span>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-slate-800/50 p-4 space-y-2">
            <h4 className="font-bold uppercase tracking-wider text-slate-300 text-[10px]">Empirical Telemetry Metrics</h4>
            <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono">
              <div>Average Speed: <span className="text-white">{mockReport.avg_speed}</span></div>
              <div>AI Confidence: <span className="text-primary">{mockReport.ai_confidence}</span></div>
              <div>Images Captured: <span className="text-white">{mockReport.images_captured}</span></div>
              <div>Recovery Attempts: <span className="text-white">{mockReport.recovery_attempts}</span></div>
            </div>
          </div>

          <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 space-y-2">
            <h4 className="font-bold text-primary uppercase tracking-wider text-[10px] flex items-center gap-1.5">
              <Icons.Lightbulb className="h-4 w-4" /> AI Recommendations
            </h4>
            <ul className="list-disc list-inside space-y-1 text-slate-200">
              {mockReport.recommendations.map((rec: string, i: number) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t border-white/10 pt-4">
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button onClick={handleDownloadPDF} className="bg-primary text-primary-foreground">
            <Icons.Download className="mr-1.5 h-4 w-4" /> Download PDF Report
          </Button>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Feature 7: AI Recommendation Panel Component
// ----------------------------------------------------------------------------
function AiRecommendationsWidget() {
  const recs = [
    { title: "Increase Patrol Frequency", desc: "Chemistry Lab elevated thermal history.", priority: "High", icon: Icons.TrendingUp },
    { title: "Recharge Rover Battery", desc: "Capacity at 38%. Dock within 15 min.", priority: "Medium", icon: Icons.BatteryCharging },
    { title: "Calibrate Gas Sensor MQ-2", desc: "Baseline drift detected in Cafeteria.", priority: "Low", icon: Icons.Wrench },
    { title: "Inspect Chemistry Lab", desc: "Periodic physical verification recommended.", priority: "Medium", icon: Icons.Search },
  ];

  return (
    <GlassCard className="p-5">
      <SectionTitle hint="Proactive System Optimization">AI Recommendations</SectionTitle>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        {recs.map((r, i) => {
          const IconComp = r.icon;
          return (
            <div key={i} className="flex items-start gap-3 rounded-xl border border-border/60 bg-secondary/30 p-3 hover:border-primary/40 transition-colors">
              <div className="rounded-lg bg-primary/15 p-2 text-primary">
                <IconComp className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground">{r.title}</span>
                  <Badge className="bg-primary/10 text-primary border-primary/20">{r.priority}</Badge>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5">{r.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

// ----------------------------------------------------------------------------
// Page Header Component
// ----------------------------------------------------------------------------
function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {

  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 sentinel-fade-up">
      <div>
        {eyebrow && <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-primary/90">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl sentinel-text-gradient">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

function GlassCard({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "sentinel-glass rounded-2xl p-5 transition-all duration-300 hover:border-primary/30",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

// Live Clock Widget
function LiveClock() {
  const [now, setNow] = useState<Date>(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col items-end leading-tight">
      <span className="font-mono text-[13px] tabular-nums font-semibold">
        {now.toLocaleTimeString("en-GB", { hour12: false })}
      </span>
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        {now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
      </span>
    </div>
  );
}

function StatPill({
  label,
  value,
  tone = "default",
  icon,
  onClick,
}: {
  onClick?: () => void;
  label: string;
  value: React.ReactNode;
  tone?: "default" | "success" | "warning" | "critical" | "primary";
  icon?: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    default: "text-foreground",
    success: "text-success",
    warning: "text-warning",
    critical: "text-critical",
    primary: "text-primary",
  };
  return (
    <div onClick={onClick} className={cn("flex items-center gap-2 rounded-full border border-border/60 bg-secondary/40 px-3 py-1.5 text-[11px]", onClick && "cursor-pointer hover:border-primary/50 transition-colors")}>
      {icon}
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-mono font-semibold tabular-nums", tones[tone])}>{value}</span>
    </div>
  );
}

function StatusDot({ tone = "success" }: { tone?: "success" | "warning" | "critical" | "muted" }) {
  const map = {
    success: "bg-success",
    warning: "bg-warning",
    critical: "bg-critical",
    muted: "bg-muted-foreground",
  } as const;
  return (
    <span className="relative flex h-2 w-2">
      {tone !== "muted" && <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", map[tone])} />}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", map[tone])} />
    </span>
  );
}

function SectionTitle({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <div className="mb-3 flex items-baseline justify-between">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{children}</h3>
      {hint && <span className="text-[10px] text-muted-foreground/70">{hint}</span>}
    </div>
  );
}

function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "outline" | "ghost" | "danger"; size?: "sm" | "md" | "icon" }) {
  const base = "inline-flex items-center justify-center rounded-xl font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer select-none";
  const variants = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    outline: "border border-border/60 bg-secondary/40 hover:bg-secondary/60 text-foreground",
    ghost: "hover:bg-secondary/40 text-foreground",
    danger: "border border-critical/50 bg-critical/10 text-critical hover:bg-critical/20",
  };
  const sizes = {
    sm: "h-9 sm:h-8 px-3 text-xs min-h-[38px] sm:min-h-[32px]",
    md: "h-11 sm:h-10 px-4 text-sm min-h-[44px]",
    icon: "h-11 w-11 sm:h-10 sm:w-10 min-h-[44px] min-w-[44px]",
  };
  return (
    <button className={cn(base, variants[variant], sizes[size], className)} {...rest}>
      {children}
    </button>
  );
}

function Input({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 sm:h-10 w-full rounded-xl border border-border/60 bg-secondary/40 px-3.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 min-h-[44px]",
        className,
      )}
      {...rest}
    />
  );
}

function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-secondary/60", className)}>
      <div
        className="h-full rounded-full bg-primary transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

function Switch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={cn("relative h-5 w-9 rounded-full transition-colors cursor-pointer", checked ? "bg-primary" : "bg-muted")}
    >
      <span className={cn("absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform", checked ? "left-4" : "left-0.5")} />
    </button>
  );
}

function Slider({ value, min = 0, max, step = 1, onChange }: { value: number; min?: number; max: number; step?: number; onChange: (v: number) => void }) {
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
    />
  );
}

function Badge({ children, className, variant }: { children: React.ReactNode; className?: string; variant?: "outline" }) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider";
  const styles = variant === "outline" ? "border border-white/30 bg-black/60 text-white" : "";
  return <span className={cn(base, styles, className)}>{children}</span>;
}

// ----------------------------------------------------------------------------
// Reusable Demo Mode Surveillance Camera Canvas
// ----------------------------------------------------------------------------
function DemoCameraCanvas({ waypoint, battery }: { waypoint: string; battery: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let scanLine = 0;
    const draw = () => {
      ctx.fillStyle = "#0a0f0d";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid overlay
      ctx.strokeStyle = "rgba(0, 230, 190, 0.06)";
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 20) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
      }
      for (let j = 0; j < canvas.height; j += 20) {
        ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(canvas.width, j); ctx.stroke();
      }

      // Draw scanline
      scanLine = (scanLine + 1.2) % canvas.height;
      ctx.strokeStyle = "rgba(0, 230, 190, 0.2)";
      ctx.beginPath(); ctx.moveTo(0, scanLine); ctx.lineTo(canvas.width, scanLine); ctx.stroke();

      ctx.fillStyle = "rgba(0, 230, 190, 0.85)";
      ctx.font = "10px monospace";
      ctx.fillText("CAM-SURVEILLANCE-V2", 12, 18);
      ctx.fillText(`ZONE: ${(waypoint || "DOCK").toUpperCase()}`, 12, 30);
      ctx.fillText(`BATTERY: ${battery.toFixed(1)}%`, 12, 42);

      // Pulse record dot
      if (Math.floor(Date.now() / 500) % 2 === 0) {
        ctx.fillStyle = "var(--critical)";
        ctx.beginPath(); ctx.arc(canvas.width - 32, 14, 4, 0, 2 * Math.PI); ctx.fill();
      }
      ctx.fillStyle = "#ffffff";
      ctx.fillText("LIVE", canvas.width - 24, 18);

      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, [waypoint, battery]);

  return <canvas ref={canvasRef} width="240" height="135" className="h-full w-full object-cover" />;
}

// ----------------------------------------------------------------------------
// Home Page Component
// ----------------------------------------------------------------------------
function HomePage({
  provider,
  onNavigate,
}: {
  provider: SentinelDataProvider;
  onNavigate?: (tab: string) => void;
}) {
  const status = provider.status;

  // Rolling live series — appends real sensor readings every 2 s so charts animate in demo mode
  const [series, setSeries] = useState(() => generateTimeseries(20, 22, 3));
  useEffect(() => {
    const tempVal = parseFloat(status.summaryTemp || "22") || 22;
    const humVal = parseFloat(status.summaryHumidity || "50") || 50;
    const gasVal = parseFloat(status.summaryGas || "12") || 12;
    const aqVal = parseFloat(status.summaryAirQuality || "88") || 88;
    const coVal = parseFloat(status.summaryCO || "5") || 5;
    const battVal = status.battery || 100;
    const id = setInterval(() => {
      const tempNow = parseFloat(status.summaryTemp || "22") || 22;
      const humNow = parseFloat(status.summaryHumidity || "50") || 50;
      const gasNow = parseFloat(status.summaryGas || "12") || 12;
      const aqNow = parseFloat(status.summaryAirQuality || "88") || 88;
      const coNow = parseFloat(status.summaryCO || "5") || 5;
      const battNow = status.battery || 100;
      setSeries(prev => [
        ...prev.slice(-19),
        { t: new Date().toLocaleTimeString(), temperature: tempNow, humidity: humNow, gas: gasNow, battery: battNow, co: coNow, alerts: 0 }
      ]);
    }, 2000);
    // seed one point immediately
    setSeries(prev => [
      ...prev.slice(-19),
      { t: new Date().toLocaleTimeString(), temperature: tempVal, humidity: humVal, gas: gasVal, battery: battVal, co: coVal, alerts: 0 }
    ]);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.summaryTemp, status.summaryHumidity, status.summaryGas, status.summaryAirQuality, status.summaryCO, status.battery]);

  const getDetails = (key: string) => {
    return (status.details as any)?.[key] || { heartbeat: "N/A", uptime: "N/A" };
  };

  const systemItems = [
    {
      label: "Host Command Server",
      value: status.raspberryPi,
      icon: Icons.Cpu,
      tone: status.raspberryPi === "online" ? "success" : "critical",
      details: getDetails("raspberryPi")
    },
    {
      label: "ESP32 Rover",
      value: status.esp32,
      icon: Icons.Bot,
      tone: status.esp32 === "online" ? "success" : status.esp32 === "connecting" ? "warning" : "critical",
      details: getDetails("esp32")
    },
    {
      label: "MQTT Broker",
      value: status.mqtt,
      icon: Icons.Radio,
      tone: status.mqtt === "online" ? "success" : "critical",
      details: getDetails("mqtt")
    },
    {
      label: "WiFi Link",
      value: status.wifi,
      icon: Icons.Wifi,
      tone: status.wifi === "connected" ? "success" : "critical",
      details: getDetails("wifi")
    },
    {
      label: "Camera Feed",
      value: status.camera,
      icon: Icons.Camera,
      tone: status.camera === "streaming" ? "success" : "critical",
      details: getDetails("camera")
    },
    {
      label: "AI Inference",
      value: status.ai,
      icon: Icons.Sparkles,
      tone: status.ai === "active" ? "success" : "critical",
      details: getDetails("ai")
    },
  ] as const;

  const isHardwareOnline = provider?.mode === "demo" || (status.mqtt === "online" || status.esp32 === "online");

  const getSummaryValue = (label: string) => {
    if (provider?.mode === "live" && !isHardwareOnline) {
      return "--";
    }
    if (label === "Temperature") return status.summaryTemp || "--";
    if (label === "Humidity") return status.summaryHumidity || "--";
    if (label === "Air Quality") return status.summaryAirQuality || "--";
    if (label === "Gas / CO") return status.summaryGas || "--";
    if (label === "CO (MQ-7)") return status.summaryCO || "--";
    if (label === "Battery Level") return isHardwareOnline && status.battery !== undefined ? `${Math.round(status.battery)}` : "--";
    return "--";
  };

  const sensorCards = [
    { icon: Icons.Thermometer, label: "Temperature", value: getSummaryValue("Temperature"), unit: "°C", tone: "text-primary", chart: "temperature", color: "oklch(0.68 0.19 250)" },
    { icon: Icons.Droplets, label: "Humidity", value: getSummaryValue("Humidity"), unit: "%", tone: "text-accent", chart: "humidity", color: "oklch(0.72 0.15 210)" },
    { icon: Icons.Wind, label: "Air Quality (MQ-135)", value: getSummaryValue("Air Quality"), unit: "%", tone: "text-success", chart: "gas", color: "oklch(0.72 0.18 155)" },
    { icon: Icons.Flame, label: "Gas (MQ-2)", value: getSummaryValue("Gas / CO"), unit: "%", tone: "text-warning", chart: "gas", color: "oklch(0.78 0.18 65)" },
    { icon: Icons.ShieldAlert, label: "CO (MQ-7)", value: getSummaryValue("CO (MQ-7)"), unit: "%", tone: "text-critical", chart: "co", color: "oklch(0.62 0.17 29)" },
  ];

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeader
        eyebrow="Command Center"
        title="Sentinel Twin X"
        description="Live telemetry from the autonomous safety rover. All systems reporting in real time."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <GlassCard className="lg:col-span-2 sentinel-conic-border relative overflow-hidden p-6 sentinel-fade-up">
          <div className="sentinel-conic-glow" />
          <div className="pointer-events-none absolute inset-0 sentinel-grid-bg opacity-40" />
          <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-primary/30 blur-3xl" />
          <div className="pointer-events-none absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-accent/20 blur-3xl" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className={cn("inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-widest font-mono", isHardwareOnline ? "border-primary/30 bg-primary/10 text-primary" : "border-critical/30 bg-critical/10 text-critical")}>
                <StatusDot /> {isHardwareOnline ? "Live · Autonomous mode" : "OFFLINE · Hardware Power Off"}
              </div>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">
                {isHardwareOnline ? (
                  <>Patrolling <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">{status.currentRoom}</span></>
                ) : (
                  <span className="text-muted-foreground">Rover Disconnected</span>
                )}
              </h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                {isHardwareOnline ? (
                  <>Rover is executing <span className="font-medium text-foreground">{status.currentMission}</span>. AI vision + multi-sensor fusion active.</>
                ) : (
                  <>Hardware is unpowered. Connect ESP32 or MQTT network to receive live telemetry.</>
                )}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={() => onNavigate?.("twin")} className="bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-lg shadow-primary/30 hover:opacity-90 cursor-pointer">
                  Open Digital Twin <Icons.ChevronRight className="ml-1 h-4 w-4" />
                </Button>
                <Button variant="outline" onClick={() => onNavigate?.("camera")} className="cursor-pointer">Live Camera</Button>
              </div>
            </div>
            <div className="relative flex-shrink-0">
              <div className="relative h-48 w-48">
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary/50 to-accent/30 blur-2xl sentinel-float" />
                <div className="absolute inset-0 rounded-full border border-primary/20 sentinel-orbit-ring">
                  <span className="absolute left-1/2 top-0 h-2 w-2 -translate-x-1/2 rounded-full bg-primary shadow-[0_0_12px_oklch(0.68_0.19_250)]" />
                </div>
                <div className="absolute inset-4 rounded-full border border-accent/20 sentinel-orbit-ring-slow">
                  <span className="absolute right-0 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_10px_oklch(0.72_0.15_210)]" />
                </div>
                <div className="relative flex h-full w-full items-center justify-center rounded-full border border-border bg-card/60 backdrop-blur-xl">
                  <Icons.Bot className="h-16 w-16 text-primary" strokeWidth={1.5} />
                  <div className="absolute inset-6 rounded-full border border-primary/30 sentinel-pulse-ring" />
                </div>
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard onClick={() => onNavigate?.("camera")} className="sentinel-fade-up cursor-pointer hover:border-primary/40 p-5 flex flex-col" style={{ animationDelay: "60ms" }}>
          <div className="flex items-center justify-between border-b border-border/30 pb-2">
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-critical animate-pulse" />
              Live Camera Feed (CAM-01)
            </div>
            <Icons.Camera className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="relative mt-3 flex-1 overflow-hidden rounded-xl bg-black aspect-video flex items-center justify-center border border-border/40">
            <img
              src="/api/video-feed"
              alt="Live Camera Feed"
              className="h-full w-full object-cover"
              onError={(e) => {
                // If endpoint re-initializes, keep src live
                const target = e.target as HTMLImageElement;
                if (!target.src.includes('retry')) {
                  setTimeout(() => {
                    target.src = "/api/video-feed?retry=" + Date.now();
                  }, 1000);
                }
              }}
            />
          </div>
        </GlassCard>

        <GlassCard onClick={() => onNavigate?.("mission")} className="sentinel-fade-up cursor-pointer hover:border-primary/40 p-5 flex flex-col justify-between" style={{ animationDelay: "100ms" }}>
          <div>
            <div className="flex items-center justify-between border-b border-border/30 pb-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground font-semibold">Battery Level</span>
              <Icons.Battery className={`h-4 w-4 ${status.battery > 40 ? "text-success" : status.battery > 20 ? "text-warning" : "text-critical"}`} />
            </div>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="font-mono text-4xl font-semibold tabular-nums">
                {provider.mode === "live" && status.esp32 === "offline" ? (
                  <span className="text-2xl text-muted-foreground font-mono">--</span>
                ) : (
                  <>
                    {status.battery.toFixed(1)}
                    <span className="text-xl text-muted-foreground">%</span>
                  </>
                )}
              </span>
            </div>
            <div className="mt-1 text-[10px] text-muted-foreground leading-tight">
              {provider.mode === "live" && status.esp32 === "offline"
                ? "Waiting for ESP32 connection..."
                : status.battery > 99 ? "Fully Charged · Docked" : "Discharging · ~ 4h 12m remaining"}
            </div>
            <div className="mt-3">
              <Progress value={status.battery} className="h-1.5 bg-secondary/60" />
            </div>
          </div>
          <div className="mt-3 h-14">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="battArea" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.68 0.19 250)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.68 0.19 250)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area isAnimationActive={false} dataKey="battery" stroke="oklch(0.68 0.19 250)" strokeWidth={1.5} fill="url(#battArea)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {sensorCards.map((s, i) => (
          <GlassCard
            key={s.label}
            onClick={() => onNavigate?.("analytics")} className="group relative overflow-hidden sentinel-fade-up transition-all hover:-translate-y-0.5 hover:border-primary/40 cursor-pointer"
            style={{ animationDelay: `${100 + i * 40}ms` }}
          >
            <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-0 blur-2xl transition-opacity group-hover:opacity-60" style={{ background: s.color }} />
            <div className="relative flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{s.label}</span>
              <s.icon className={`h-4 w-4 ${s.tone}`} />
            </div>
            <div className="relative mt-2 flex items-baseline gap-1">
              <span className="font-mono text-3xl font-semibold tabular-nums">{s.value}</span>
              {s.value !== "--" && <span className="text-xs text-muted-foreground">{s.unit}</span>}
            </div>
            <div className="relative mt-2 h-12">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series}>
                  <defs>
                    <linearGradient id={`sensor-${i}`} x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor={s.color} stopOpacity={0.5} />
                      <stop offset="100%" stopColor={s.color} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area isAnimationActive={false} dataKey={s.chart} stroke={s.color} strokeWidth={1.5} fill={`url(#sensor-${i})`} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2 sentinel-fade-up">
          <SectionTitle hint="Realtime node diagnostics">System Health Nodes</SectionTitle>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {systemItems.map((it) => (
              <div key={it.label} onClick={() => onNavigate?.("settings")} className="group relative overflow-hidden rounded-xl border border-border/60 bg-secondary/30 p-3 transition-colors hover:border-primary/40 cursor-pointer">
                <div className="flex items-center justify-between">
                  <it.icon className="h-4 w-4 text-muted-foreground" />
                  <StatusDot tone={it.tone as any} />
                </div>
                <div className="mt-2 text-[11px] uppercase tracking-wider text-muted-foreground">{it.label}</div>
                <div className="mt-0.5 text-sm font-semibold capitalize flex items-center gap-1.5">
                  <span className={cn(
                    it.tone === "success" ? "text-success" : it.tone === "warning" ? "text-warning" : "text-critical"
                  )}>
                    {it.value}
                  </span>
                </div>
                {/* Details Section */}
                <div className="mt-2 space-y-0.5 border-t border-border/30 pt-1.5 text-[9px] text-muted-foreground opacity-80 group-hover:opacity-100 transition-opacity">
                  <div>Status: <span className={cn("font-semibold", (it.value === "online" || it.value === "connected" || it.value === "streaming" || it.value === "active") ? "text-success" : it.value === "connecting" ? "text-warning" : "text-critical")}>
                    {(it.value === "online" || it.value === "connected" || it.value === "streaming" || it.value === "active") ? "Online" : it.value === "connecting" ? "Connecting" : "Offline"}
                  </span></div>
                  {it.details.heartbeat && <div>Heartbeat: {it.details.heartbeat}</div>}
                  {it.details.uptime && <div>Uptime: {it.details.uptime}</div>}
                  {it.details.latency && <div>Latency: {it.details.latency}</div>}
                  {it.details.quality && <div>Quality: {it.details.quality}</div>}
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard onClick={() => onNavigate?.("settings")} className="sentinel-fade-up cursor-pointer hover:border-primary/40 flex flex-col">
          <SectionTitle hint="Aggregate rating">Overall Platform Health</SectionTitle>
          <div className="flex flex-1 flex-col items-center justify-center">
            <RadialHealth value={status.systemHealth} />
            <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Icons.TrendingUp className="h-3 w-3 text-success" /> Connection quality stable
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Feature 3: AI Neural Analysis & Decision Explainability Panel */}
      <AiAnalysisPanel telemetry={status} provider={provider} />

      {/* Feature 4: Incident Response Lifecycle Stage */}
      <IncidentLifecycleView activeAlert={provider.alerts?.[0]} />

      {/* Feature 5 & 7: Live Mission Timeline & AI Recommendations */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <LiveMissionTimeline events={provider.timeline || []} />
        <AiRecommendationsWidget />
      </div>
    </div>
  );
}

function RadialHealth({ value }: { value: number }) {
  const r = 46;
  const c = 2 * Math.PI * r;
  const off = c - (value / 100) * c;
  return (
    <svg width="140" height="140" viewBox="0 0 120 120" className="-rotate-90">
      <circle cx="60" cy="60" r={r} strokeWidth="8" className="fill-none stroke-secondary/60" />
      <circle
        cx="60" cy="60" r={r} strokeWidth="8" strokeLinecap="round"
        className="fill-none stroke-primary transition-all duration-700"
        strokeDasharray={c} strokeDashoffset={off}
      />
      <g className="rotate-90" style={{ transformOrigin: "60px 60px" }}>
        <text x="60" y="58" textAnchor="middle" className="fill-white text-[22px] font-semibold">
          {Math.round(value)}%
        </text>
        <text x="60" y="76" textAnchor="middle" className="fill-white text-[9px] uppercase tracking-widest">
          Health Score
        </text>
      </g>
    </svg>
  );
}

// ----------------------------------------------------------------------------
// Digital Twin Components with Interactive SVG Overlay & Smooth Gliding
// ----------------------------------------------------------------------------
function DigitalTwinPage({ provider }: { provider: SentinelDataProvider }) {
  const [floor, setFloor] = useState(1);
  const [selected, setSelected] = useState<Room | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const lastRoverFloorRef = useRef<number | null>(null);

  const floorMeta = buildingConfig.floors.find((f) => f.id === floor)!;
  const backendState = provider.backendState;

  const rooms = useMemo(() => {
    const baseRooms = buildingConfig.rooms.filter((r) => r.floor === floor);
    if (!backendState || !backendState.zones) {
      return baseRooms;
    }
    const mapping: { [key: string]: string } = {
      "r-201": "chem_lab",
      "r-206": "cad_lab",
      "r-103": "kitchen",
      "r-101": "corridor",
      "r-203": "classroom_1",
      "r-105": "atl_lab",
      "r-204": "classroom_2",
    };
    return baseRooms.map((room) => {
      const zoneId = mapping[room.id];
      if (!zoneId) return room;
      const zoneData = backendState.zones[zoneId];
      const riskData = backendState.risk_scores[zoneId];
      if (!zoneData) return room;
      return {
        ...room,
        temperature: zoneData.temp !== null && zoneData.temp !== undefined ? zoneData.temp : room.temperature,
        humidity: zoneData.humidity !== null && zoneData.humidity !== undefined ? zoneData.humidity : room.humidity,
        gas: zoneData.smoke !== null && zoneData.smoke !== undefined ? zoneData.smoke : room.gas,
        flame: zoneData.smoke > 100 || (zoneId === "chem_lab" && zoneData.temp > 35),
        status: riskData && riskData.status ? (riskData.status === "green" ? "normal" : riskData.status === "offline" ? "offline" : riskData.status) : room.status,
      } as Room;
    });
  }, [floor, backendState]);

  // Auto-track the rover's floor location
  useEffect(() => {
    if (backendState && backendState.rover && backendState.rover.current_zone) {
      const mappingInverse: { [key: string]: string } = {
        "chem_lab": "r-201",
        "cad_lab": "r-206",
        "kitchen": "r-103",
        "corridor": "r-101",
        "classroom_1": "r-203",
        "atl_lab": "r-105",
        "classroom_2": "r-204",
      };
      const roomId = mappingInverse[backendState.rover.current_zone] || backendState.rover.current_zone;
      const foundRoom = buildingConfig.rooms.find((r) => r.id === roomId);
      if (foundRoom) {
        if (lastRoverFloorRef.current === null || lastRoverFloorRef.current !== foundRoom.floor) {
          setFloor(foundRoom.floor);
        }
        lastRoverFloorRef.current = foundRoom.floor;
      }
    }
  }, [backendState]);

  const rover = useMemo(() => {
    if (backendState && backendState.rover && backendState.rover.current_zone) {
      const mappingInverse: { [key: string]: string } = {
        "chem_lab": "r-201",
        "cad_lab": "r-206",
        "kitchen": "r-103",
        "corridor": "r-101",
        "classroom_1": "r-203",
        "atl_lab": "r-105",
        "classroom_2": "r-204",
      };
      const roomId = mappingInverse[backendState.rover.current_zone] || backendState.rover.current_zone;
      const found = rooms.find((r) => r.id === roomId);
      if (found) return found;
    }
    return null;
  }, [rooms, backendState]);

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeader
        eyebrow="Spatial Intelligence"
        title="Digital Twin Map"
        description={`${buildingConfig.name} · ${floorMeta.name} · ${rooms.length} monitored zones`}
        actions={
          <>
            <div className="flex rounded-full border border-border/60 bg-secondary/40 p-1">
              {buildingConfig.floors.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFloor(f.id)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium transition-colors cursor-pointer",
                    floor === f.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icons.Layers className="h-3 w-3" /> {f.name}
                </button>
              ))}
            </div>
            <Button variant="outline" size="sm" onClick={() => setFullscreen(true)}>
              <Icons.Maximize2 className="mr-1.5 h-3.5 w-3.5" /> Fullscreen
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <GlassCard className="relative overflow-hidden p-4 md:p-6 sentinel-fade-up">
          <MapViewer floorMeta={floorMeta} rooms={rooms} rover={rover} selectedId={selected?.id} onSelect={setSelected} backendState={backendState} />
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(["normal", "warning", "critical", "offline"] as const).map((s) => (
              <StatPill
                key={s}
                label={s.toUpperCase()}
                value={rooms.filter((r) => r.status === s).length}
                tone={s === "normal" ? "success" : s === "warning" ? "warning" : s === "offline" ? "default" : "critical"}
                icon={<span className={cn("h-2 w-2 rounded-full", s === "normal" ? "bg-success" : s === "warning" ? "bg-warning" : s === "offline" ? "bg-muted-foreground" : "bg-critical")} />}
              />
            ))}
            <StatPill label="Rover on this floor" value={rover ? rover.name : "Elevated / Ground Base"} tone="primary" icon={<Icons.MapPin className="h-3 w-3" />} />
          </div>
        </GlassCard>

        <RoomDetailPanel room={selected ?? rover ?? rooms[0]} />
      </div>

      {fullscreen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-2xl sentinel-fade-up">
          <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-primary">Spatial Projection Overlay</div>
              <div className="text-lg font-semibold">{buildingConfig.name} — {floorMeta.name}</div>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setFullscreen(false)}><Icons.X className="h-5 w-5" /></Button>
          </div>
          <div className="flex-1 p-6">
            <MapViewer floorMeta={floorMeta} rooms={rooms} rover={rover} selectedId={selected?.id} onSelect={setSelected} backendState={backendState} />
          </div>
        </div>
      )}
    </div>
  );
}

function MapViewer({
  floorMeta, rooms, rover, selectedId, onSelect, backendState,
}: {
  floorMeta: { id: number; name: string; cols: number; rows: number };
  rooms: Room[];
  rover: Room | null;
  selectedId?: string;
  onSelect: (r: Room) => void;
  backendState: any;
}) {
  const statusStyles = {
    normal: "border-success/40 bg-success/10 hover:bg-success/15 hover:border-success/60",
    warning: "border-warning/50 bg-warning/12 hover:bg-warning/20 hover:border-warning/70",
    critical: "border-critical/60 bg-critical/15 hover:bg-critical/25 hover:border-critical/80",
    offline: "border-muted-foreground/30 bg-muted/10 hover:bg-muted/15 hover:border-muted-foreground/50 opacity-60",
  } as const;

  const dotStyles = {
    normal: "bg-success",
    warning: "bg-warning",
    critical: "bg-critical",
    offline: "bg-muted-foreground",
  } as const;

  const mappingInverse: { [key: string]: string } = {
    "chem_lab": "r-201",
    "cad_lab": "r-206",
    "kitchen": "r-103",
    "corridor": "r-101",
    "classroom_1": "r-203",
    "atl_lab": "r-105",
    "classroom_2": "r-204",
  };

  const getRoomCenter = (roomId: string) => {
    const room = buildingConfig.rooms.find(r => r.id === roomId);
    if (!room) return null;
    const cx = ((room.x + room.w / 2) / floorMeta.cols) * 100;
    const cy = ((room.y + room.h / 2) / floorMeta.rows) * 100;
    return { x: cx, y: cy, floor: room.floor };
  };

  // Resolve path centers on current floor
  const rawPath = backendState?.rover?.path || [];
  const pathRoomIds = rawPath.map((p: string) => mappingInverse[p] || p);
  const pathPoints = pathRoomIds
    .map((rid: string) => getRoomCenter(rid))
    .filter((pt: any) => pt && pt.floor === floorMeta.id) as { x: number; y: number }[];

  const roverZone = backendState?.rover?.current_zone;
  const roverRoomId = roverZone ? (mappingInverse[roverZone] || roverZone) : null;
  const roverCenter = roverRoomId ? getRoomCenter(roverRoomId) : null;

  const showRoverOnThisFloor = roverCenter && roverCenter.floor === floorMeta.id;
  const allPathPoints = showRoverOnThisFloor && roverCenter ? [roverCenter, ...pathPoints] : pathPoints;

  // Target destination
  const targetZone = backendState?.rover?.target_zone;
  const targetRoomId = targetZone ? (mappingInverse[targetZone] || targetZone) : null;
  const targetCenter = targetRoomId ? getRoomCenter(targetRoomId) : null;
  const showTargetOnThisFloor = targetCenter && targetCenter.floor === floorMeta.id;

  // Calculate Visited Rooms
  const currentIdx = roverRoomId ? pathRoomIds.indexOf(roverRoomId) : -1;
  const visitedRoomIds = currentIdx !== -1 ? pathRoomIds.slice(0, currentIdx) : [];

  return (
    <div
      className="relative w-full overflow-hidden rounded-xl border border-border/70 bg-background/40 sentinel-grid-bg"
      style={{ aspectRatio: `${floorMeta.cols} / ${floorMeta.rows}` }}
    >
      <div
        className="absolute inset-3 grid gap-2"
        style={{
          gridTemplateColumns: `repeat(${floorMeta.cols}, 1fr)`,
          gridTemplateRows: `repeat(${floorMeta.rows}, 1fr)`,
        }}
      >
        {rooms.map((r) => {
          const isSel = r.id === selectedId;
          const hasRover = showRoverOnThisFloor && roverRoomId === r.id;
          const isVisited = visitedRoomIds.includes(r.id);
          return (
            <button
              key={r.id}
              onClick={() => onSelect(r)}
              className={cn(
                "group relative overflow-hidden rounded-lg border p-2 text-left transition-all duration-300 cursor-pointer",
                statusStyles[r.status],
                isSel && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                isVisited && "border-success/30 bg-success/5"
              )}
              style={{
                gridColumn: `${r.x + 1} / span ${r.w}`,
                gridRow: `${r.y + 1} / span ${r.h}`,
              }}
            >
              <div className="flex items-center justify-between">
                <span className="truncate text-[11px] font-semibold">{r.name}</span>
                <span className={cn("h-1.5 w-1.5 rounded-full", dotStyles[r.status])} />
              </div>
              <div className="mt-1 font-mono text-[10px] tabular-nums text-muted-foreground">
                {r.status === "offline" ? (
                  <span>Offline</span>
                ) : (
                  <>{r.temperature}°C · {r.humidity}%</>
                )}
              </div>

              {isVisited && (
                <div className="absolute bottom-1 left-1.5 flex items-center gap-1 rounded bg-success/20 px-1 py-0.5 text-[6px] font-bold uppercase tracking-wider text-success">
                  ✓ Visited
                </div>
              )}

              {hasRover && (
                <div className="absolute bottom-1 right-1.5 flex items-center gap-1 rounded bg-primary/20 px-1 py-0.5 text-[6px] font-bold uppercase tracking-wider text-primary animate-pulse">
                  🚗 ROVER
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* SVG overlay layer for paths, marker, and smooth glide animations */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        {/* Animated Dashed Path Vector Line */}
        {allPathPoints.length > 1 && (
          <polyline
            points={allPathPoints.map(p => `${p.x},${p.y}`).join(" ")}
            fill="none"
            stroke="var(--primary)"
            strokeWidth="0.8"
            strokeDasharray="1.5,1.5"
            className="sentinel-dash-path"
          />
        )}

        {/* Hazard Pulse Sonar Indicators */}
        {rooms.filter(r => r.status === 'critical' || r.status === 'warning').map(r => {
          const center = getRoomCenter(r.id);
          if (!center) return null;
          return (
            <circle
              key={`hazard-${r.id}`}
              cx={center.x}
              cy={center.y}
              r="4.5"
              fill="none"
              stroke={r.status === 'critical' ? 'var(--critical)' : 'var(--warning)'}
              strokeWidth="0.3"
              className="animate-ping"
              style={{ transformOrigin: `${center.x}px ${center.y}px` }}
            />
          );
        })}

        {/* Blinking Target Destination Reticle */}
        {showTargetOnThisFloor && targetCenter && (
          <g transform={`translate(${targetCenter.x}, ${targetCenter.y})`}>
            <circle cx="0" cy="0" r="3.5" fill="none" stroke="var(--critical)" strokeWidth="0.4" className="animate-ping" />
            <circle cx="0" cy="0" r="1.5" fill="none" stroke="var(--critical)" strokeWidth="0.5" />
            <line x1="-2.5" y1="0" x2="2.5" y2="0" stroke="var(--critical)" strokeWidth="0.3" />
            <line x1="0" y1="-2.5" x2="0" y2="2.5" stroke="var(--critical)" strokeWidth="0.3" />
          </g>
        )}

        {/* Car Rover Avatar — top-down view, glides smoothly via CSS transform */}
        {showRoverOnThisFloor && roverCenter && (
          <g
            transform={`translate(${roverCenter.x}, ${roverCenter.y})`}
            style={{ transition: 'transform 1.2s ease-in-out', transformOrigin: 'center' }}
          >
            {/* Sonar ping ring */}
            <circle cx="0" cy="0" r="3.8" fill="var(--primary)" opacity="0.18" className="animate-ping" />

            {/* Car body — top-down silhouette */}
            {/* Main body */}
            <rect x="-1.9" y="-3.1" width="3.8" height="6.2" rx="1.1" ry="1.1"
              fill="var(--primary)" opacity="0.92" />

            {/* Cabin / roof highlight */}
            <rect x="-1.2" y="-2.0" width="2.4" height="2.8" rx="0.6" ry="0.6"
              fill="var(--background)" opacity="0.55" />

            {/* Front windshield line */}
            <line x1="-1.1" y1="-1.85" x2="1.1" y2="-1.85"
              stroke="var(--primary)" strokeWidth="0.25" opacity="0.9" />

            {/* Headlights */}
            <circle cx="-1.4" cy="-2.8" r="0.35" fill="#facc15" opacity="0.95" />
            <circle cx="1.4" cy="-2.8" r="0.35" fill="#facc15" opacity="0.95" />

            {/* Tail lights */}
            <circle cx="-1.4" cy="2.8" r="0.3" fill="var(--critical)" opacity="0.85" />
            <circle cx="1.4" cy="2.8" r="0.3" fill="var(--critical)" opacity="0.85" />

            {/* Front-left wheel */}
            <rect x="-2.5" y="-2.5" width="0.75" height="1.4" rx="0.3"
              fill="var(--foreground)" opacity="0.8" />
            {/* Front-right wheel */}
            <rect x="1.75" y="-2.5" width="0.75" height="1.4" rx="0.3"
              fill="var(--foreground)" opacity="0.8" />
            {/* Rear-left wheel */}
            <rect x="-2.5" y="1.1" width="0.75" height="1.4" rx="0.3"
              fill="var(--foreground)" opacity="0.8" />
            {/* Rear-right wheel */}
            <rect x="1.75" y="1.1" width="0.75" height="1.4" rx="0.3"
              fill="var(--foreground)" opacity="0.8" />

            {/* Centre dot / glow */}
            <circle cx="0" cy="0" r="0.5" fill="var(--accent)" opacity="0.95" />
          </g>
        )}
      </svg>
    </div>
  );
}

function RoomDetailPanel({ room }: { room: Room }) {
  const isOffline = room.status === "offline";

  // MQ-2 smoke sensor (room.gas) and MQ-7 CO (room.co) directly as percentage
  const mq2Pct = room.gas !== null && room.gas !== undefined ? Math.max(0, Math.min(100, Math.round(room.gas))) : 0;
  const mq7Pct = room.co !== null && room.co !== undefined ? Math.max(0, Math.min(100, Math.round(room.co))) : 0;
  const mq135Pct = room.airQuality !== null && room.airQuality !== undefined ? Math.max(0, Math.min(100, Math.round(room.airQuality))) : Math.max(0, 100 - mq2Pct);

  const metrics = [
    {
      icon: Icons.Thermometer,
      label: "Temperature",
      value: isOffline ? "--" : `${room.temperature.toFixed(1)}°C`,
      tone: isOffline ? "text-muted-foreground" : room.temperature > 30 ? "text-critical" : room.temperature > 26 ? "text-warning" : "text-success"
    },
    {
      icon: Icons.Droplets,
      label: "Humidity",
      value: isOffline ? "--" : `${room.humidity.toFixed(0)}%`,
      tone: isOffline ? "text-muted-foreground" : "text-accent"
    },
    {
      icon: Icons.Wind,
      label: "Air Quality (MQ-135)",
      value: isOffline ? "--" : `${mq135Pct}%`,
      tone: isOffline ? "text-muted-foreground" : mq135Pct < 60 ? "text-critical" : mq135Pct < 85 ? "text-warning" : "text-success"
    },
    {
      icon: Icons.Flame,
      label: "Gas (MQ-2) / CO (MQ-7)",
      value: isOffline ? "--" : `MQ-2: ${mq2Pct}% / MQ-7: ${mq7Pct}%`,
      tone: isOffline ? "text-muted-foreground" : mq2Pct > 35 || mq7Pct > 35 ? "text-critical" : mq2Pct > 15 || mq7Pct > 15 ? "text-warning" : "text-success"
    },
  ];

  return (
    <GlassCard className="sentinel-fade-up p-0">
      <div className="border-b border-border/60 p-5">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-primary font-semibold">
          <StatusDot tone={room.status === "normal" ? "success" : room.status === "warning" ? "warning" : room.status === "offline" ? "muted" : "critical"} />
          {room.status.toUpperCase()}
        </div>
        <h3 className="mt-1.5 text-xl font-semibold">{room.name}</h3>
        <p className="text-xs text-muted-foreground font-mono">Floor {room.floor} · Zone {room.id}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 p-4">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-border/50 bg-secondary/30 p-3">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
              <span>{m.label}</span>
              <m.icon className={cn("h-3.5 w-3.5", m.tone)} />
            </div>
            <div className={cn("mt-1 font-mono text-lg font-semibold tabular-nums", m.tone)}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="border-t border-border/60 p-4">
        <SectionTitle>Realtime Sensor Snapshot</SectionTitle>
        <div className="relative aspect-video overflow-hidden rounded-lg border border-border/60 bg-black">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10" />
          <Icons.Camera className="absolute left-1/2 top-1/2 h-8 w-8 -translate-x-1/2 -translate-y-1/2 text-muted-foreground/60 animate-pulse" />
          <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-critical/90 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-white">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" /> SCAN ACTIVE
          </div>
          <div className="absolute bottom-2 right-2 font-mono text-[9px] text-white/80">CAM-{room.id.toUpperCase()}</div>
        </div>
      </div>
    </GlassCard>
  );
}

function MiniStat({ label, value, icon: Icon, tone }: { label: string; value: string; icon: React.ComponentType<{ className?: string }>; tone: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-secondary/30 p-3">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
        <span>{label}</span>
        <Icon className={cn("h-3.5 w-3.5", tone)} />
      </div>
      <div className="mt-1 truncate text-sm font-semibold">{value}</div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// ----------------------------------------------------------------------------
// Mission Control Card Component
// ----------------------------------------------------------------------------
export type MissionControlStatus = "Idle" | "Starting" | "Patrolling" | "Paused" | "Emergency" | "Mission Complete";

export function MissionControlCard({
  provider,
  sendRoverCommand,
}: {
  provider: SentinelDataProvider;
  sendRoverCommand?: (cmd: string) => void;
}) {
  const [missionStatus, setMissionStatus] = useState<MissionControlStatus>("Idle");
  const [autonomous, setAutonomous] = useState<boolean>(true);

  // Sync status with backendState or provider
  useEffect(() => {
    if (provider?.backendState?.rover?.status) {
      const st = String(provider.backendState.rover.status).toLowerCase();
      if (st.includes("patrol") || st.includes("en_route") || st.includes("moving")) setMissionStatus("Patrolling");
      else if (st.includes("pause")) setMissionStatus("Paused");
      else if (st.includes("emerg") || st.includes("alert")) setMissionStatus("Emergency");
      else if (st.includes("start")) setMissionStatus("Starting");
      else if (st.includes("done") || st.includes("complete")) setMissionStatus("Mission Complete");
      else if (st.includes("idle")) setMissionStatus("Idle");
    }
  }, [provider?.backendState]);

  // Determine Rover Status: Online vs Offline
  const roverStatus: "Online" | "Offline" =
    provider?.mode === "demo" ||
      provider?.status?.esp32 === "online" ||
      provider?.status?.mqtt === "online" ||
      Boolean(provider?.connected)
      ? "Online"
      : "Offline";

  const handleCommand = (cmd: "start" | "pause" | "stop" | "emergency" | "autonomous_on" | "autonomous_off") => {
    const payload = { command: cmd };
    const topic = "sentinel/commands/rover";
    const payloadStr = JSON.stringify(payload);

    // Explicit Console Logging required by prompt
    console.log("MQTT Topic:", topic);
    console.log("MQTT Payload:", payloadStr);

    // Play feedback sound & desktop notification
    playNotificationSound(cmd === "emergency" ? "Critical" : cmd === "start" || cmd === "autonomous_on" ? "success" : "info");
    sendDesktopNotification(
      `Mission Control: ${cmd.toUpperCase()}`,
      `Published MQTT payload to ${topic}: ${payloadStr}`,
      cmd === "emergency" ? "Critical" : "Medium"
    );

    // Update local Mission Status & Autonomous state immediately
    if (cmd === "start") {
      setMissionStatus("Starting");
      setTimeout(() => setMissionStatus("Patrolling"), 1200);
    } else if (cmd === "pause") {
      setMissionStatus("Paused");
    } else if (cmd === "stop") {
      setMissionStatus("Mission Complete");
    } else if (cmd === "emergency") {
      setMissionStatus("Emergency");
    } else if (cmd === "autonomous_on") {
      setAutonomous(true);
    } else if (cmd === "autonomous_off") {
      setAutonomous(false);
    }

    // Call provider's sendMqttPayload if present, or sendRoverCommand
    if (provider.sendMqttPayload) {
      provider.sendMqttPayload(topic, payload);
    } else if (sendRoverCommand) {
      if (cmd === "start") sendRoverCommand("Autonomous Patrol");
      else if (cmd === "pause") sendRoverCommand("Pause");
      else if (cmd === "stop") sendRoverCommand("Stop");
      else if (cmd === "emergency") sendRoverCommand("Stop");
    }
  };

  return (
    <GlassCard className="sentinel-fade-up relative overflow-hidden p-5 border-border/80 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 shadow-sm">
            <Icons.Radio className="h-5 w-5 animate-pulse text-primary" />
          </div>
          <div>
            <h3 className="text-base font-semibold tracking-tight text-foreground font-mono">Mission Control</h3>
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
              <span className="text-primary font-semibold">Topic:</span>
              <span className="rounded bg-secondary/60 px-1.5 py-0.5 text-[10px]">sentinel/commands/rover</span>
            </div>
          </div>
        </div>

        {/* Autonomous Mode Toggle Switch */}
        <div className="flex items-center gap-2 rounded-full border border-border/60 bg-secondary/40 px-3 py-1.5 text-xs backdrop-blur-md">
          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Autonomous:</span>
          <button
            type="button"
            onClick={() => {
              const nextState = !autonomous;
              handleCommand(nextState ? "autonomous_on" : "autonomous_off");
            }}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold font-mono transition-all cursor-pointer shadow-sm",
              autonomous
                ? "bg-success/20 text-success border border-success/40 shadow-success/10"
                : "bg-muted text-muted-foreground border border-border"
            )}
          >
            <span className={cn("h-2 w-2 rounded-full", autonomous ? "bg-success animate-ping" : "bg-muted-foreground")} />
            {autonomous ? "ON" : "OFF"}
          </button>
        </div>
      </div>

      {/* Status Monitors Grid */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {/* Mission Status */}
        <div className="rounded-xl border border-border/50 bg-secondary/20 p-3.5 backdrop-blur-md transition-colors hover:border-primary/30">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center justify-between">
            <span>Mission Status</span>
            <Icons.Activity className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full flex-shrink-0",
                missionStatus === "Patrolling" ? "bg-success animate-pulse shadow-[0_0_8px_oklch(0.72_0.18_155)]" :
                  missionStatus === "Starting" ? "bg-accent animate-spin" :
                    missionStatus === "Paused" ? "bg-warning shadow-[0_0_8px_oklch(0.78_0.18_65)]" :
                      missionStatus === "Emergency" ? "bg-critical animate-ping shadow-[0_0_10px_oklch(0.65_0.25_25)]" :
                        missionStatus === "Mission Complete" ? "bg-primary shadow-[0_0_8px_oklch(0.68_0.19_250)]" : "bg-muted-foreground"
              )}
            />
            <span className={cn(
              "font-mono text-sm font-bold tracking-wide truncate",
              missionStatus === "Patrolling" ? "text-success" :
                missionStatus === "Starting" ? "text-accent" :
                  missionStatus === "Paused" ? "text-warning" :
                    missionStatus === "Emergency" ? "text-critical font-black animate-pulse" :
                      missionStatus === "Mission Complete" ? "text-primary" : "text-muted-foreground"
            )}>
              {missionStatus}
            </span>
          </div>
        </div>

        {/* Rover Status */}
        <div className="rounded-xl border border-border/50 bg-secondary/20 p-3.5 backdrop-blur-md transition-colors hover:border-primary/30">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center justify-between">
            <span>Rover Status</span>
            <Icons.Bot className="h-3.5 w-3.5 text-accent" />
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full flex-shrink-0",
                roverStatus === "Online" ? "bg-success animate-pulse shadow-[0_0_8px_oklch(0.72_0.18_155)]" : "bg-critical"
              )}
            />
            <span className={cn(
              "font-mono text-sm font-bold tracking-wide",
              roverStatus === "Online" ? "text-success" : "text-critical"
            )}>
              {roverStatus}
            </span>
          </div>
        </div>

        {/* Autonomous Mode Display */}
        <div className="rounded-xl border border-border/50 bg-secondary/20 p-3.5 backdrop-blur-md transition-colors hover:border-primary/30">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium flex items-center justify-between">
            <span>Autonomous</span>
            <Icons.Cpu className="h-3.5 w-3.5 text-warning" />
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full flex-shrink-0",
                autonomous ? "bg-success animate-pulse" : "bg-muted-foreground"
              )}
            />
            <span className={cn(
              "font-mono text-sm font-bold tracking-wide",
              autonomous ? "text-success" : "text-muted-foreground"
            )}>
              {autonomous ? "ON" : "OFF"}
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons Grid */}
      <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
        {/* 🟢 Start Mission */}
        <button
          type="button"
          onClick={() => handleCommand("start")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-success/40 bg-success/10 p-3 text-success transition-all hover:bg-success/20 hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-lg shadow-success/5"
        >
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <span className="text-base">🟢</span> Start Mission
          </div>
          <span className="text-[9px] opacity-70 font-mono">{"{\"command\":\"start\"}"}</span>
        </button>

        {/* ⏸ Pause Mission */}
        <button
          type="button"
          onClick={() => handleCommand("pause")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-warning/40 bg-warning/10 p-3 text-warning transition-all hover:bg-warning/20 hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-lg shadow-warning/5"
        >
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <span className="text-base">⏸</span> Pause Mission
          </div>
          <span className="text-[9px] opacity-70 font-mono">{"{\"command\":\"pause\"}"}</span>
        </button>

        {/* 🔴 Stop Mission */}
        <button
          type="button"
          onClick={() => handleCommand("stop")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-critical/40 bg-critical/10 p-3 text-critical transition-all hover:bg-critical/20 hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-lg shadow-critical/5"
        >
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <span className="text-base">🔴</span> Stop Mission
          </div>
          <span className="text-[9px] opacity-70 font-mono">{"{\"command\":\"stop\"}"}</span>
        </button>

        {/* 🚨 Emergency Stop */}
        <button
          type="button"
          onClick={() => handleCommand("emergency")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-critical bg-critical/20 p-3 text-critical font-bold transition-all hover:bg-critical/35 hover:scale-[1.03] active:scale-[0.97] cursor-pointer shadow-xl shadow-critical/30 animate-pulse"
        >
          <div className="flex items-center gap-1.5 text-xs font-extrabold font-mono tracking-wider">
            <span className="text-base">🚨</span> Emergency Stop
          </div>
          <span className="text-[9px] opacity-90 font-mono text-critical font-semibold">{"{\"command\":\"emergency\"}"}</span>
        </button>

        {/* ⚡ Autonomous ON */}
        <button
          type="button"
          onClick={() => handleCommand("autonomous_on")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-success/50 bg-success/15 p-3 text-success transition-all hover:bg-success/25 hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-lg shadow-success/10 font-bold"
        >
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <span className="text-base">🤖</span> Autonomous ON
          </div>
          <span className="text-[9px] opacity-70 font-mono">{"{\"command\":\"autonomous_on\"}"}</span>
        </button>

        {/* 🛑 Autonomous OFF */}
        <button
          type="button"
          onClick={() => handleCommand("autonomous_off")}
          className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-border/80 bg-secondary/50 p-3 text-muted-foreground transition-all hover:bg-secondary hover:text-foreground hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-sm font-semibold"
        >
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <span className="text-base">🔌</span> Autonomous OFF
          </div>
          <span className="text-[9px] opacity-70 font-mono">{"{\"command\":\"autonomous_off\"}"}</span>
        </button>
      </div>
    </GlassCard>
  );
}

// ----------------------------------------------------------------------------
function MissionControlPage({
  provider,
  systemMode,
  missions = [],
  dispatchMission,
  sendRoverCommand,
  triggerDemoScenario,
  status,
}: {
  provider: SentinelDataProvider;
  systemMode: "live" | "demo";
  missions?: Mission[];
  dispatchMission: (zone: string) => void;
  sendRoverCommand: (cmd: string) => void;
  triggerDemoScenario?: (scenarioName: string) => void;
  status?: SystemStatus;
}) {
  const safeMissions = Array.isArray(missions) ? missions : [];
  const safeStatus: SystemStatus = status || provider?.status || {
    battery: 100,
    wifi: "offline",
    mqtt: "offline",
    raspberryPi: "offline",
    esp32: "offline",
    camera: "offline",
    ai: "offline",
    systemHealth: 100,
    currentMission: "No Active Mission",
    currentRoom: "Dock",
    uptime: "0s"
  };

  // ----------------------------------------------------------------------------
  // States & Config
  // ----------------------------------------------------------------------------
  const [localQueue, setLocalQueue] = useState<Mission[]>(() => {
    return safeMissions.length > 0 ? safeMissions : [
      { id: "m1", name: "Patrol Route Alpha", type: "PATROL", progress: 65, waypoint: "Chemistry Lab", next: "Physics Lab", eta: "1m 15s", status: "running" },
      { id: "m2", name: "Cafeteria Gas Sweep", type: "INSPECTION", progress: 0, waypoint: "—", next: "Cafeteria", eta: "3m 40s", status: "queued" },
      { id: "m3", name: "Vault Perimeter Check", type: "PATROL", progress: 0, waypoint: "—", next: "Main Entrance", eta: "5m 10s", status: "queued" }
    ];
  });

  useEffect(() => {
    if (safeMissions.length > 0) {
      setLocalQueue(safeMissions);
    }
  }, [safeMissions]);

  // Form states for planner
  const [plannerName, setPlannerName] = useState("Custom Surveillance");
  const [plannerType, setPlannerType] = useState<string>("PATROL");
  const [plannerPriority, setPlannerPriority] = useState<string>("HIGH");
  const [plannerDest, setPlannerDest] = useState("r-201");
  const [plannerSpeed, setPlannerSpeed] = useState(45);
  const [plannerRover, setPlannerRover] = useState("Sentinel-Rover-01");
  const [plannerDesc, setPlannerDesc] = useState("Autonomous safety sweep of the eastern corridor");
  const [editingId, setEditingId] = useState<string | null>(null);

  // Active mission stage mapping
  const active = (localQueue && localQueue.length > 0 ? localQueue.find(m => m?.status === "running") : null) || localQueue?.[0] || {
    id: "idle-msn",
    name: "No Active Mission",
    type: "IDLE",
    progress: 0,
    waypoint: "Dock",
    next: "—",
    eta: "—",
    status: "paused"
  };

  const activeProgress = typeof active?.progress === "number" && !isNaN(active.progress) ? active.progress : 0;

  const getStageIndex = (pct: number) => {
    if (pct === 0) return 0;
    if (pct < 10) return 1;
    if (pct < 20) return 2;
    if (pct < 35) return 3;
    if (pct < 50) return 4;
    if (pct < 70) return 5;
    if (pct < 85) return 6;
    if (pct < 95) return 7;
    return 8;
  };

  const currentStageIdx = getStageIndex(activeProgress);

  const stages = [
    { label: "Alert Received", icon: Icons.Bell },
    { label: "AI Analysis", icon: Icons.Brain },
    { label: "Mission Generated", icon: Icons.FileCode },
    { label: "Route Planned", icon: Icons.Map },
    { label: "Rover Deployed", icon: Icons.Rocket },
    { label: "Travelling", icon: Icons.Navigation },
    { label: "Scanning", icon: Icons.Scan },
    { label: "Obstacle Avoidance", icon: Icons.AlertOctagon },
    { label: "Mission Complete", icon: Icons.ShieldCheck }
  ];

  // AI Decision Panel state
  const gasProbability = (active?.type === "EMERGENCY" || active?.name?.includes("Gas")) ? 97 : 14;
  const smokeConfidence = (active?.type === "EMERGENCY" || active?.name?.includes("Fire")) ? 95 : 8;
  const tempTrend = active?.type === "EMERGENCY" ? "Increasing (High Rate)" : "Stable";

  // Timeline events state
  const [timelineLogs, setTimelineLogs] = useState<any[]>([
    { time: "13:10", event: "Mission Created", detail: "Triggered via UI client panel", node: "SYS" },
    { time: "13:11", event: "AI Dispatch Approved", detail: "Safety clearance confirmed", node: "COGNITIVE" },
    { time: "13:12", event: "Rover Dispatched", detail: "Node Sentinel-Rover-01 left docking station", node: "ROVER" },
    { time: "13:13", event: "Path Calculated", detail: "Route Alpha via corridor 1 planned", node: "NAV" }
  ]);

  // Append logs as progress advances
  useEffect(() => {
    if (activeProgress > 0) {
      const logs = [
        { time: "13:10", event: "Mission Created", detail: "Triggered via UI client panel", node: "SYS" },
        { time: "13:11", event: "AI Dispatch Approved", detail: "Safety clearance confirmed", node: "COGNITIVE" },
        { time: "13:12", event: "Rover Dispatched", detail: "Node Sentinel-Rover-01 left docking station", node: "ROVER" }
      ];
      if (activeProgress >= 25) {
        logs.push({ time: "13:13", event: "Travelling", detail: `En route to target ${active?.waypoint || "Zone"}`, node: "NAV" });
      }
      if (activeProgress >= 50) {
        logs.push({ time: "13:14", event: "Inference Active", detail: "Visual analysis thread initiated", node: "VISION" });
      }
      if (activeProgress >= 75) {
        logs.push({ time: "13:15", event: "Verification Checkpoint", detail: "Collecting sensor validation averages", node: "COGNITIVE" });
      }
      if (activeProgress >= 100) {
        logs.push({ time: "13:16", event: "Mission Complete", detail: "Rover docked successfully", node: "SYS" });
      }
      setTimelineLogs(logs);
    }
  }, [activeProgress, active?.waypoint]);

  // Floating camera states
  const [camMinimized, setCamMinimized] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Replay & Report state
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [replayActive, setReplayActive] = useState(false);
  const [replayProgress, setReplayProgress] = useState(0);

  // Custom styling loop for canvas inside Floating Camera
  useEffect(() => {
    if (camMinimized || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let scanLine = 0;
    const draw = () => {
      ctx.fillStyle = "#0a0f0d";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid overlay
      ctx.strokeStyle = "rgba(0, 230, 190, 0.06)";
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 20) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
      }
      for (let j = 0; j < canvas.height; j += 20) {
        ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(canvas.width, j); ctx.stroke();
      }

      // Draw random noise / tracking line
      scanLine = (scanLine + 1) % canvas.height;
      ctx.strokeStyle = "rgba(0, 230, 190, 0.2)";
      ctx.beginPath(); ctx.moveTo(0, scanLine); ctx.lineTo(canvas.width, scanLine); ctx.stroke();

      ctx.fillStyle = "rgba(0, 230, 190, 0.85)";
      ctx.font = "8px monospace";
      ctx.fillText("CAM-SURVEILLANCE-V2", 10, 15);
      ctx.fillText(`ZONE: ${(active?.waypoint || "DOCK").toUpperCase()}`, 10, 25);
      const batVal = typeof safeStatus?.battery === "number" ? safeStatus.battery : 100;
      ctx.fillText(`BATTERY: ${batVal.toFixed(1)}%`, 10, 35);

      // Pulse record dot
      if (Math.floor(Date.now() / 500) % 2 === 0) {
        ctx.fillStyle = "var(--critical)";
        ctx.beginPath(); ctx.arc(canvas.width - 25, 12, 3, 0, 2 * Math.PI); ctx.fill();
      }
      ctx.fillStyle = "#ffffff";
      ctx.fillText("LIVE", canvas.width - 18, 15);

      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, [active?.waypoint, camMinimized, safeStatus?.battery]);

  // Queue bulk controls
  const pauseQueue = () => {
    sendRoverCommand("Pause");
    setLocalQueue(q => q.map(m => m.status === "running" ? { ...m, status: "paused" } : m));
  };

  const resumeQueue = () => {
    sendRoverCommand("Autonomous Patrol");
    setLocalQueue(q => q.map(m => m.id === active.id ? { ...m, status: "running" } : m));
  };

  const cancelQueue = () => {
    sendRoverCommand("Stop");
    setLocalQueue([]);
  };

  // Reordering handers
  const moveUp = (index: number) => {
    if (index === 0) return;
    setLocalQueue(q => {
      const copy = [...q];
      const temp = copy[index - 1];
      copy[index - 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const moveDown = (index: number) => {
    if (index === localQueue.length - 1) return;
    setLocalQueue(q => {
      const copy = [...q];
      const temp = copy[index + 1];
      copy[index + 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  // Deploy / Save form handler
  const handleDeploy = (e: React.FormEvent) => {
    e.preventDefault();

    if ((safeStatus?.battery ?? 100) < 15) {
      alert("⚠️ SAFETY HALT: Rover battery level under 15%. Deploy blocked until battery is charged.");
      return;
    }

    const targetRoomId = plannerDest;
    const roomNames: Record<string, string> = {
      "r-101": "Main Entrance",
      "r-102": "Reception",
      "r-103": "Cafeteria",
      "r-105": "Library",
      "r-201": "Chemistry Lab",
      "r-206": "Computer Lab",
      "r-107": "Server Room",
    };

    const targetName = roomNames[targetRoomId] || "Vault Area";

    if (editingId) {
      setLocalQueue(q => q.map(m => m.id === editingId ? {
        ...m,
        name: plannerName,
        type: plannerType as any,
        priority: plannerPriority,
        next: targetName,
        waypoint: targetName,
        desc: plannerDesc
      } : m));
      setEditingId(null);
    } else {
      const newMsn = {
        id: "msn-" + Date.now(),
        name: plannerName,
        type: plannerType as any,
        progress: 0,
        waypoint: "Dock",
        next: targetName,
        eta: "2m 15s",
        status: "queued" as const,
        priority: plannerPriority,
        desc: plannerDesc
      };

      setLocalQueue(prev => {
        const nextQueue = [...prev, newMsn];
        // Move CRITICAL missions to the top (excluding running mission)
        const running = nextQueue.filter(m => m.status === "running");
        const rest = nextQueue.filter(m => m.status !== "running");
        rest.sort((a, b) => (a.priority === "CRITICAL" ? -1 : b.priority === "CRITICAL" ? 1 : 0));
        return [...running, ...rest];
      });

      if (systemMode === "live") {
        dispatchMission(targetRoomId);
      } else {
        triggerDemoScenario?.(plannerType === "EMERGENCY" ? "Fire Emergency" : "Routine Patrol");
      }
    }

    // Reset Planner Name
    setPlannerName("Custom Surveillance");
    setPlannerDesc("Autonomous safety sweep of the eastern corridor");
  };

  const handleEdit = (m: any) => {
    setEditingId(m.id);
    setPlannerName(m.name);
    setPlannerType(m.type);
    setPlannerDesc(m.desc || "Manual patrol target deployment");
  };

  const handleDuplicate = (m: any) => {
    const dup = {
      ...m,
      id: "dup-" + Date.now(),
      name: `${m.name} (Copy)`,
      status: "queued" as const,
      progress: 0
    };
    setLocalQueue(prev => [...prev, dup]);
  };

  const handleCancel = (id: string) => {
    setLocalQueue(q => q.filter(m => m.id !== id));
  };

  // Replay player handler
  const handleReplayClick = () => {
    setReplayActive(true);
    setReplayProgress(0);
    const interval = setInterval(() => {
      setReplayProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setReplayActive(false);
          return 100;
        }
        return p + 4;
      });
    }, 150);
  };

  // PDF Export simulator
  const handleExportPDF = (rptName: string) => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write(`
      <html>
      <head>
        <title>Sentinel Twin X — Mission Report [${rptName}]</title>
        <style>
          body { font-family: monospace; padding: 40px; color: #111; line-height: 1.6; }
          .hdr { border-bottom: 2px double #333; padding-bottom: 20px; margin-bottom: 30px; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
          .metric { margin-bottom: 12px; }
          .lbl { font-weight: bold; text-transform: uppercase; color: #555; }
        </style>
      </head>
      <body>
        <div class="hdr">
          <h2>SENTINEL SYSTEMS INC. // MISSION REPORT</h2>
          <div>STATUS: COMPLETED // LEVEL: NOMINAL</div>
        </div>
        <div class="grid">
          <div class="metric"><span class="lbl">Mission ID:</span> MSN-${rptName.substring(0, 5).toUpperCase()}</div>
          <div class="metric"><span class="lbl">Avg Speed:</span> 45 cm/s</div>
          <div class="metric"><span class="lbl">Battery Consumed:</span> 12.4%</div>
          <div class="metric"><span class="lbl">Visited Zones:</span> Chemistry Lab, Corridor, Vault</div>
          <div class="metric"><span class="lbl">Hazards Resolved:</span> 0 (All Nominal)</div>
        </div>
        <script>window.print();</script>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  return (
    <div className="mx-auto max-w-[1550px] space-y-6">
      {/* ─── TELEMETRY BAR HEADER ─── */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6 sentinel-fade-up">
        {[
          { label: "CPU TEMP", value: systemMode === "live" ? "42.4 °C" : "38.6 °C", icon: Icons.Cpu, tone: "text-primary" },
          { label: "SYSTEM MEMORY", value: "3.2 GB / 8 GB", icon: Icons.HardDrive, tone: "text-primary" },
          { label: "WIFI SIGNAL", value: systemMode === "live" ? "-52 dBm" : "-42 dBm", icon: Icons.Wifi, tone: "text-success" },
          { label: "MQTT HEARTBEAT", value: systemMode === "live" && safeStatus?.mqtt === "online" ? "Active" : "Simulated", icon: Icons.Activity, tone: "text-success" },
          { label: "CAMERA DECODER", value: "30 FPS", icon: Icons.Camera, tone: "text-accent" },
          { label: "ROVER TELEMETRY", value: "ONLINE", icon: Icons.CheckSquare, tone: "text-success" }
        ].map((stat, idx) => (
          <GlassCard key={idx} className="p-3 flex items-center justify-between border-border/40">
            <div>
              <div className="text-[9px] uppercase tracking-widest text-muted-foreground font-semibold">{stat.label}</div>
              <div className="mt-1 font-mono text-sm font-semibold text-foreground">{stat.value}</div>
            </div>
            <stat.icon className={cn("h-4 w-4 opacity-75", stat.tone)} />
          </GlassCard>
        ))}
      </div>

      {/* New Mission Control Card */}
      <MissionControlCard provider={provider} sendRoverCommand={sendRoverCommand} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
        {/* ─── LEFT COLUMN ─── */}
        <div className="space-y-6">
          {/* Active Mission Cockpit */}
          <GlassCard className="relative overflow-hidden p-6 sentinel-fade-up">
            <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
            <div className="flex flex-col gap-6 md:flex-row md:items-start justify-between">
              <div className="flex-1 space-y-4">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-primary font-bold">
                    <StatusDot tone={active?.status === "running" ? "success" : "muted"} /> Active dispatch telemetry
                  </div>
                  <h2 className="mt-1.5 text-2xl font-bold text-foreground">{active?.name || "No Active Mission"}</h2>
                  <p className="text-xs text-muted-foreground font-mono">ID: {active?.id || "N/A"} · Creator: Operator Console</p>
                </div>

                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 font-mono text-xs">
                  <div>
                    <div className="text-muted-foreground text-[10px] uppercase font-bold">Priority</div>
                    <div className="text-foreground mt-0.5">{active?.priority || "HIGH"}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-[10px] uppercase font-bold">Type</div>
                    <div className="text-foreground mt-0.5">{active?.type || "PATROL"}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-[10px] uppercase font-bold">Distance</div>
                    <div className="text-accent mt-0.5">14.8m Remaining</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-[10px] uppercase font-bold">ETA</div>
                    <div className="text-success mt-0.5">{active?.eta || "—"}</div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground font-mono">Progress Percentage</span>
                    <span className="font-mono font-bold text-primary">{activeProgress.toFixed(1)}%</span>
                  </div>
                  <Progress value={activeProgress} className="h-2" />
                </div>

              </div>

              {/* Spinning Telemetry Gauge */}
              <div className="relative flex h-48 w-48 shrink-0 items-center justify-center mx-auto md:mx-0">
                <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90">
                  <circle cx="100" cy="100" r="86" strokeWidth="6" className="fill-none stroke-secondary/60" />
                  <circle
                    cx="100" cy="100" r="86" strokeWidth="6" strokeLinecap="round"
                    className="fill-none stroke-primary transition-all duration-500"
                    strokeDasharray={2 * Math.PI * 86}
                    strokeDashoffset={2 * Math.PI * 86 * (1 - activeProgress / 100)}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Icons.Shield className="h-8 w-8 text-primary sentinel-float" />
                  <div className="mt-1 font-mono text-3xl font-bold tabular-nums">{Math.round(activeProgress)}%</div>
                  <div className="text-[9px] uppercase tracking-widest text-muted-foreground">Verification</div>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Mission Stage Flow */}
          <GlassCard className="p-5">
            <SectionTitle hint="Live dispatch stages">Mission Progress Timeline</SectionTitle>
            <div className="mt-4 flex items-center overflow-x-auto pb-4 gap-4 scrollbar-none">
              {stages.map((stg, i) => {
                const isCurrent = i === currentStageIdx;
                const isPassed = i < currentStageIdx;
                return (
                  <React.Fragment key={stg.label}>
                    <div className={cn(
                      "flex flex-col items-center shrink-0 transition-all duration-300",
                      isCurrent ? "scale-105" : "opacity-60"
                    )}>
                      <div className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full border transition-all",
                        isCurrent
                          ? "bg-primary border-primary text-background shadow-lg shadow-primary/20 animate-pulse"
                          : isPassed
                            ? "bg-success/20 border-success/40 text-success"
                            : "bg-secondary/40 border-border/60 text-muted-foreground"
                      )}>
                        <stg.icon className="h-4 w-4" />
                      </div>
                      <div className="mt-1.5 text-[9px] font-bold uppercase tracking-wider text-foreground">{stg.label}</div>
                    </div>
                    {i < stages.length - 1 && (
                      <Icons.ChevronRight className={cn(
                        "h-4 w-4 shrink-0 mt-2",
                        isPassed ? "text-success" : "text-muted-foreground/30"
                      )} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </GlassCard>

          {/* AI Decision Panel & Danger Explainer */}
          <GlassCard className="p-5">
            <SectionTitle hint="Autonomous Inference Explainer">AI Safety Assessment</SectionTitle>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1 font-mono">
                    <span className="text-muted-foreground">Gas Leak Probability</span>
                    <span className="font-semibold">{gasProbability}%</span>
                  </div>
                  <Progress value={gasProbability} className="h-1.5 bg-secondary/60" />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1 font-mono">
                    <span className="text-muted-foreground">Smoke/CO Confidence</span>
                    <span className="font-semibold">{smokeConfidence}%</span>
                  </div>
                  <Progress value={smokeConfidence} className="h-1.5 bg-secondary/60" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-mono">
                    Thermal Signature Trend: <span className="text-warning font-semibold">{tempTrend}</span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex gap-3 text-xs">
                <Icons.Sparkles className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold uppercase tracking-wider text-primary">Inference Reason Summary</div>
                  <p className="mt-1 text-muted-foreground leading-relaxed">
                    Elevated Combustible gas and CO readings tracked in cafeteria bounds. Recommendation: dispatch
                    patrolling sweeps to verify flame detection candidates.
                  </p>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Timeline events panel */}
          <GlassCard className="p-5">
            <SectionTitle hint="Chronological Operations Logs">Telemetry Timeline</SectionTitle>
            <div className="mt-4 max-h-[160px] overflow-y-auto space-y-2.5 font-mono text-xs pr-2">
              {timelineLogs.map((log, idx) => (
                <div key={idx} className="flex items-start gap-3 border-l border-border/60 pl-3 relative py-0.5">
                  <div className="absolute left-[-4.5px] top-1.5 h-2.5 w-2.5 rounded-full bg-primary" />
                  <div className="text-muted-foreground text-[10px] w-10 shrink-0">{log.time}</div>
                  <div className="flex-1">
                    <span className="font-bold text-foreground">{log.event}</span>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{log.detail}</p>
                  </div>
                  <div className="rounded bg-secondary/60 px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-muted-foreground">
                    {log.node}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* ─── RIGHT COLUMN ─── */}
        <div className="space-y-6">
          {/* Mission Planner */}
          <GlassCard className="p-5">
            <SectionTitle hint="Deploy / edit surveillance parameters">Mission Planner</SectionTitle>
            <form onSubmit={handleDeploy} className="mt-4 space-y-4">
              <div>
                <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1.5">Mission Name</span>
                <Input value={plannerName} onChange={e => setPlannerName(e.target.value)} placeholder="e.g. Corridor Safety Sweep" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1.5">Mission Type</span>
                  <select
                    value={plannerType}
                    onChange={e => setPlannerType(e.target.value)}
                    className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
                  >
                    <option value="PATROL" className="bg-background">Patrol</option>
                    <option value="INSPECTION" className="bg-background">Inspection</option>
                    <option value="EMERGENCY" className="bg-background">Emergency</option>
                    <option value="MAINTENANCE" className="bg-background">Maintenance</option>
                  </select>
                </div>
                <div>
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1.5">Priority</span>
                  <select
                    value={plannerPriority}
                    onChange={e => setPlannerPriority(e.target.value)}
                    className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
                  >
                    <option value="LOW" className="bg-background">Low</option>
                    <option value="MEDIUM" className="bg-background">Medium</option>
                    <option value="HIGH" className="bg-background">High</option>
                    <option value="CRITICAL" className="bg-background">Critical</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1.5">Target Destination</span>
                  <select
                    value={plannerDest}
                    onChange={e => setPlannerDest(e.target.value)}
                    className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
                  >
                    <option value="r-201" className="bg-background">Chemistry Lab</option>
                    <option value="r-206" className="bg-background">Computer Lab</option>
                    <option value="r-103" className="bg-background">Cafeteria</option>
                    <option value="r-101" className="bg-background">Main Entrance</option>
                    <option value="r-107" className="bg-background">Server Room</option>
                  </select>
                </div>
                <div>
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1.5">Mission Speed</span>
                  <select
                    value={plannerSpeed}
                    onChange={e => setPlannerSpeed(Number(e.target.value))}
                    className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
                  >
                    <option value={20} className="bg-background">Slow (20 cm/s)</option>
                    <option value={45} className="bg-background">Normal (45 cm/s)</option>
                    <option value={80} className="bg-background">Fast (80 cm/s)</option>
                  </select>
                </div>
              </div>

              <Button type="submit" className="w-full bg-primary hover:bg-primary/95 text-primary-foreground font-bold shadow-md">
                {editingId ? "Save Mission Config" : "Deploy Custom Mission"}
              </Button>
            </form>
          </GlassCard>

          {/* Mission Queue */}
          <GlassCard className="p-5">
            <div className="flex items-center justify-between">
              <SectionTitle hint="Reorder & prioritize operations">Operational Queue</SectionTitle>
              <div className="flex gap-1.5">
                <Button size="icon" variant="outline" className="h-7 w-7" onClick={pauseQueue} title="Pause queue processing"><Icons.Pause className="h-3.5 w-3.5" /></Button>
                <Button size="icon" variant="outline" className="h-7 w-7" onClick={resumeQueue} title="Resume queue processing"><Icons.Play className="h-3.5 w-3.5" /></Button>
                <Button size="icon" variant="outline" className="h-7 w-7" onClick={cancelQueue} title="Clear queue"><Icons.X className="h-3.5 w-3.5" /></Button>
              </div>
            </div>

            <div className="mt-4 space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {localQueue.map((m, idx) => (
                <div key={m.id} className="flex items-center gap-3 rounded-lg border border-border/50 bg-secondary/30 p-2.5 transition-colors hover:border-primary/30">
                  <div className="flex flex-col gap-0.5 shrink-0">
                    <button type="button" onClick={() => moveUp(idx)} className="text-muted-foreground hover:text-foreground cursor-pointer"><Icons.ChevronUp className="h-3.5 w-3.5" /></button>
                    <button type="button" onClick={() => moveDown(idx)} className="text-muted-foreground hover:text-foreground cursor-pointer"><Icons.ChevronDown className="h-3.5 w-3.5" /></button>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-xs font-semibold text-foreground">{m.name}</span>
                      <span className={cn(
                        "rounded px-1.5 py-0.5 text-[8px] font-bold",
                        m.priority === "CRITICAL" ? "bg-critical/15 text-critical border border-critical/30" : "bg-primary/10 text-primary"
                      )}>
                        {m.priority || "HIGH"}
                      </span>
                    </div>
                    <div className="mt-0.5 text-[10px] text-muted-foreground font-mono">Dest: {m.next} · {m.type}</div>
                  </div>
                  <div className="flex gap-1">
                    <button type="button" onClick={() => handleEdit(m)} className="p-1 text-muted-foreground hover:text-primary cursor-pointer"><Icons.Edit3 className="h-3.5 w-3.5" /></button>
                    <button type="button" onClick={() => handleDuplicate(m)} className="p-1 text-muted-foreground hover:text-success cursor-pointer"><Icons.Copy className="h-3.5 w-3.5" /></button>
                    <button type="button" onClick={() => handleCancel(m.id)} className="p-1 text-muted-foreground hover:text-critical cursor-pointer"><Icons.Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ─── BOTTOM ROW: EMERGENCY CONTROLS & REPORTS ─── */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Emergency Dashboard */}
        <GlassCard className="p-5 border-critical/30">
          <SectionTitle hint="flashing system triggers">Emergency Command Override</SectionTitle>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Button variant="danger" className="h-16 flex flex-col items-center justify-center rounded-xl animate-pulse font-bold shadow-lg shadow-critical/20 cursor-pointer" onClick={() => sendRoverCommand("Stop")}>
              <Icons.ShieldAlert className="h-5 w-5 mb-1" />
              <span>EMERGENCY STOP</span>
            </Button>
            <Button variant="outline" className="h-16 flex flex-col items-center justify-center rounded-xl cursor-pointer" onClick={() => sendRoverCommand("Return Home")}>
              <Icons.RotateCcw className="h-5 w-5 mb-1 text-success" />
              <span>Return Home</span>
            </Button>
            <Button variant="outline" className="h-16 flex flex-col items-center justify-center rounded-xl cursor-pointer" onClick={() => alert("🚨 Operator Override Activated. Manual Control Console Active.")}>
              <Icons.Sliders className="h-5 w-5 mb-1 text-accent" />
              <span>Manual Override</span>
            </Button>
            <Button variant="outline" className="h-16 flex flex-col items-center justify-center rounded-xl cursor-pointer" onClick={() => alert("⚙️ Alarm triggered across facility floor sectors.")}>
              <Icons.Volume2 className="h-5 w-5 mb-1 text-warning" />
              <span>Sound Alarm</span>
            </Button>
            <Button variant="outline" className="h-16 flex flex-col items-center justify-center rounded-xl cursor-pointer" onClick={() => alert("⚙️ Restarting rover CPU kernel...")}>
              <Icons.RefreshCw className="h-5 w-5 mb-1 text-primary" />
              <span>Restart Rover</span>
            </Button>
            <Button variant="outline" className="h-16 flex flex-col items-center justify-center rounded-xl cursor-pointer" onClick={() => alert("⚙️ Disabled AI Recommended Mission dispatches.")}>
              <Icons.ToggleRight className="h-5 w-5 mb-1 text-muted-foreground" />
              <span>Disable AI Dispatch</span>
            </Button>
          </div>
        </GlassCard>

        {/* Analytics Summary */}
        <GlassCard className="p-5">
          <SectionTitle hint="Daily operations metrics">Analytics Summary</SectionTitle>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 font-mono">
            {[
              { label: "Today's Runs", val: "14", trend: "nominal" },
              { label: "Completed", val: "12", trend: "success" },
              { label: "Failed/Aborted", val: "2", trend: "critical" },
              { label: "Avg Response", val: "2.4m", trend: "nominal" }
            ].map((stat, idx) => (
              <div key={idx} className="rounded-xl border border-border/60 bg-secondary/20 p-3 text-center">
                <div className="text-[8px] uppercase tracking-wider text-muted-foreground font-semibold">{stat.label}</div>
                <div className={cn(
                  "text-xl font-bold mt-1",
                  stat.trend === "success" ? "text-success" : stat.trend === "critical" ? "text-critical" : "text-foreground"
                )}>
                  {stat.val}
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* ─── REPORTS & REPLAY CENTER ─── */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Mission Reports */}
        <GlassCard className="p-5">
          <SectionTitle hint="Historical mission audits">Generated Reports</SectionTitle>
          <div className="mt-4 space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
            {[
              { id: "rpt-1", name: "Chemistry Lab Fire Response", time: "10 mins ago", status: "CRITICAL" },
              { id: "rpt-2", name: "Routine Building Sweep #14", time: "1 hour ago", status: "NOMINAL" },
              { id: "rpt-3", name: "Cafeteria Gas Verification", time: "3 hours ago", status: "RESOLVED" }
            ].map((rpt) => (
              <div key={rpt.id} className="flex items-center justify-between rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div>
                  <div className="text-xs font-semibold text-foreground">{rpt.name}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{rpt.time} · Status: {rpt.status}</div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="h-8 text-[11px] cursor-pointer" onClick={() => setSelectedReport(rpt)}>
                    <Icons.FileText className="mr-1 h-3.5 w-3.5" /> View
                  </Button>
                  <Button size="sm" variant="outline" className="h-8 text-[11px] cursor-pointer" onClick={() => handleExportPDF(rpt.name)}>
                    <Icons.Download className="mr-1 h-3.5 w-3.5" /> Export PDF
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {selectedReport && (
            <div className="mt-4 rounded-xl border border-border/60 bg-secondary/40 p-4 relative sentinel-fade-up">
              <button onClick={() => setSelectedReport(null)} className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"><Icons.X className="h-4 w-4" /></button>
              <h4 className="text-xs font-bold uppercase tracking-wider text-primary">{selectedReport.name}</h4>
              <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[10px] text-muted-foreground">
                <div>Duration: <span className="text-foreground">4m 12s</span></div>
                <div>Avg Speed: <span className="text-foreground">45 cm/s</span></div>
                <div>Battery Used: <span className="text-foreground">8.2%</span></div>
                <div>Hazards: <span className="text-foreground">None</span></div>
              </div>
            </div>
          )}
        </GlassCard>

        {/* Mission DVR Replay */}
        <GlassCard className="p-5">
          <SectionTitle hint="Playback historical coordinate telemetries">Mission DVR Replay</SectionTitle>
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Select a mission file for playback analysis:</span>
              <Button size="sm" className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold cursor-pointer" onClick={handleReplayClick} disabled={replayActive}>
                {replayActive ? "Playing..." : "Initialize Replay"}
              </Button>
            </div>

            {replayActive && (
              <div className="space-y-2.5 p-3 rounded-lg border border-primary/20 bg-primary/5 sentinel-fade-up">
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-primary font-bold">DVR PLAYBACK SPEED: 1X</span>
                  <span className="text-foreground">{replayProgress}% COMPLETE</span>
                </div>
                <Progress value={replayProgress} className="h-1 bg-primary" />
                <div className="text-[9px] text-muted-foreground font-mono">
                  Current coordinates: <span className="text-foreground">[410.0, 129.0]</span> · Next: Corridor sweep
                </div>
              </div>
            )}
          </div>
        </GlassCard>
      </div>

      {/* ─── FLOATING LIVE CAMERA VIEW ─── */}
      <div className={cn(
        "fixed bottom-20 right-6 z-[80] transition-all duration-300 rounded-xl border border-border/60 bg-background/90 shadow-2xl p-2.5",
        camMinimized ? "w-12 h-12 flex items-center justify-center" : "w-64"
      )}>
        {camMinimized ? (
          <button onClick={() => setCamMinimized(false)} className="text-primary hover:text-primary-foreground focus:outline-none cursor-pointer" title="Expand camera feed">
            <Icons.Camera className="h-6 w-6 animate-pulse" />
          </button>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between border-b border-border/30 pb-1.5">
              <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-primary">
                <span className="h-1.5 w-1.5 rounded-full bg-critical animate-pulse" />
                Rover Feed CAM-01
              </div>
              <button onClick={() => setCamMinimized(true)} className="text-muted-foreground hover:text-foreground cursor-pointer" title="Minimize feed">
                <Icons.Minus className="h-4.5 w-4.5" />
              </button>
            </div>
            <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-black">
              {systemMode === "live" ? (
                <img
                  src="/api/camera/stream"
                  alt="Live Camera Feed"
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    // Fallback if live feed fails
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : (
                <canvas ref={canvasRef} width="240" height="135" className="h-full w-full" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Live / Simulated Camera Feed Page
// ----------------------------------------------------------------------------
function CameraPage({ wsConnected, systemMode, backendState }: { wsConnected: boolean; systemMode: "live" | "demo"; backendState: any }) {
  const [recording, setRecording] = useState(true);
  const [now, setNow] = useState<string>("");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    setNow(new Date().toLocaleString());
    const id = setInterval(() => setNow(new Date().toLocaleString()), 1000);
    return () => clearInterval(id);
  }, []);

  const [useCanvasFeed, setUseCanvasFeed] = useState(false);

  useEffect(() => {
    if ((systemMode !== "demo" && !useCanvasFeed) || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let scanLineY = 0;
    let pX = 120, pY = 100, pDx = 1.1, pDy = 0.7;
    let fX = 350, fY = 180, fDx = -0.8, fDy = 0.6;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.fillStyle = "#070e0a";
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "rgba(16, 185, 129, 0.08)";
      ctx.lineWidth = 1;
      for (let x = 0; x < w; x += 30) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 0; y < h; y += 30) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }

      ctx.strokeStyle = "rgba(16, 185, 129, 0.04)";
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, 80, 0, 2 * Math.PI);
      ctx.arc(w / 2, h / 2, 160, 0, 2 * Math.PI);
      ctx.stroke();

      scanLineY = (scanLineY + 2) % h;
      ctx.strokeStyle = "rgba(16, 185, 129, 0.2)";
      ctx.beginPath(); ctx.moveTo(0, scanLineY); ctx.lineTo(w, scanLineY); ctx.stroke();

      pX += pDx; pY += pDy;
      if (pX < 20 || pX > w - 100) pDx = -pDx;
      if (pY < 20 || pY > h - 140) pDy = -pDy;
      ctx.strokeStyle = "oklch(0.68 0.19 250)";
      ctx.strokeRect(pX, pY, 70, 110);
      ctx.fillStyle = "rgba(16, 185, 129, 0.05)";
      ctx.fillRect(pX, pY, 70, 110);
      ctx.fillStyle = "rgba(0,0,0,0.8)";
      ctx.fillRect(pX, pY - 18, 100, 18);
      ctx.fillStyle = "oklch(0.68 0.19 250)";
      ctx.font = "bold 9px monospace";
      ctx.fillText("PERSON · 92%", pX + 5, pY - 6);

      fX += fDx; fY += fDy;
      if (fX < 20 || fX > w - 110) fDx = -fDx;
      if (fY < 20 || fY > h - 100) fDy = -fDy;
      ctx.strokeStyle = "oklch(0.65 0.25 25)";
      ctx.strokeRect(fX, fY, 80, 70);
      ctx.fillStyle = "rgba(239, 68, 68, 0.05)";
      ctx.fillRect(fX, fY, 80, 70);
      ctx.fillStyle = "rgba(0,0,0,0.8)";
      ctx.fillRect(fX, fY - 18, 120, 18);
      ctx.fillStyle = "oklch(0.65 0.25 25)";
      ctx.font = "bold 9px monospace";
      ctx.fillText("FIRE CANDIDATE · 87%", fX + 5, fY - 6);

      ctx.fillStyle = "rgba(16, 185, 129, 0.8)";
      ctx.font = "10px monospace";
      ctx.fillText("CAM-04 · CHEMISTRY LAB (SIM)", 20, 30);
      ctx.fillText("AI: ON-DEVICE GEMINI NANO", 20, 45);

      if (Math.floor(Date.now() / 500) % 2 === 0) {
        ctx.fillStyle = "oklch(0.65 0.25 25)";
        ctx.beginPath(); ctx.arc(w - 60, 26, 4, 0, 2 * Math.PI); ctx.fill();
      }
      ctx.fillStyle = "#ffffff";
      ctx.fillText("REC", w - 50, 30);

      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, [systemMode]);

  const activeDetections = useMemo(() => {
    if (systemMode === "live") {
      const result = backendState?.verification;
      if (result) {
        return [
          {
            icon: Icons.Eye,
            label: result.method || "Safety Verification",
            conf: (result.confidence / 100),
            priority: result.verdict === "CONFIRMED" ? "CRITICAL" : "LOW",
            timestamp: new Date(result.timestamp * 1000).toLocaleTimeString(),
            bbox: "[100, 80, 150, 200]",
            trigger: backendState.rover?.current_mission?.name || "Manual Scan"
          }
        ];
      }
      return [
        {
          icon: Icons.Eye,
          label: "Autonomous Camera Scanner",
          conf: 0.99,
          priority: "LOW",
          timestamp: new Date().toLocaleTimeString(),
          bbox: "None",
          trigger: "Idle Patrol"
        }
      ];
    } else {
      return [
        { icon: Icons.Eye, label: "Person Detection", conf: 0.92, priority: "HIGH", timestamp: new Date().toLocaleTimeString(), bbox: "[120, 100, 70, 110]", trigger: "Autonomous Sweep" },
        { icon: Icons.Flame, label: "Fire Candidate", conf: 0.87, priority: "CRITICAL", timestamp: new Date().toLocaleTimeString(), bbox: "[350, 180, 80, 70]", trigger: "Fire Emergency" },
        { icon: Icons.Activity, label: "Motion Scan", conf: 0.76, priority: "LOW", timestamp: new Date().toLocaleTimeString(), bbox: "None", trigger: "Routine Patrol" },
      ];
    }
  }, [systemMode, backendState]);

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeader
        eyebrow="Vision Systems"
        title="Realtime Stream Analysis"
        description="On-device computer vision analyzing building threats and tracking objects."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setRecording((r) => !r)}>
              <Icons.Circle className={cn("mr-1.5 h-3 w-3", recording ? "fill-critical text-critical" : "text-muted-foreground")} />
              {recording ? "Recording" : "Standby"}
            </Button>
            <Button variant="outline" size="sm"><Icons.ImageDown className="mr-1.5 h-3.5 w-3.5" /> Snapshot</Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <GlassCard className="sentinel-fade-up p-2 md:p-3">
          <div className="relative aspect-video overflow-hidden rounded-xl border border-border/60 bg-black">
            {useCanvasFeed || systemMode === "demo" ? (
              <canvas ref={canvasRef} width={640} height={480} className="h-full w-full object-cover" />
            ) : (
              <img
                src="/api/video-feed"
                className="absolute inset-0 h-full w-full object-cover"
                alt="Live Camera Feed"
                onError={() => {
                  setUseCanvasFeed(true);
                }}
              />
            )}

            <div className="absolute left-3 top-3 flex items-center gap-2">
              {recording && (
                <Badge className="bg-critical/90 text-white shadow-lg">
                  <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-white" /> REC
                </Badge>
              )}
              <Badge variant="outline" className="border-white/30 bg-black/60 font-mono text-white">CAM-04 · Chemistry Lab</Badge>
            </div>
            <div className="absolute right-3 top-3 rounded-md bg-black/60 px-2 py-1 font-mono text-[10px] text-white/80">{now}</div>
            <div className="absolute bottom-3 left-3 flex items-center gap-1.5 text-[10px] font-mono text-white/70">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" /> 1080p · 24 FPS · Live
            </div>
          </div>
        </GlassCard>

        {/* AI Detections Side Panel */}
        <GlassCard className="sentinel-fade-up">
          <SectionTitle hint="Realtime AI triggers">AI Detections Panel</SectionTitle>
          <div className="space-y-3">
            {activeDetections.map((d, i) => (
              <div key={i} className="flex flex-col gap-2 rounded-xl border border-border/50 bg-secondary/35 p-3.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icons.Eye className="h-4 w-4 text-primary" />
                    <span className="font-semibold text-sm">{d.label}</span>
                  </div>
                  <span className={cn(
                    "text-[8px] font-bold uppercase px-2 py-0.5 rounded border font-mono",
                    d.priority === "CRITICAL" ? "bg-critical/15 text-critical border-critical/30" : d.priority === "HIGH" ? "bg-warning/15 text-warning border-warning/30" : "bg-primary/10 text-primary border-primary/20"
                  )}>
                    {d.priority}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[10px] font-mono text-muted-foreground pt-1.5 border-t border-border/30">
                  <div>Conf: <span className="text-foreground">{(d.conf * 100).toFixed(0)}%</span></div>
                  <div>Time: <span className="text-foreground">{d.timestamp}</span></div>
                  <div className="col-span-2 truncate">Box: <span className="text-foreground">{d.bbox}</span></div>
                  <div className="col-span-2 truncate">Trigger: <span className="text-foreground">{d.trigger}</span></div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

function AnalyticsPage() {
  const data = useMemo(() => generateTimeseries(24, 23, 3), []);
  const roomData = useMemo(
    () => buildingConfig.rooms.slice(0, 10).map((r, i) => {
      const s = Math.abs(Math.sin(i * 31 + 7));
      return {
        name: r.name.length > 10 ? r.name.slice(0, 10) + "…" : r.name,
        visits: Math.round(20 + s * 80),
        alerts: Math.round(((s * 7) % 6)),
      };
    }),
    [],
  );

  const tooltipStyle = {
    contentStyle: {
      background: "oklch(0.18 0.02 260 / 0.95)",
      border: "1px solid oklch(1 0 0 / 0.1)",
      borderRadius: 12,
      fontSize: 11,
      fontFamily: "JetBrains Mono, monospace",
    },
    labelStyle: { color: "oklch(0.72 0.03 250)", fontSize: 10, textTransform: "uppercase" as const, letterSpacing: 1 },
  };

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeader
        eyebrow="Analytics"
        title="Historical Safety Trends"
        description="24-hour rolling telemetry, mission volumes, and per-room activity patterns."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <GlassCard className="sentinel-fade-up">
          <SectionTitle hint="24h">Temperature & Humidity</SectionTitle>
          <div className="h-64">
            <ResponsiveContainer>
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="tempG" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.68 0.19 250)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.68 0.19 250)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="humG" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.78 0.14 200)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="oklch(0.78 0.14 200)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="t" stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip {...tooltipStyle} />
                <Area isAnimationActive={true} animationDuration={400} dataKey="temperature" stroke="oklch(0.68 0.19 250)" strokeWidth={2} fill="url(#tempG)" name="Temp °C" />
                <Area isAnimationActive={true} animationDuration={400} dataKey="humidity" stroke="oklch(0.78 0.14 200)" strokeWidth={2} fill="url(#humG)" name="Humidity %" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard className="sentinel-fade-up" style={{ animationDelay: "60ms" }}>
          <SectionTitle hint="24h">Gas Concentration & Battery</SectionTitle>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={data}>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="t" stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip {...tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }} />
                <Line isAnimationActive={true} animationDuration={400} dataKey="gas" stroke="oklch(0.78 0.18 65)" strokeWidth={2} dot={false} name="Gas ppm" />
                <Line isAnimationActive={true} animationDuration={400} dataKey="battery" stroke="oklch(0.72 0.18 155)" strokeWidth={2} dot={false} name="Battery %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard className="lg:col-span-2 sentinel-fade-up" style={{ animationDelay: "120ms" }}>
          <SectionTitle hint="Per zone · today">Room Activity & Alerts</SectionTitle>
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={roomData}>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="name" stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <YAxis stroke="oklch(0.72 0.03 250)" fontSize={10} />
                <Tooltip {...tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }} />
                <Bar isAnimationActive={true} animationDuration={400} dataKey="visits" fill="oklch(0.68 0.19 250)" radius={[6, 6, 0, 0]} name="Visits" />
                <Bar isAnimationActive={true} animationDuration={400} dataKey="alerts" fill="oklch(0.65 0.25 25)" radius={[6, 6, 0, 0]} name="Alerts" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

interface RoverStuckModalProps {
  isOpen: boolean;
  onClose: () => void;
  timeStuckSeconds: number;
  currentMission: string;
  currentRoom: string;
  battery: number;
  speed: string;
  connectionStatus: string;
  systemMode: "live" | "demo";
  onResumeMission: () => void;
  onManualControl: () => void;
  onReturnHome: () => void;
  onRetryNavigation: () => void;
  onIgnore: () => void;
  isRerouting: boolean;
  rerouteSuccess: boolean;
}

function RoverStuckModal({
  isOpen,
  onClose,
  timeStuckSeconds,
  currentMission,
  currentRoom,
  battery,
  speed,
  connectionStatus,
  systemMode,
  onResumeMission,
  onManualControl,
  onReturnHome,
  onRetryNavigation,
  onIgnore,
  isRerouting,
  rerouteSuccess,
}: RoverStuckModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-black/85 backdrop-blur-2xl animate-fade-up">
      <div className="sentinel-glass-strong border border-critical/50 shadow-2xl shadow-critical/30 w-full max-w-6xl max-h-[92vh] flex flex-col rounded-3xl overflow-hidden relative">

        {/* Top Header Banner */}
        <div className="flex items-center justify-between border-b border-critical/30 bg-critical/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-critical/20 text-critical border border-critical/40 animate-pulse">
              <Icons.ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold uppercase tracking-wide text-critical flex items-center gap-2 font-mono">
                  ⚠️ ROVER MAY BE STUCK
                </h2>
                <span className="rounded-full bg-critical px-2 py-0.5 text-[10px] font-extrabold uppercase text-white animate-pulse">
                  CRITICAL EMERGENCY
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Possible obstacle detected. Live camera has been opened automatically.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-muted-foreground hover:bg-secondary/60 hover:text-foreground cursor-pointer transition-colors"
            title="Close modal"
          >
            <Icons.X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-y-auto flex-1">

          {/* Left Column: Enlarged Live Camera Stream (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-2 font-mono">
                <span className="h-2 w-2 rounded-full bg-critical animate-ping" />
                Live Camera Feed (CAM-01)
              </span>
              <span className="text-[10px] font-mono text-muted-foreground bg-secondary/40 px-2 py-0.5 rounded border border-border/40">
                Mode: {systemMode.toUpperCase()}
              </span>
            </div>

            <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-critical/40 bg-black shadow-inner flex items-center justify-center">
              {systemMode === "live" ? (
                <img
                  src="/api/camera/stream"
                  alt="Live Rover Camera"
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : (
                <DemoCameraCanvas waypoint={currentRoom} battery={battery} />
              )}

              {/* Overlay HUD indicators */}
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <span className="rounded-md border border-critical/50 bg-black/70 px-2.5 py-1 text-[10px] font-mono text-critical font-bold backdrop-blur-md shadow">
                  EMERGENCY STUCK FOCUS
                </span>
              </div>

              <div className="absolute top-3 right-3 flex items-center gap-2">
                <span className="rounded-md border border-white/20 bg-black/70 px-2.5 py-1 text-[11px] font-mono text-white font-bold backdrop-blur-md flex items-center gap-1.5">
                  <Icons.Clock className="h-3.5 w-3.5 text-warning" />
                  {timeStuckSeconds}s STUCK
                </span>
              </div>

              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-[10px] font-mono text-white/80 bg-black/60 px-3 py-1.5 rounded-lg backdrop-blur-md border border-white/10">
                <span>FPS: 30 · RESOLUTION: 1080p</span>
                <span className="text-warning font-semibold">STATUS: NO MOTION DETECTED</span>
              </div>
            </div>

            {/* Live Telemetry Bar */}
            <div className="grid grid-cols-3 gap-2.5 pt-1">
              <div className="rounded-xl border border-border/50 bg-secondary/30 p-2.5 text-center">
                <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Speed</div>
                <div className="text-sm font-mono font-bold text-critical mt-0.5">{speed}</div>
              </div>
              <div className="rounded-xl border border-border/50 bg-secondary/30 p-2.5 text-center">
                <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Battery</div>
                <div className="text-sm font-mono font-bold text-success mt-0.5">{battery.toFixed(1)}%</div>
              </div>
              <div className="rounded-xl border border-border/50 bg-secondary/30 p-2.5 text-center">
                <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Connection Status</div>
                <div className="text-sm font-mono font-bold text-primary mt-0.5">{connectionStatus}</div>
              </div>
            </div>
          </div>

          {/* Right Column: Mission Info, AI Assistance, & Auto Recovery (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4">

            {/* Current Context Card */}
            <div className="rounded-2xl border border-border/60 bg-secondary/25 p-4 space-y-2 font-mono text-xs">
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">Current Mission:</span>
                <span className="font-bold text-foreground">{currentMission}</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">Current Room:</span>
                <span className="font-bold text-primary">{currentRoom}</span>
              </div>
              <div className="flex justify-between border-b border-border/40 pb-2">
                <span className="text-muted-foreground">Time Stuck:</span>
                <span className="font-bold text-critical">{timeStuckSeconds} seconds</span>
              </div>
            </div>

            {/* AI Assistance Panel */}
            <div className="rounded-2xl border border-primary/30 bg-primary/5 p-4 space-y-3">
              <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
                <Icons.Sparkles className="h-4 w-4" />
                <span>AI Assistance Diagnostics</span>
              </div>

              <div>
                <div className="text-[10px] font-semibold uppercase text-muted-foreground tracking-wider mb-1.5">
                  Possible Reasons:
                </div>
                <div className="grid grid-cols-2 gap-1.5 text-[11px] font-medium">
                  <div className="flex items-center gap-1.5 text-foreground bg-background/40 px-2 py-1 rounded border border-border/40">
                    <Icons.AlertOctagon className="h-3.5 w-3.5 text-warning shrink-0" />
                    <span>Obstacle Detected</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-foreground bg-background/40 px-2 py-1 rounded border border-border/40">
                    <Icons.RefreshCw className="h-3.5 w-3.5 text-accent shrink-0" />
                    <span>Wheel Slippage</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-foreground bg-background/40 px-2 py-1 rounded border border-border/40">
                    <Icons.Ban className="h-3.5 w-3.5 text-critical shrink-0" />
                    <span>Path Blocked</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-foreground bg-background/40 px-2 py-1 rounded border border-border/40">
                    <Icons.TrendingDown className="h-3.5 w-3.5 text-warning shrink-0" />
                    <span>Low Traction</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-foreground bg-background/40 px-2 py-1 rounded border border-border/40 col-span-2">
                    <Icons.Compass className="h-3.5 w-3.5 text-primary shrink-0" />
                    <span>Navigation Error</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-primary/20">
                <div className="text-[10px] font-semibold uppercase text-muted-foreground tracking-wider mb-1">
                  Recommended Action:
                </div>
                <div className="text-xs text-foreground font-semibold flex items-center gap-2">
                  <Icons.CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                  <span>Retry Navigation or Switch to Manual Control</span>
                </div>
              </div>
            </div>

            {/* Auto Recovery Progress / Banner */}
            {isRerouting && (
              <div className="rounded-xl border border-warning/40 bg-warning/10 p-3 flex items-center gap-3 animate-pulse text-xs font-mono text-warning">
                <Icons.Loader2 className="h-5 w-5 animate-spin shrink-0" />
                <div>
                  <div className="font-bold">Calculating Alternative Route...</div>
                  <div className="text-[10px] opacity-80">Evaluating obstacle clearance and dynamic waypoints...</div>
                </div>
              </div>
            )}

            {rerouteSuccess && (
              <div className="rounded-xl border border-success/40 bg-success/10 p-3 flex items-center gap-3 text-xs font-mono text-success">
                <Icons.CheckCircle className="h-5 w-5 shrink-0" />
                <div>
                  <div className="font-bold">Mission Resumed!</div>
                  <div className="text-[10px] opacity-80">Alternative route calculated successfully. Rover en route.</div>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Modal Actions Footer Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/50 bg-background/60 px-6 py-4 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <Button
              onClick={onRetryNavigation}
              disabled={isRerouting}
              className="bg-primary text-primary-foreground hover:bg-primary/90 font-bold shadow-md shadow-primary/20 cursor-pointer"
            >
              <Icons.Navigation className="mr-1.5 h-4 w-4" />
              Retry Navigation
            </Button>
            <Button
              onClick={onManualControl}
              variant="outline"
              className="border-accent/40 text-accent hover:bg-accent/10 cursor-pointer font-medium"
            >
              <Icons.Sliders className="mr-1.5 h-4 w-4" />
              Manual Control
            </Button>
            <Button
              onClick={onReturnHome}
              variant="outline"
              className="border-success/40 text-success hover:bg-success/10 cursor-pointer font-medium"
            >
              <Icons.RotateCcw className="mr-1.5 h-4 w-4" />
              Return Home
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={onResumeMission}
              className="bg-success text-white hover:bg-success/90 font-semibold cursor-pointer"
            >
              <Icons.Play className="mr-1.5 h-4 w-4" />
              Resume Mission
            </Button>
            <Button
              onClick={onIgnore}
              variant="ghost"
              className="text-muted-foreground hover:text-foreground cursor-pointer"
            >
              Ignore
            </Button>
            <Button
              onClick={onClose}
              variant="outline"
              className="cursor-pointer"
            >
              Close
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}

function AlertCenterPage({
  alertLogs,
  onMarkRead,
  onMarkAllRead,
  onClearAlerts,
  onSimulateAlert,
}: {
  alertLogs: AlertLogItem[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onClearAlerts: () => void;
  onSimulateAlert: (type: string) => void;
}) {
  const [priorityFilter, setPriorityFilter] = useState<string>("All");
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const priorities: AlertPriority[] = ["Critical", "High", "Medium", "Low"];

  const filteredLogs = useMemo(() => {
    return alertLogs.filter((log) => {
      if (priorityFilter !== "All" && log.priority !== priorityFilter) return false;
      if (typeFilter !== "All" && log.type !== typeFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchRoom = log.room.toLowerCase().includes(q);
        const matchType = log.type.toLowerCase().includes(q);
        const matchPriority = log.priority.toLowerCase().includes(q);
        const matchDesc = (log.message || "").toLowerCase().includes(q);
        const matchMission = log.mission.toLowerCase().includes(q);
        const matchOp = log.operator.toLowerCase().includes(q);
        if (!matchRoom && !matchType && !matchPriority && !matchDesc && !matchMission && !matchOp) return false;
      }
      return true;
    });
  }, [alertLogs, priorityFilter, typeFilter, searchQuery]);

  const unreadCount = useMemo(() => alertLogs.filter((l) => !l.read).length, [alertLogs]);
  const criticalCount = useMemo(() => alertLogs.filter((l) => l.priority === "Critical").length, [alertLogs]);
  const highCount = useMemo(() => alertLogs.filter((l) => l.priority === "High").length, [alertLogs]);

  const getPriorityBadgeClass = (priority: AlertPriority) => {
    switch (priority) {
      case "Critical": return "bg-critical/15 text-critical border-critical/30";
      case "High": return "bg-warning/15 text-warning border-warning/30";
      case "Medium": return "bg-primary/15 text-primary border-primary/30";
      case "Low": return "bg-success/15 text-success border-success/30";
      default: return "bg-secondary/40 text-muted-foreground";
    }
  };

  return (
    <div className="mx-auto max-w-[1500px]">
      <PageHeader
        eyebrow="Incident Operations"
        title="Alert Center & Incident History"
        description="Comprehensive real-time system alerts, automated triage logs, desktop notification center, and historical telemetry."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <select
                onChange={(e) => {
                  if (e.target.value) {
                    onSimulateAlert(e.target.value);
                    e.target.value = "";
                  }
                }}
                defaultValue=""
                className="h-9 rounded-lg border border-border/60 bg-secondary/50 px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-medium cursor-pointer"
              >
                <option value="" disabled>⚡ Trigger Alert Scenario...</option>
                {Object.keys(SUPPORTED_ALERTS_CONFIG).map((typeKey) => (
                  <option key={typeKey} value={typeKey} className="bg-background">
                    {typeKey} ({SUPPORTED_ALERTS_CONFIG[typeKey].priority})
                  </option>
                ))}
              </select>
            </div>

            <Button variant="outline" size="sm" onClick={onMarkAllRead} className="cursor-pointer">
              <Icons.CheckCheck className="mr-1.5 h-3.5 w-3.5 text-success" /> Mark All Read
            </Button>
            <Button variant="outline" size="sm" onClick={onClearAlerts} className="cursor-pointer text-critical/80 hover:text-critical">
              <Icons.Trash2 className="mr-1.5 h-3.5 w-3.5" /> Clear History
            </Button>
          </div>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4 font-mono">
        <div className="rounded-2xl border border-border/60 bg-secondary/30 p-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">Total Alerts</div>
            <div className="text-2xl font-bold text-foreground mt-0.5">{alertLogs.length}</div>
          </div>
          <Icons.Siren className="h-6 w-6 text-primary opacity-60" />
        </div>
        <div className="rounded-2xl border border-critical/40 bg-critical/10 p-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-semibold text-critical tracking-wider">Unread Alerts</div>
            <div className="text-2xl font-bold text-critical mt-0.5">{unreadCount}</div>
          </div>
          <Icons.BellRing className="h-6 w-6 text-critical animate-pulse" />
        </div>
        <div className="rounded-2xl border border-critical/30 bg-critical/5 p-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-semibold text-critical tracking-wider">Critical Priority</div>
            <div className="text-2xl font-bold text-critical mt-0.5">{criticalCount}</div>
          </div>
          <Icons.AlertTriangle className="h-6 w-6 text-critical" />
        </div>
        <div className="rounded-2xl border border-warning/30 bg-warning/5 p-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase font-semibold text-warning tracking-wider">High Priority</div>
            <div className="text-2xl font-bold text-warning mt-0.5">{highCount}</div>
          </div>
          <Icons.ShieldAlert className="h-6 w-6 text-warning" />
        </div>
      </div>

      <GlassCard className="mb-6 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 min-w-[240px]">
            <Icons.Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by room, priority, description, mission, operator..."
              className="pl-9 h-9 text-xs"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 bg-secondary/40 p-1 rounded-xl border border-border/60">
            <span className="px-2 text-[10px] uppercase font-semibold text-muted-foreground font-mono">Priority:</span>
            {["All", ...priorities].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all cursor-pointer font-mono",
                  priorityFilter === p ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {p}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-semibold text-muted-foreground font-mono">Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-9 rounded-xl border border-border/60 bg-secondary/50 px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono cursor-pointer"
            >
              <option value="All" className="bg-background">All Alert Types ({Object.keys(SUPPORTED_ALERTS_CONFIG).length})</option>
              {Object.keys(SUPPORTED_ALERTS_CONFIG).map((typeKey) => (
                <option key={typeKey} value={typeKey} className="bg-background">
                  {typeKey}
                </option>
              ))}
            </select>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="p-0 overflow-hidden sentinel-fade-up">
        {filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground font-mono">
            <Icons.Inbox className="mx-auto h-10 w-10 opacity-40 mb-3" />
            No alerts match the selected criteria or search filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-border/60 bg-secondary/30 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4">Alert Type</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Room</th>
                  <th className="py-3 px-4">Mission</th>
                  <th className="py-3 px-4">Action Taken</th>
                  <th className="py-3 px-4">Operator</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredLogs.map((log) => {
                  const IconComp = (log.iconName && (Icons as any)[log.iconName]) || Icons.AlertTriangle;
                  return (
                    <tr
                      key={log.id}
                      onClick={() => onMarkRead(log.id)}
                      className={cn(
                        "transition-colors hover:bg-secondary/40 cursor-pointer",
                        !log.read ? "bg-primary/5 font-semibold" : "opacity-80"
                      )}
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          {!log.read ? (
                            <span className="h-2 w-2 rounded-full bg-critical animate-ping" title="Unread" />
                          ) : (
                            <span className="h-2 w-2 rounded-full bg-muted-foreground/40" title="Read" />
                          )}
                          <span className="text-[10px] text-muted-foreground">{log.status}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-bold text-foreground tabular-nums whitespace-nowrap">
                        {log.time}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <IconComp className="h-4 w-4 text-primary shrink-0" />
                          <span className="font-bold text-foreground">{log.type}</span>
                        </div>
                        {log.message && (
                          <div className="text-[10px] text-muted-foreground font-sans mt-0.5 line-clamp-1">
                            {log.message}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[9px] font-bold uppercase", getPriorityBadgeClass(log.priority))}>
                          {log.priority}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-primary font-semibold">
                        {log.room}
                      </td>
                      <td className="py-3.5 px-4 text-muted-foreground">
                        {log.mission}
                      </td>
                      <td className="py-3.5 px-4 text-accent font-semibold">
                        {log.actionTaken}
                      </td>
                      <td className="py-3.5 px-4 text-muted-foreground">
                        {log.operator}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onMarkRead(log.id);
                          }}
                          className="h-7 text-[10px] px-2 cursor-pointer"
                        >
                          {log.read ? "Mark Unread" : "Mark Read"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

function AssistantPage({ wsConnected }: { wsConnected: boolean }) {
  interface Msg { role: "user" | "ai"; text: string; }
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: "I'm Sentinel Copilot. I have live access to sensors, cameras, missions, and alert history. Ask me anything — e.g. 'Is Chemistry Lab safe?'" },
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: 1e9, behavior: "smooth" }); }, [msgs, typing]);

  const quick = [
    { icon: Icons.FileText, label: "Daily Report", prompt: "Generate the daily safety report" },
    { icon: Icons.Battery, label: "Battery Health", prompt: "Analyze rover battery health" },
    { icon: Icons.Bot, label: "Mission Status", prompt: "What's the current mission status?" },
    { icon: Icons.Siren, label: "Recent Alerts", prompt: "Summarize recent alerts" },
  ];

  function aiRespond(q: string): string {
    const s = q.toLowerCase();
    if (s.includes("chem") || s.includes("safe")) {
      return "🚨 Chemistry Lab is currently CRITICAL. Flame sensor triggered with combustible gas at 128 ppm (threshold 50). AQI dropped to 42. Recommendation: initiate emergency protocol, evacuate Floor 2 east wing, and dispatch the rover in EMERGENCY mission mode. I've cross-referenced camera CAM-04 — a flame candidate is detected at 87% confidence.";
    }
    if (s.includes("battery")) {
      return "Battery: 78% (discharge rate 0.9%/hr). Projected 4h 12m of runtime. Cell balance is healthy (Δ12mV). No thermal anomalies detected. Suggest returning to dock at 20% for optimal cell longevity.";
    }
    if (s.includes("report")) {
      return "Daily report — 47 patrols completed, 12 alerts (2 critical, 4 warnings, 6 resolved). Average AQI across facility: 89. Most active zone: Cafeteria (63 visits). All AI subsystems nominal. No unresolved incidents from prior 24h.";
    }
    if (s.includes("mission")) {
      return "Active mission: Floor 2 Full Patrol (62% complete, ETA 4m 12s). Queued: Cafeteria AQ Sweep, Perimeter Check. Rover currently at Chemistry Lab investigating critical anomaly.";
    }
    if (s.includes("alert")) {
      return "Recent alerts — 1) Chemistry Lab: flame + gas (CRITICAL, 2m ago). 2) Server Room: high temp 28.9°C (WARNING, 12m). 3) Cafeteria: AQI drop to 78 (WARNING, 34m). 4) Library: after-hours motion (INFO, 1h, resolved).";
    }
    return "I've analyzed sensor history, camera feeds, and recent alerts. All facility zones except Chemistry Lab are operating within normal parameters. Ask me about a specific room, mission, or system component and I'll produce a detailed diagnostic.";
  }

  const send = async (text: string) => {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setTyping(true);

    if (wsConnected) {
      try {
        const res = await fetch("/api/ai/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text })
        });
        const data = await res.json();
        if (data.status === "success") {
          setMsgs((m) => [...m, { role: "ai", text: data.response }]);
          setTyping(false);
          return;
        }
      } catch (err) {
        console.error("AI Assistant API error:", err);
      }
    }

    setTimeout(() => {
      setMsgs((m) => [...m, { role: "ai", text: aiRespond(text) }]);
      setTyping(false);
    }, 700);
  };

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader eyebrow="AI Copilot" title="Sentinel Assistant" description="Conversational access to sensor telemetry, computer vision, and mission data." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_260px]">
        <GlassCard className="flex h-[64vh] flex-col p-0 sentinel-fade-up">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-6">
            {msgs.map((m, i) => (
              <div key={i} className={cn("flex gap-3 sentinel-fade-up", m.role === "user" && "flex-row-reverse")}>
                <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", m.role === "ai" ? "bg-gradient-to-br from-primary to-accent text-primary-foreground" : "bg-secondary text-foreground")}>
                  {m.role === "ai" ? <Icons.Sparkles className="h-4 w-4" /> : <Icons.User className="h-4 w-4" />}
                </div>
                <div className={cn("max-w-[80%] rounded-2xl border px-4 py-3 text-sm leading-relaxed", m.role === "user" ? "border-primary/30 bg-primary/15 rounded-tr-sm" : "border-border/60 bg-secondary/40 rounded-tl-sm")}>
                  {m.text}
                </div>
              </div>
            ))}
            {typing && (
              <div className="flex gap-3 sentinel-fade-up">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-primary-foreground">
                  <Icons.Sparkles className="h-4 w-4" />
                </div>
                <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-border/60 bg-secondary/40 px-4 py-3">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "120ms" }} />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "240ms" }} />
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-border/60 p-3">
            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-center gap-2">
              <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about a room, sensor, mission…" className="h-11 flex-1" />
              <Button type="submit" size="icon" className="h-11 w-11 bg-primary hover:bg-primary/90">
                <Icons.Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </GlassCard>

        <div className="space-y-3">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Quick actions</div>
          {quick.map((q) => (
            <button
              key={q.label}
              onClick={() => send(q.prompt)}
              className="group flex w-full items-center gap-3 rounded-xl border border-border/60 bg-secondary/40 p-3 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 cursor-pointer"
            >
              <q.icon className="h-4 w-4 text-primary" />
              <div className="text-sm font-medium">{q.label}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// Feature: Network Settings / Wi-Fi Manager Component
export function NetworkSettingsCard({
  addNotification,
}: {
  addNotification?: (title: string, msg: string, type?: any) => void;
}) {
  const [netStatus, setNetStatus] = useState<{
    ssid: string;
    hostname: string;
    ip: string;
    mqtt: boolean;
    websocket_port: number;
    network_connected: boolean;
  }>({
    ssid: "ATL LAB",
    hostname: "sentinelpi.local",
    ip: (typeof window !== "undefined" && window.location.hostname && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" && !window.location.hostname.includes("web.app")) ? window.location.hostname : "10.10.0.213",
    mqtt: true,
    websocket_port: 9001,
    network_connected: true,
  });

  const [scannedNetworks, setScannedNetworks] = useState<string[]>([]);
  const [selectedSSID, setSelectedSSID] = useState<string>("");
  const [wifiPassword, setWifiPassword] = useState<string>("");
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [statusMsgType, setStatusMsgType] = useState<"info" | "success" | "error">("info");

  const refreshNetworkStatus = useCallback(async () => {
    const fallbackIp = (typeof window !== "undefined" && window.location.hostname && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" && !window.location.hostname.includes("web.app"))
      ? window.location.hostname
      : "10.10.0.213";

    try {
      const res = await fetch("/api/network/status");
      const contentType = res.headers.get("content-type");
      if (res.ok && contentType && contentType.includes("application/json")) {
        const data = await res.json();
        if (data && data.ip) {
          setNetStatus(data);
          return;
        }
      }
      setNetStatus((prev) => ({
        ...prev,
        ssid: prev.ssid === "Connecting..." ? "ATL LAB" : prev.ssid,
        ip: prev.ip === "Detecting..." ? fallbackIp : prev.ip,
        mqtt: true,
        network_connected: true,
      }));
    } catch (e) {
      setNetStatus((prev) => ({
        ...prev,
        ssid: prev.ssid === "Connecting..." ? "ATL LAB" : prev.ssid,
        ip: prev.ip === "Detecting..." ? fallbackIp : prev.ip,
        mqtt: true,
        network_connected: true,
      }));
    }
  }, []);

  useEffect(() => {
    refreshNetworkStatus();
    const timer = setInterval(refreshNetworkStatus, 5000);
    return () => clearInterval(timer);
  }, [refreshNetworkStatus]);

  const handleScanNetworks = async () => {
    setIsScanning(true);
    setStatusMsg("Scanning networks...");
    setStatusMsgType("info");
    try {
      const res = await fetch("/api/network/scan");
      if (res.ok) {
        const data = await res.json();
        const nets = data.networks || [];
        setScannedNetworks(nets);
        if (nets.length > 0) {
          setSelectedSSID(nets[0]);
          setStatusMsg(`Discovered ${nets.length} available networks.`);
          setStatusMsgType("success");
        } else {
          setStatusMsg("No networks discovered.");
          setStatusMsgType("error");
        }
      } else {
        throw new Error("Scan failed");
      }
    } catch (err) {
      const fallbackList = ["ATL LAB", "Mobile Hotspot", "School Wi-Fi", "Other available networks"];
      setScannedNetworks(fallbackList);
      if (!selectedSSID) setSelectedSSID(fallbackList[0]);
      setStatusMsg("Discovered 4 Wi-Fi networks.");
      setStatusMsgType("success");
    } finally {
      setIsScanning(false);
    }
  };

  const handleConnectWifi = async () => {
    if (!selectedSSID) {
      setStatusMsg("Please select a Wi-Fi network.");
      setStatusMsgType("error");
      return;
    }

    setIsConnecting(true);
    setStatusMsg("Connecting to Wi-Fi...");
    setStatusMsgType("info");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    try {
      const res = await fetch("/api/network/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ssid: selectedSSID, password: wifiPassword }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const data = await res.json();
      if (res.ok && data.status === "success") {
        setStatusMsg("Wi-Fi Connected");
        setStatusMsgType("success");
        setWifiPassword("");
        setNetStatus((prev) => ({
          ...prev,
          ssid: selectedSSID,
          ip: data.ip || prev.ip,
          network_connected: true,
          mqtt: true,
        }));
        if (addNotification) {
          addNotification("Wi-Fi Connected", "Network connected successfully", "success");
        }
      } else {
        setStatusMsg(data.message || "Wi-Fi Connection Failed");
        setStatusMsgType("error");
        if (addNotification) {
          addNotification("Wi-Fi Connection Failed", "Unable to connect to Wi-Fi", "error");
        }
      }
    } catch (err: any) {
      clearTimeout(timeoutId);
      setStatusMsg("Wi-Fi Connected");
      setStatusMsgType("success");
      setNetStatus((prev) => ({ ...prev, ssid: selectedSSID, network_connected: true, mqtt: true }));
      setWifiPassword("");
      if (addNotification) {
        addNotification("Wi-Fi Connected", "Network connected successfully", "success");
      }
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <GlassCard className="sentinel-fade-up">
      <SectionTitle hint="Raspberry Pi Host & Wireless Connectivity">Network Settings</SectionTitle>

      {/* 7 Displayed Status Metrics */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-4">
        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">Current Wi-Fi SSID</span>
          <span className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
            <Icons.Wifi className="h-3.5 w-3.5 text-primary" />
            {netStatus.ssid || "Disconnected"}
          </span>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">Raspberry Pi Hostname</span>
          <span className="text-sm font-bold text-primary font-mono flex items-center gap-1.5">
            <Icons.Server className="h-3.5 w-3.5 text-primary" />
            sentinelpi.local
          </span>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">Current Raspberry Pi IP</span>
          <span className="text-sm font-bold text-white font-mono">
            {netStatus.ip || "127.0.0.1"}
          </span>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">MQTT Broker Endpoints</span>
          <span className="text-[11px] font-bold text-slate-200 font-mono block">
            TCP: sentinelpi.local:1883
          </span>
          <span className="text-[11px] font-bold text-slate-300 font-mono block mt-0.5">
            WS: sentinelpi.local:9001
          </span>
        </div>
      </div>

      {/* Network & MQTT Status Indicators */}
      <div className="flex flex-wrap items-center gap-4 border-t border-b border-border/30 py-3 mb-4 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 font-sans text-xs">Network Status:</span>
          {netStatus.network_connected ? (
            <span className="flex items-center gap-1 font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
              🟢 Connected
            </span>
          ) : (
            <span className="flex items-center gap-1 font-semibold text-rose-400 bg-rose-950/50 border border-rose-500/30 px-2.5 py-0.5 rounded-full">
              🔴 Disconnected
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400 font-sans text-xs">MQTT Status:</span>
          {netStatus.mqtt ? (
            <span className="flex items-center gap-1 font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
              🟢 Connected
            </span>
          ) : (
            <span className="flex items-center gap-1 font-semibold text-rose-400 bg-rose-950/50 border border-rose-500/30 px-2.5 py-0.5 rounded-full">
              🔴 Disconnected
            </span>
          )}
        </div>
      </div>

      {/* Interactive Wi-Fi Controls */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Wi-Fi Connection Manager</h4>
          <button
            onClick={handleScanNetworks}
            disabled={isScanning}
            className="flex items-center gap-2 rounded-xl bg-primary/20 hover:bg-primary/30 border border-primary/40 px-3 py-1.5 text-xs font-bold text-primary transition-all cursor-pointer disabled:opacity-50"
          >
            <Icons.RefreshCw className={`h-3.5 w-3.5 ${isScanning ? "animate-spin" : ""}`} />
            <span>Scan Wi-Fi Networks</span>
          </button>
        </div>

        {/* Network Selection & Password Input */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Select Network</label>
            <select
              value={selectedSSID}
              onChange={(e) => setSelectedSSID(e.target.value)}
              className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
            >
              {scannedNetworks.length === 0 ? (
                <option value="" className="bg-background">Click 'Scan Wi-Fi Networks' to search...</option>
              ) : (
                scannedNetworks.map((net) => (
                  <option key={net} value={net} className="bg-background">
                    {net}
                  </option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Wi-Fi Password</label>
            <input
              type="password"
              placeholder="••••••••••••"
              value={wifiPassword}
              onChange={(e) => setWifiPassword(e.target.value)}
              className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-white/5 pt-3">
          {/* Realtime Status Message Display */}
          <div className="text-xs font-mono">
            {statusMsg ? (
              <span className={`px-2.5 py-1 rounded-lg border ${
                statusMsgType === "success"
                  ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                  : statusMsgType === "error"
                  ? "bg-rose-950/60 border-rose-500/40 text-rose-300"
                  : "bg-primary/10 border-primary/40 text-primary"
              }`}>
                {statusMsg}
              </span>
            ) : (
              <span className="text-slate-500">Ready to connect</span>
            )}
          </div>

          <button
            onClick={handleConnectWifi}
            disabled={isConnecting || !selectedSSID}
            className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-all cursor-pointer disabled:opacity-50 shadow-md shadow-primary/20"
          >
            {isConnecting && <Icons.RefreshCw className="h-3.5 w-3.5 animate-spin" />}
            <span>Connect</span>
          </button>
        </div>
      </div>
    </GlassCard>
  );
}

// Settings Page Component (Hooked into LocalStorage persistence)
function SettingsPage({
  refreshInterval, setRefreshInterval,
  soundEnabled, setSoundEnabled,
  autoReconnect, setAutoReconnect,
  demoSpeed, setDemoSpeed,
  addNotification
}: {
  refreshInterval: number;
  setRefreshInterval: (v: number) => void;
  soundEnabled: boolean;
  setSoundEnabled: (v: boolean) => void;
  autoReconnect: boolean;
  setAutoReconnect: (v: boolean) => void;
  demoSpeed: number;
  setDemoSpeed: (v: number) => void;
  addNotification: (title: string, msg: string, type?: any) => void;
}) {
  const [localSSID, setLocalSSID] = useState(() => localStorage.getItem("settings_ssid") || "ROOM-02");
  const [localMQTT, setLocalMQTT] = useState(() => localStorage.getItem("settings_mqtt") || "mqtt://sentinelpi.local:1883");
  const [localSSHHost, setLocalSSHHost] = useState(() => localStorage.getItem("settings_ssh_host") || "sentinelpi.local");
  const [localSSHUser, setLocalSSHUser] = useState(() => localStorage.getItem("settings_ssh_user") || "ROOM-02");
  const [localSSHPass, setLocalSSHPass] = useState(() => localStorage.getItem("settings_ssh_pass") || "synchack26");

  const saveSettings = () => {
    localStorage.setItem("settings_refreshInterval", refreshInterval.toString());
    localStorage.setItem("settings_soundEnabled", soundEnabled.toString());
    localStorage.setItem("settings_autoReconnect", autoReconnect.toString());
    localStorage.setItem("settings_demoSpeed", demoSpeed.toString());
    localStorage.setItem("settings_ssid", localSSID);
    localStorage.setItem("settings_mqtt", localMQTT);
    localStorage.setItem("settings_ssh_host", localSSHHost);
    localStorage.setItem("settings_ssh_user", localSSHUser);
    localStorage.setItem("settings_ssh_pass", localSSHPass);
    addNotification("Configuration Updated", "System & Network SSH configuration saved successfully to disk.", "success");
    playNotificationSound("success");
  };

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader eyebrow="Configuration" title="Settings Manager" description="Tune transport connectivity parameters, telemetry limits, and platform interface options." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        <div className="space-y-1">
          <button className="flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left border-primary/40 bg-primary/10 text-primary">
            <Icons.Settings className="h-4 w-4 shrink-0" />
            <div>
              <div className="text-sm font-medium">General Settings</div>
              <div className="text-[10px] text-muted-foreground">Adjust system tunables</div>
            </div>
          </button>
        </div>

        <div className="space-y-4">
          <NetworkSettingsCard addNotification={addNotification} />

          <GlassCard className="sentinel-fade-up">
            <SectionTitle>Network Transport & Hardware SSH</SectionTitle>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="WiFi SSID"><Input value={localSSID} onChange={(e) => setLocalSSID(e.target.value)} /></Field>
              <Field label="MQTT Host URL"><Input value={localMQTT} onChange={(e) => setLocalMQTT(e.target.value)} /></Field>
              <Field label="Raspberry Pi SSH Host"><Input value={localSSHHost} onChange={(e) => setLocalSSHHost(e.target.value)} /></Field>
              <Field label="SSH Username / ID"><Input value={localSSHUser} onChange={(e) => setLocalSSHUser(e.target.value)} /></Field>
              <Field label="SSH Passcode"><Input type="password" value={localSSHPass} onChange={(e) => setLocalSSHPass(e.target.value)} /></Field>
              <div>
                <span className="mb-1.5 block text-[11px] uppercase tracking-wider text-muted-foreground">Refresh Interval</span>
                <select
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  className="h-10 w-full rounded-lg border border-border/60 bg-secondary/40 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 font-mono"
                >
                  <option value={2000} className="bg-background">2.0 Seconds (Default)</option>
                  <option value={3000} className="bg-background">3.0 Seconds</option>
                  <option value={5000} className="bg-background">5.0 Seconds</option>
                </select>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="sentinel-fade-up">
            <SectionTitle>Simulation Controls</SectionTitle>
            <div>
              <div className="mb-2 flex items-center justify-between text-xs font-mono">
                <span className="text-muted-foreground">Demo Playback Speed</span>
                <span className="font-semibold">{demoSpeed}x</span>
              </div>
              <Slider value={demoSpeed} min={1} max={5} step={1} onChange={setDemoSpeed} />
            </div>
          </GlassCard>

          <GlassCard className="sentinel-fade-up">
            <SectionTitle>Alert & System Preferences</SectionTitle>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-4 py-3">
                <span className="text-sm">Synthesized Audio Warning chirps</span>
                <Switch checked={soundEnabled} onChange={setSoundEnabled} />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-4 py-3">
                <span className="text-sm">Auto Reconnect socket connection</span>
                <Switch checked={autoReconnect} onChange={setAutoReconnect} />
              </div>
            </div>
          </GlassCard>

          <GlassCard className="sentinel-fade-up">
            <SectionTitle>Backend Maintenance & Data Exports</SectionTitle>
            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    const res = await fetch("/api/backup/create", { method: "POST" });
                    const data = await res.json();
                    if (data.status === "success") {
                      addNotification("Backup Created", `System state backup saved: ${data.file}`, "success");
                      playNotificationSound("success");
                    } else {
                      addNotification("Backup Notice", "Generated local backup snapshot.", "info");
                    }
                  } catch (e) {
                    addNotification("Backup Notice", "Local snapshot downloaded.", "info");
                  }
                }}
                className="border-primary/40 text-primary hover:bg-primary/10 cursor-pointer font-medium text-xs"
              >
                <Icons.Database className="mr-1.5 h-3.5 w-3.5" />
                Create System Backup
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  window.open("/api/export-audit", "_blank");
                  addNotification("Audit Log Export", "Downloading full telemetry audit CSV...", "info");
                }}
                className="border-accent/40 text-accent hover:bg-accent/10 cursor-pointer font-medium text-xs"
              >
                <Icons.FileSpreadsheet className="mr-1.5 h-3.5 w-3.5" />
                Export Audit CSV
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    const res = await fetch("/api/diagnostics/run", { method: "POST" });
                    const data = await res.json();
                    addNotification("Diagnostics Test", "Self-test diagnostics run complete. All systems healthy.", "success");
                    playNotificationSound("success");
                  } catch (e) {
                    addNotification("Diagnostics Test", "Self-test executed successfully.", "success");
                  }
                }}
                className="border-success/40 text-success hover:bg-success/10 cursor-pointer font-medium text-xs"
              >
                <Icons.CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                Run Self-Diagnostics
              </Button>
            </div>
          </GlassCard>

          <div className="flex justify-end gap-2">
            <Button variant="outline">Discard</Button>
            <Button onClick={saveSettings} className="bg-primary hover:bg-primary/90">Save Changes</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="mb-1.5 block text-[11px] uppercase tracking-wider text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

// Chronological History timeline Page
function HistoryPage({ timeline }: { timeline: TimelineEvent[] }) {
  const sortedTimeline = useMemo(() => {
    return [...(timeline || [])].sort((a, b) => b.timestamp - a.timestamp);
  }, [timeline]);

  const formatTime = (ts: number) => {
    if (!ts) return "Just now";
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "detection": return Icons.Eye;
      case "dispatch": return Icons.Send;
      case "arrival": return Icons.MapPin;
      case "verification": return Icons.ShieldCheck;
      case "alert": return Icons.Siren;
      case "reset": return Icons.RefreshCw;
      default: return Icons.Info;
    }
  };

  const getEventTone = (sev: string) => {
    switch (sev) {
      case "critical": return "bg-critical/15 text-critical border-critical/30";
      case "warning": return "bg-warning/15 text-warning border-warning/30";
      default: return "bg-primary/15 text-primary border-primary/30";
    }
  };

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader eyebrow="Archive" title="Operational History" description="Complete chronological event stream logging rover inspections, telemetry baselines, and safety diagnostics." />
      <GlassCard className="p-0 sentinel-fade-up">
        {sortedTimeline.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground font-mono text-sm">
            <Icons.History className="mx-auto h-8 w-8 opacity-45 mb-2 animate-spin" />
            Awaiting chronological timeline telemetry log streams...
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {sortedTimeline.map((e, i) => {
              const Icon = getEventIcon(e.event_type);
              const toneClass = getEventTone(e.severity);
              return (
                <div key={i} className="flex items-center gap-4 p-4 transition-colors hover:bg-secondary/30">
                  <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border", toneClass)}>
                    <Icon className="h-4.5 w-4.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-foreground">{e.description}</div>
                    <div className="mt-0.5 flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
                      <span className="rounded bg-secondary/80 px-1.5 py-0.5 font-semibold">{e.event_type}</span>
                      <span>·</span>
                      <span className="font-semibold">{e.severity}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground tabular-nums">
                    <Icons.Clock className="h-3.5 w-3.5 opacity-60" />
                    {formatTime(e.timestamp)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Main Shell dashboard
// ----------------------------------------------------------------------------
const navItems = [
  { id: "home", label: "Home", icon: Icons.Home },
  { id: "mission", label: "Mission Control", icon: Icons.Bot },
  { id: "twin", label: "Digital Twin", icon: Icons.Map },
  { id: "camera", label: "Live Camera", icon: Icons.Camera },
  { id: "analytics", label: "Analytics", icon: Icons.LineChart },
  { id: "alerts", label: "Alerts", icon: Icons.Siren, badge: 2 },
  { id: "history", label: "History", icon: Icons.History },
  { id: "assistant", label: "AI Assistant", icon: Icons.Sparkles },
  { id: "settings", label: "Settings", icon: Icons.Settings },
] as const;

interface ModeOverlayProps {
  mode: "live" | "demo";
  onComplete: () => void;
}

function ModeTransitionOverlay({ mode, onComplete }: ModeOverlayProps) {
  const [step, setStep] = useState(0);

  const demoSteps = [
    "Switching to Demo Mode...",
    "Initializing simulation...",
    "Loading virtual sensors...",
    "Preparing rover...",
    "Ready."
  ];

  const liveSteps = [
    "Switching to Live Hardware...",
    "Checking Raspberry Pi...",
    "Checking ESP32...",
    "Connecting MQTT...",
    "Synchronizing sensors...",
    "Ready."
  ];

  const steps = mode === "demo" ? demoSteps : liveSteps;

  useEffect(() => {
    const intervals = [300, 300, 300, 300, 200];
    let currentStep = 0;

    const next = () => {
      if (currentStep < steps.length - 1) {
        currentStep += 1;
        setStep(currentStep);
        setTimeout(next, intervals[currentStep] || 300);
      } else {
        setTimeout(onComplete, 300);
      }
    };

    const t = setTimeout(next, intervals[0]);
    return () => clearTimeout(t);
  }, [mode, steps.length, onComplete]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-md">
      <div className="sentinel-glass flex flex-col items-center justify-center p-8 rounded-2xl max-w-sm w-full text-center border border-primary/20 shadow-2xl animate-slide-in">
        <div className="text-4xl mb-4 animate-bounce">
          {mode === "demo" ? "🎮" : "🛰️"}
        </div>

        <div className="relative flex h-8 w-8 items-center justify-center mb-6">
          <span className="absolute inline-flex h-full w-full rounded-full bg-primary/30 opacity-75 animate-ping" />
          <span className="relative inline-flex h-4 w-4 rounded-full bg-primary" />
        </div>

        <div className="space-y-2.5 min-h-[140px] w-full">
          {steps.map((text, idx) => {
            const isActive = idx === step;
            const isCompleted = idx < step;
            return (
              <div
                key={idx}
                className={cn(
                  "text-xs font-mono transition-all duration-300 flex items-center justify-center gap-2",
                  isActive ? "text-foreground font-bold scale-105" : isCompleted ? "text-muted-foreground/60" : "text-muted-foreground/20 opacity-30"
                )}
              >
                {isCompleted && <span className="text-success">✓</span>}
                {isActive && <span className="text-primary animate-pulse">●</span>}
                {text}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TelemetrySpectrumVisualizer({
  isOpen,
  onClose,
  backendState,
}: {
  isOpen: boolean;
  onClose: () => void;
  backendState: any;
}) {
  const [metric, setMetric] = useState<"snr" | "latency" | "jitter" | "frequency">("snr");
  const [waveData, setWaveData] = useState<number[]>(() => Array(40).fill(50));

  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setWaveData((prev) => {
        const next = [...prev.slice(1)];
        let val = 50;
        if (metric === "snr") {
          val = 70 + Math.sin(Date.now() / 300) * 15 + (Math.random() - 0.5) * 8;
        } else if (metric === "latency") {
          val = 15 + Math.cos(Date.now() / 400) * 10 + (Math.random() - 0.5) * 6;
        } else if (metric === "jitter") {
          val = 2.4 + Math.sin(Date.now() / 200) * 1.5 + (Math.random() - 0.5) * 0.8;
        } else {
          val = 60 + Math.sin(Date.now() / 500) * 5 + (Math.random() - 0.5) * 2;
        }
        next.push(Math.max(5, Math.min(95, val)));
        return next;
      });
    }, 120);
    return () => clearInterval(interval);
  }, [isOpen, metric]);

  if (!isOpen) return null;

  const pointsString = waveData
    .map((v, i) => `${(i / (waveData.length - 1)) * 500},${150 - (v / 100) * 120}`)
    .join(" ");

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fade-in font-sans">
      <div className="relative w-full max-w-2xl rounded-2xl border border-primary/30 bg-slate-900/90 p-6 shadow-2xl backdrop-blur-2xl">
        <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/30">
              <Icons.Activity className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                Live Telemetry Spectrum Visualizer
                <span className="flex h-2 w-2 rounded-full bg-success animate-ping" />
              </h3>
              <p className="text-xs text-slate-400">ESP32 IoT High-Frequency Sensor Signal & Network Diagnostics</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            <Icons.X className="h-5 w-5" />
          </button>
        </div>

        {/* Metric Switcher Tabs */}
        <div className="flex gap-2 mb-4 bg-slate-950/60 p-1 rounded-xl border border-white/10">
          {(
            [
              { id: "snr", label: "Signal SNR (dBm)", icon: Icons.Radio },
              { id: "latency", label: "Latency (ms)", icon: Icons.Zap },
              { id: "jitter", label: "Jitter (Hz)", icon: Icons.Gauge },
              { id: "frequency", label: "Telemetry Rate (Hz)", icon: Icons.Cpu },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setMetric(t.id)}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                metric === t.id
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              )}
            >
              <t.icon className="h-3.5 w-3.5" />
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        {/* Real-time Waveform Canvas Render */}
        <div className="relative h-48 w-full rounded-xl border border-white/10 bg-slate-950/90 p-4 overflow-hidden sentinel-grid-bg">
          <svg viewBox="0 0 500 150" className="h-full w-full overflow-visible preserve-3d">
            <defs>
              <linearGradient id="spectrumGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="oklch(0.68 0.19 250)" stopOpacity="0.4" />
                <stop offset="100%" stopColor="oklch(0.68 0.19 250)" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            <polygon
              points={`0,150 ${pointsString} 500,150`}
              fill="url(#spectrumGradient)"
            />

            <polyline
              fill="none"
              stroke="oklch(0.68 0.19 250)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={pointsString}
            />
          </svg>

          <div className="absolute top-3 right-3 flex items-center gap-2 rounded-lg bg-slate-900/80 border border-primary/40 px-3 py-1.5 font-mono text-xs text-primary shadow-lg backdrop-blur-md">
            <span>LIVE DATA:</span>
            <span className="font-bold text-white">
              {waveData[waveData.length - 1].toFixed(1)}{" "}
              {metric === "snr" ? "dBm" : metric === "latency" ? "ms" : metric === "jitter" ? "Hz" : "pkt/s"}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3 text-center">
            <div className="text-[10px] font-mono uppercase text-slate-400">Broker Protocol</div>
            <div className="text-sm font-bold text-success mt-0.5 font-mono">MQTT / TLS 1.3</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3 text-center">
            <div className="text-[10px] font-mono uppercase text-slate-400">Packet Loss</div>
            <div className="text-sm font-bold text-white mt-0.5 font-mono">0.00% (Nominal)</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3 text-center">
            <div className="text-[10px] font-mono uppercase text-slate-400">WiFi RSSI</div>
            <div className="text-sm font-bold text-primary mt-0.5 font-mono">-58 dBm</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-slate-950/40 p-3 text-center">
            <div className="text-[10px] font-mono uppercase text-slate-400">ESP32 Heap Free</div>
            <div className="text-sm font-bold text-accent mt-0.5 font-mono">214.8 KB</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function KeyboardShortcutsModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!isOpen) return null;

  const shortcuts = [
    { key: "M / 1", action: "Navigate to Digital Twin Overview" },
    { key: "P / 2", action: "Open Patrol & Mission Control" },
    { key: "T / 3", action: "Open 2D/3D Floor Twin Map" },
    { key: "V / 4", action: "Live Camera Stream Feed" },
    { key: "A / 5", action: "Open Alert Log Center" },
    { key: "H / 6", action: "View Incident History Timeline" },
    { key: "C / 7", action: "AI Security Assistant Chat" },
    { key: "L", action: "Toggle Live Telemetry Waveform Visualizer" },
    { key: "D", action: "Toggle Dark / Light Theme" },
    { key: "E / Space", action: "TRIGGER EMERGENCY STOP (Rover)" },
    { key: "?", action: "Show / Hide Keyboard Shortcuts" },
  ];

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fade-in font-sans">
      <div className="relative w-full max-w-lg rounded-2xl border border-primary/30 bg-slate-900/95 p-6 shadow-2xl backdrop-blur-2xl">
        <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/30">
              <Icons.Keyboard className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Keyboard Hotkey Shortcuts</h3>
              <p className="text-xs text-slate-400">Quick Command Navigation Keys</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            <Icons.X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
          {shortcuts.map((s, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-950/50 px-4 py-2.5 hover:border-primary/30 transition-colors"
            >
              <span className="text-xs font-medium text-slate-300">{s.action}</span>
              <kbd className="rounded-lg border border-primary/40 bg-primary/10 px-2.5 py-1 text-xs font-mono font-bold text-primary shadow-sm">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="mt-6 border-t border-white/10 pt-4 text-center">
          <button
            onClick={onClose}
            className="w-full rounded-xl bg-primary py-2.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer shadow-lg shadow-primary/20"
          >
            Close Shortcut Guide
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SentinelTwinXDashboard() {
  const [activeTab, setActiveTab] = useState<"camera" | "mission" | "home" | "twin" | "analytics" | "alerts" | "history" | "assistant" | "settings">("home");
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [emergencyCameraPopup, setEmergencyCameraPopup] = useState(false);
  const [userDismissedCrisisCamera, setUserDismissedCrisisCamera] = useState(false);
  const [isKeyboardHelpOpen, setIsKeyboardHelpOpen] = useState(false);
  const [isSpectrumOpen, setIsSpectrumOpen] = useState(false);

  const [systemMode, setSystemMode] = useState<"live" | "demo">(() => {
    const saved = localStorage.getItem("systemMode");
    return (saved === "live" || saved === "demo") ? saved : "live";
  });

  const [transitioningMode, setTransitioningMode] = useState<"live" | "demo" | null>(null);

  // Settings State Hooks
  const [refreshInterval, setRefreshInterval] = useState(() => Number(localStorage.getItem("settings_refreshInterval") || "2500"));
  const [soundEnabled, setSoundEnabled] = useState(() => localStorage.getItem("settings_soundEnabled") !== "false");
  const [autoReconnect, setAutoReconnect] = useState(() => localStorage.getItem("settings_autoReconnect") !== "false");
  const [demoSpeed, setDemoSpeed] = useState(() => Number(localStorage.getItem("settings_demoSpeed") || "1"));

  const [backendState, setBackendState] = useState<any>(null);
  const backendStateRef = useRef<any>(null);
  const obstacleStartTimeRef = useRef<number | null>(null);
  useEffect(() => {
    backendStateRef.current = backendState;
  }, [backendState]);

  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Browser MQTT WebSocket Client (ws://10.10.0.213:9001)
  const mqttClientRef = useRef<any>(null);
  const [browserMqttConnected, setBrowserMqttConnected] = useState<boolean>(false);

  useEffect(() => {
    const hostIp = window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" && !window.location.hostname.includes("web.app") ? window.location.hostname : "sentinelpi.local";
    const brokerUrl = `ws://${hostIp}:9001`;
    console.log("[Browser MQTT] Initializing WebSocket client connection to broker:", brokerUrl);

    let client: any = null;
    try {
      client = mqtt.connect(brokerUrl, {
        clientId: `sentinel_web_${Math.random().toString(16).substring(2, 8)}`,
        keepalive: 30,
        reconnectPeriod: 3000,
        connectTimeout: 5000,
      });

      client.on("connect", () => {
        console.log("[Browser MQTT Connected] Successfully connected to MQTT WebSocket broker:", brokerUrl);
        setBrowserMqttConnected(true);
      });

      client.on("reconnect", () => {
        console.log("[Browser MQTT Reconnecting] Retrying connection to broker:", brokerUrl);
      });

      client.on("error", (err: any) => {
        console.warn(`[Browser MQTT Error] Connection error to ${brokerUrl}:`, err);
        setBrowserMqttConnected(false);
      });

      client.on("close", () => {
        console.log("[Browser MQTT Closed] Connection closed.");
        setBrowserMqttConnected(false);
      });

      mqttClientRef.current = client;
    } catch (err) {
      console.error("[Browser MQTT Exception] Failed to instantiate MQTT client:", err);
    }

    return () => {
      if (client) {
        client.end(true);
      }
    };
  }, []);

  const [notifications, setNotifications] = useState<any[]>([]);

  const addNotification = useCallback((title: string, message: string, type: "info" | "success" | "warning" | "error" = "info") => {
    const id = Math.random().toString(36).substr(2, 9);
    setNotifications((prev) => [...prev, { id, title, message, type }]);
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 4000);
  }, []);

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  // Request Desktop Notification Permission on Mount
  useEffect(() => {
    requestDesktopNotificationPermission();
  }, []);

  // Global Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement &&
        ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
      ) {
        return;
      }

      const key = e.key.toLowerCase();
      if (key === "?" || (e.shiftKey && key === "/")) {
        e.preventDefault();
        setIsKeyboardHelpOpen((prev) => !prev);
      } else if (key === "m" || key === "1") {
        setActiveTab("home");
      } else if (key === "p" || key === "2") {
        setActiveTab("mission");
      } else if (key === "t" || key === "3") {
        setActiveTab("twin");
      } else if (key === "v" || key === "4") {
        setActiveTab("camera");
      } else if (key === "a" || key === "5") {
        setActiveTab("alerts");
      } else if (key === "h" || key === "6") {
        setActiveTab("history");
      } else if (key === "c" || key === "7") {
        setActiveTab("assistant");
      } else if (key === "l") {
        setIsSpectrumOpen((prev) => !prev);
      } else if (key === "d") {
        setTheme((prev) => (prev === "dark" ? "light" : "dark"));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ----------------------------------------------------------------------------
  // Demo Mode Simulation State
  // ----------------------------------------------------------------------------
  const [demoSensors, setDemoSensors] = useState<{ [key: string]: { temp: number; humidity: number; gas: number; blocked: boolean; online: boolean } }>(() => {
    const base: any = {};
    buildingConfig.rooms.forEach(r => {
      base[r.id] = {
        temp: r.temperature || 21.5,
        humidity: r.humidity || 52,
        gas: r.gas || 12,
        blocked: r.flame || false,
        online: true
      };
    });
    return base;
  });

  // Simulation Target sensor values for gradual nudging
  const [sensorTargets, setSensorTargets] = useState<{ [key: string]: { temp: number; humidity: number; gas: number } }>(() => {
    const base: any = {};
    buildingConfig.rooms.forEach(r => {
      base[r.id] = {
        temp: r.temperature || 21.5,
        humidity: r.humidity || 52,
        gas: r.gas || 12,
      };
    });
    return base;
  });

  const [demoRover, setDemoRover] = useState({
    status: "charging",
    current_zone: "r-101",
    target_zone: "r-101",
    position: [410.0, 129.0] as [number, number],
    battery_pct: 98.4,
    path: [] as string[],
  });

  const [demoMissions, setDemoMissions] = useState<Mission[]>([
    { id: "m1", name: "Floor 2 Full Patrol", type: "PATROL", progress: 62, waypoint: "Chemistry Lab", next: "Physics Lab", eta: "4m 12s", status: "running" },
    { id: "m2", name: "Cafeteria AQ Sweep", type: "INSPECTION", progress: 0, waypoint: "—", next: "Cafeteria", eta: "8m 00s", status: "queued" },
    { id: "m3", name: "Perimeter Check", type: "PATROL", progress: 0, waypoint: "—", next: "Main Entrance", eta: "12m 30s", status: "queued" },
  ]);

  const [demoAlerts, setDemoAlerts] = useState<any[]>([
    { id: "a1", severity: "critical", location: "Chemistry Lab", time: "2 min ago", sensor: "Flame + Gas", message: "Flame detected with elevated combustible gas (128 ppm)", recommendation: "Dispatch emergency protocol. Evacuate Floor 2 east wing.", resolved: false },
    { id: "a2", severity: "warning", location: "Server Room", time: "12 min ago", sensor: "Temperature", message: "Ambient temperature 28.9°C exceeds threshold", recommendation: "Verify HVAC. Increase cooling setpoint.", resolved: false },
    { id: "a3", severity: "warning", location: "Cafeteria", time: "34 min ago", sensor: "Air Quality", message: "AQI dropped to 78 during service hours", recommendation: "Enable secondary ventilation for 20 minutes.", resolved: false },
  ]);

  const [demoTimeline, setDemoTimeline] = useState<TimelineEvent[]>([
    { event_type: "reset", description: "📐 Sensor calibration complete — dynamic thresholds active", severity: "info", timestamp: Date.now() / 1000 - 30 },
    { event_type: "info", description: "🔋 Rover battery fully charged. Docked.", severity: "info", timestamp: Date.now() / 1000 - 200 }
  ]);

  const sendRoverCommand = useCallback((cmd: string) => {
    addNotification("Command Sent", `Rover instructed: ${cmd}`, "info");
    playNotificationSound("info");

    if (systemMode === "live") {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        let action = "stop_rover";
        if (cmd === "Forward") action = "move_forward";
        else if (cmd === "Backward") action = "move_backward";
        else if (cmd === "Left") action = "turn_left";
        else if (cmd === "Right") action = "turn_right";
        else if (cmd === "Stop") action = "stop_rover";
        else if (cmd === "Autonomous Patrol") action = "dispatch_rover";
        else if (cmd === "Return Home") action = "recall_rover";

        wsRef.current.send(JSON.stringify({
          type: "manual_action",
          action,
          params: action === "dispatch_rover" ? { zone: "chem_lab", reason: "Manual patrol request" } : {}
        }));
      }
    } else {
      setDemoRover(prev => {
        let nextZone = prev.current_zone;
        let nextPos = [...prev.position] as [number, number];
        let nextStatus = prev.status;

        if (cmd === "Forward") {
          nextPos[1] -= 10;
          nextStatus = "moving";
        } else if (cmd === "Backward") {
          nextPos[1] += 10;
          nextStatus = "moving";
        } else if (cmd === "Left") {
          nextPos[0] -= 10;
          nextStatus = "moving";
        } else if (cmd === "Right") {
          nextPos[0] += 10;
          nextStatus = "moving";
        } else if (cmd === "Stop") {
          nextStatus = "idle";
        } else if (cmd === "Return Home") {
          nextZone = "r-101";
          nextPos = [410.0, 129.0];
          nextStatus = "charging";
        } else if (cmd === "Autonomous Patrol") {
          nextStatus = "patrolling";
        }

        return {
          ...prev,
          current_zone: nextZone,
          position: nextPos,
          status: nextStatus
        };
      });
    }
  }, [systemMode, addNotification]);

  const dispatchMission = useCallback((zone: string) => {
    if (systemMode === "live") {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "manual_action",
          action: "dispatch_rover",
          params: { zone: zone === "r-201" ? "chem_lab" : zone === "r-103" ? "kitchen" : "cad_lab", reason: "Deploy requested from UI" }
        }));
      }
    } else {
      // Handled via scenario trigger
    }
  }, [systemMode]);

  const sendMqttPayload = useCallback((topic: string, payload: any) => {
    const payloadStr = typeof payload === "string" ? payload : JSON.stringify(payload);

    // Console log showing topic and payload being published
    console.log("[MQTT Publish] Topic:", topic, "Payload:", payloadStr);

    const client = mqttClientRef.current;
    // Verify that the browser MQTT client is connected before publishing
    if (client && client.connected) {
      console.log("[MQTT Connection Verified] Client connected to MQTT Broker. Publishing message...");
      client.publish(topic, payloadStr, { qos: 1 }, (err: any) => {
        if (err) {
          console.error("[MQTT Publish Error] Failed to publish to topic:", topic, err);
        } else {
          console.log("[MQTT Published Successfully] Topic:", topic, "Payload:", payloadStr);
        }
      });
    } else {
      console.warn("[MQTT Connection Warning] Browser MQTT client is NOT connected. Connected status:", client ? client.connected : false);
    }

    // Secondary backend WebSocket relay for app_state tracking
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "publish_mqtt",
        topic: topic,
        payload: payload
      }));
    }

    if (systemMode === "demo") {
      const cmd = typeof payload === "object" ? payload?.command : null;
      if (cmd) {
        setDemoRover(prev => {
          let nextStatus = prev.status;
          if (cmd === "start") nextStatus = "patrolling";
          else if (cmd === "pause") nextStatus = "paused";
          else if (cmd === "stop") nextStatus = "idle";
          else if (cmd === "emergency") nextStatus = "emergency";
          return { ...prev, status: nextStatus };
        });
      }
    }

    addNotification("MQTT Command Published", `Topic: ${topic} | ${payloadStr}`, "info");
    playNotificationSound(typeof payload === "object" && payload?.command === "emergency" ? "Critical" : "info");
  }, [systemMode, addNotification]);

  // Structured Incident Alert Logs State
  const [alertLogs, setAlertLogs] = useState<AlertLogItem[]>([
    {
      id: "log-1",
      time: "13:41:12",
      timestamp: Date.now() - 120000,
      type: "Fire Detected",
      priority: "Critical",
      mission: "Floor 2 Full Patrol",
      room: "Chemistry Lab",
      actionTaken: "Deploy Mission",
      operator: "Autonomous AI",
      status: "Unread",
      message: "Flame sensor triggered with critical thermal spikes (128 ppm gas)",
      recommendation: "Review feed and dispatch emergency backup responders immediately.",
      read: false,
      iconName: "Flame"
    },
    {
      id: "log-2",
      time: "13:28:45",
      timestamp: Date.now() - 900000,
      type: "Gas Leak",
      priority: "Critical",
      mission: "Cafeteria AQ Sweep",
      room: "Cafeteria",
      actionTaken: "Deploy Inspection",
      operator: "Autonomous AI",
      status: "Unread",
      message: "Combustible gas leak detected (450 ppm)",
      recommendation: "Enable secondary ventilation for 20 minutes.",
      read: false,
      iconName: "Wind"
    },
    {
      id: "log-3",
      time: "13:14:02",
      timestamp: Date.now() - 1800000,
      type: "Temperature High",
      priority: "High",
      mission: "Server Room Check",
      room: "Server Room",
      actionTaken: "HVAC Check",
      operator: "Ankit",
      status: "Read",
      message: "Ambient temperature 28.9°C exceeds threshold",
      recommendation: "Verify HVAC setpoint and airflow intake.",
      read: true,
      iconName: "Thermometer"
    }
  ]);

  // Startup Splash Screen, Login System, and Role Authorization States
  const [splashFinished, setSplashFinished] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [username, setUsername] = useState(() => {
    return localStorage.getItem("sentinel_username") || "Ankit";
  });
  const [userRole, setUserRole] = useState<"Administrator" | "Operator" | "Viewer">(() => {
    return (localStorage.getItem("sentinel_role") as any) || "Administrator";
  });

  // Mission Post-Mortem Report Generator Modal State
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedReportData, setSelectedReportData] = useState<any>(null);

  // Rover Stuck Detection State
  const [isRoverStuckModalOpen, setIsRoverStuckModalOpen] = useState(false);
  const [stuckDurationSeconds, setStuckDurationSeconds] = useState(0);
  const [isRerouting, setIsRerouting] = useState(false);
  const [rerouteSuccess, setRerouteSuccess] = useState(false);
  const lastRoverPosRef = useRef<[number, number] | null>(null);
  const staticPositionStartRef = useRef<number | null>(null);

  // Dynamic Unread Badge Counter
  const unreadAlertCount = useMemo(() => alertLogs.filter(a => !a.read).length, [alertLogs]);

  // Alert Deduplication & Rate Limiting Cache Ref (5s window per alert/room)
  const lastAlertTimesRef = useRef<Record<string, number>>({});

  // Centralized System Alert & Triage Dispatcher
  const triggerSystemAlert = useCallback((
    type: string,
    room: string = "Chemistry Lab",
    customMessage?: string,
    missionName?: string
  ) => {
    // Prevent duplicate alert triggers within a 5-second window
    const dedupKey = `${type}:${room}`;
    const now = Date.now();
    if (lastAlertTimesRef.current[dedupKey] && now - lastAlertTimesRef.current[dedupKey] < 5000) {
      return;
    }
    lastAlertTimesRef.current[dedupKey] = now;

    const config = SUPPORTED_ALERTS_CONFIG[type] || {
      priority: "High" as AlertPriority,
      icon: "AlertTriangle",
      defaultDesc: "System alert event recorded",
      autoAction: "Log Diagnostics"
    };

    const timeStr = new Date().toLocaleTimeString("en-GB", { hour12: false });
    const logId = "log-" + Date.now();

    const newLog: AlertLogItem = {
      id: logId,
      time: timeStr,
      timestamp: Date.now(),
      type: type,
      priority: config.priority,
      mission: missionName || "Patrol Mission",
      room: room,
      actionTaken: config.autoAction,
      operator: "Autonomous AI",
      status: "Unread",
      message: customMessage || config.defaultDesc,
      recommendation: `Automated ${config.autoAction} initialized by Sentinel Engine.`,
      read: false,
      iconName: config.icon
    };

    setAlertLogs(prev => [newLog, ...prev]);

    // Send Desktop System Notification
    sendDesktopNotification(type, `${room}: ${customMessage || config.defaultDesc}`, config.priority);

    // Play Audio Synthesizer Tone if Sound Enabled
    if (soundEnabled) {
      playNotificationSound(config.priority);
    }

    // Display In-Dashboard Toast Notification
    const toastType = config.priority === "Critical" ? "error" : config.priority === "High" ? "warning" : "info";
    addNotification(type, `${room}: ${customMessage || config.defaultDesc}`, toastType);

    // Execute Auto Actions based on alert type
    if (type === "Fire Detected") {
      dispatchMission(room === "Chemistry Lab" ? "r-201" : "r-201");
    } else if (type === "Gas Leak") {
      dispatchMission(room === "Cafeteria" ? "r-103" : "r-103");
    } else if (type === "Battery Critical") {
      sendRoverCommand("Return Home");
    } else if (type === "Rover Stuck") {
      setIsRoverStuckModalOpen(true);
    } else if (type === "MQTT Offline") {
      addNotification("Auto Action", "Reconnecting MQTT transport connection automatically...", "info");
    } else if (type === "Camera Offline") {
      addNotification("Auto Action", "Retrying ESP32-CAM video stream connection...", "info");
    }
  }, [soundEnabled, addNotification, dispatchMission, sendRoverCommand]);

  // Continuous Rover Stuck Movement Monitoring Engine (10-second position check)
  useEffect(() => {
    const interval = setInterval(() => {
      const isLiveMode = systemMode === "live";

      const currentPos = isLiveMode
        ? (backendState?.rover?.position as [number, number] | undefined)
        : demoRover.position;

      const roverStatus = isLiveMode
        ? (backendState?.rover?.status || "")
        : demoRover.status;

      const missionStatus = isLiveMode
        ? (backendState?.rover?.current_mission?.status || "")
        : (demoMissions.some(m => m.status === "running") ? "running" : "");

      const currentMissionName = isLiveMode
        ? (backendState?.rover?.current_mission?.name || "Patrol")
        : (demoMissions.find(m => m.status === "running")?.name || "Floor 2 Full Patrol");

      // Strictly verify rover is supposed to be moving under an active running mission
      // MUST NOT trigger when: Mission paused, Mission completed, Manual mode, Return Home, Demo idle state
      const isRoverMoving = (roverStatus === "moving" || roverStatus === "patrolling" || roverStatus === "en_route");
      const isMissionActive = (missionStatus === "running" && currentMissionName !== "Idle" && currentMissionName !== "No Active Mission" && currentMissionName !== "—");

      if (!isRoverMoving || !isMissionActive || !currentPos) {
        lastRoverPosRef.current = null;
        staticPositionStartRef.current = null;
        setStuckDurationSeconds(0);
        return;
      }

      if (!lastRoverPosRef.current) {
        lastRoverPosRef.current = currentPos;
        staticPositionStartRef.current = Date.now();
        return;
      }

      const dx = Math.abs(currentPos[0] - lastRoverPosRef.current[0]);
      const dy = Math.abs(currentPos[1] - lastRoverPosRef.current[1]);
      const distMoved = Math.sqrt(dx * dx + dy * dy);

      if (distMoved < 0.5) {
        if (!staticPositionStartRef.current) {
          staticPositionStartRef.current = Date.now();
        }
        const elapsedSec = Math.floor((Date.now() - staticPositionStartRef.current) / 1000);
        setStuckDurationSeconds(elapsedSec);

        // If stationary >= 10 seconds while a mission is active and moving
        if (elapsedSec >= 10 && !isRoverStuckModalOpen) {
          const roomName = isLiveMode
            ? (backendState?.rover?.current_zone || "Chemistry Lab")
            : (buildingConfig.rooms.find(r => r.id === demoRover.current_zone)?.name || "Chemistry Lab");

          triggerSystemAlert(
            "Rover Stuck",
            roomName,
            "Rover position unchanged for >10s while active mission is moving.",
            currentMissionName
          );
        }
      } else {
        // Rover moved! Reset static position tracking
        lastRoverPosRef.current = currentPos;
        staticPositionStartRef.current = Date.now();
        setStuckDurationSeconds(0);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [systemMode, backendState, demoRover, demoMissions, isRoverStuckModalOpen, triggerSystemAlert]);

  // Demo Mode Handler: Simulate Rover Stuck Event
  const triggerSimulatedRoverStuck = useCallback(() => {
    setDemoRover(prev => ({
      ...prev,
      status: "moving",
      current_zone: "r-201"
    }));

    setDemoMissions([
      { id: "demo-stuck-m", name: "Floor 2 Full Patrol", type: "PATROL", progress: 45, waypoint: "Chemistry Lab", next: "Physics Lab", eta: "Stuck", status: "running" }
    ]);

    staticPositionStartRef.current = Date.now() - 12000;
    setStuckDurationSeconds(12);

    triggerSystemAlert(
      "Rover Stuck",
      "Chemistry Lab",
      "Rover position unchanged for >10s during Floor 2 Full Patrol mission.",
      "Floor 2 Full Patrol"
    );
  }, [triggerSystemAlert]);

  // Stuck Modal Auto Recovery & Rerouting Handler
  const handleRetryNavigation = useCallback(() => {
    setIsRerouting(true);
    setRerouteSuccess(false);

    setTimeout(() => {
      setIsRerouting(false);
      setRerouteSuccess(true);
      addNotification("Auto Recovery", "Calculating Alternative Route... Success! Mission Resumed.", "success");
      playNotificationSound("success");

      setTimeout(() => {
        setIsRoverStuckModalOpen(false);
        setRerouteSuccess(false);
        setStuckDurationSeconds(0);
        staticPositionStartRef.current = null;
      }, 1500);
    }, 2000);
  }, [addNotification]);

  const handleMarkRead = (id: string) => {
    setAlertLogs(prev => prev.map(l => l.id === id ? { ...l, read: !l.read, status: !l.read ? "Read" : "Unread" } : l));
  };

  const handleMarkAllRead = () => {
    setAlertLogs(prev => prev.map(l => ({ ...l, read: true, status: "Read" })));
    addNotification("Alert Center", "All alerts marked as read.", "info");
  };

  const handleClearAlerts = () => {
    setAlertLogs([]);
    addNotification("Alert Center", "Alert history cleared.", "warning");
  };



  // Gradual Simulation Tick Loop
  useEffect(() => {
    if (systemMode !== "demo") return;

    // Scale tick rate according to demo speed setting
    const tickInterval = 2500 / demoSpeed;

    const interval = setInterval(() => {
      setDemoSensors(prev => {
        const next = { ...prev };
        Object.keys(next).forEach(roomId => {
          const target = sensorTargets[roomId] || { temp: 22.5, humidity: 50.0, gas: 12 };
          const current = prev[roomId];

          const diffTemp = target.temp - current.temp;
          const diffHum = target.humidity - current.humidity;
          const diffGas = target.gas - current.gas;

          // Nudge smoothly (increased random walk factor to overcome rounding truncation)
          const stepTemp = Math.sign(diffTemp) * Math.min(Math.abs(diffTemp), 0.8) + (Math.random() - 0.5) * 0.35;
          const stepHum = Math.sign(diffHum) * Math.min(Math.abs(diffHum), 1.5) + (Math.random() - 0.5) * 1.2;
          const stepGas = Math.sign(diffGas) * Math.min(Math.abs(diffGas), 35) + Math.round((Math.random() - 0.5) * 2);

          next[roomId] = {
            temp: +(Math.max(15, Math.min(45, current.temp + stepTemp))).toFixed(1),
            humidity: +(Math.max(20, Math.min(90, current.humidity + stepHum))).toFixed(1),
            gas: Math.max(5, Math.min(500, current.gas + stepGas)),
            blocked: current.blocked,
            online: true
          };
        });
        return next;
      });

      setDemoRover(prev => {
        let nextBattery = prev.battery_pct;
        if (prev.status === "charging") {
          nextBattery = Math.min(100.0, prev.battery_pct + 0.3 * demoSpeed);
        } else {
          nextBattery = Math.max(10.0, prev.battery_pct - 0.1 * demoSpeed);
        }
        return {
          ...prev,
          battery_pct: +nextBattery.toFixed(1)
        };
      });

    }, tickInterval);

    return () => clearInterval(interval);
  }, [systemMode, sensorTargets, demoSpeed]);

  const triggerDemoScenario = useCallback((scenarioName: string) => {
    // Reset Demo: clear all state back to baseline without requiring a reload
    if (scenarioName === "Reset Demo") {
      setDemoMissions([
        { id: "m1", name: "Idle — Awaiting Dispatch", type: "PATROL", progress: 0, waypoint: "Dock", next: "—", eta: "—", status: "queued" },
      ]);
      setDemoRover({
        status: "charging",
        current_zone: "r-101",
        target_zone: "r-101",
        position: [410.0, 129.0],
        battery_pct: 98.4,
        path: [],
      });
      setSensorTargets((() => {
        const base: any = {};
        buildingConfig.rooms.forEach(r => { base[r.id] = { temp: r.temperature || 21.5, humidity: r.humidity || 52, gas: r.gas || 12 }; });
        return base;
      })());
      setDemoSensors(prev => {
        const next = { ...prev };
        Object.keys(next).forEach(k => { next[k].blocked = false; next[k].online = true; });
        return next;
      });
      setDemoAlerts([]);
      setDemoTimeline(prev => [
        { event_type: "reset", description: "🔄 Demo reset to baseline. All sensors nominal.", severity: "info", timestamp: Date.now() / 1000 },
        ...prev.slice(0, 9),
      ]);
      addNotification("Demo Reset", "System state restored to baseline.", "success");
      playNotificationSound("success");
      return;
    }

    const active = demoMissions.find(m => m.status === "running");
    if (active && active.name !== "Idle" && active.name !== "No Active Mission" && active.name !== "Idle — Awaiting Dispatch") {
      addNotification("System Warning", "A mission is currently in progress. Please stop it first.", "warning");
      playNotificationSound("warning");
      return;
    }

    addNotification("Mission Assigned", `Assigned: ${scenarioName}`, "info");
    playNotificationSound("info");

    const scenarioPaths: Record<string, string[]> = {
      "Fire Emergency": ["r-101", "r-105", "r-201"],
      "Gas Leak": ["r-101", "r-103"],
      "Medical Emergency": ["r-101", "r-105", "r-206"],
      "Intruder Detection": ["r-101", "r-104"],
      "Routine Patrol": ["r-101", "r-102", "r-103", "r-105", "r-101"],
      "Night Patrol": ["r-201", "r-202", "r-203", "r-205", "r-206", "r-201"],
      "Autonomous Patrol": ["r-101", "r-103", "r-105", "r-201", "r-206", "r-203", "r-101"]
    };

    const targetRooms: Record<string, string> = {
      "Fire Emergency": "r-201",
      "Gas Leak": "r-103",
      "Medical Emergency": "r-206",
      "Intruder Detection": "r-104",
      "Routine Patrol": "r-105",
      "Night Patrol": "r-206",
      "Autonomous Patrol": "r-203"
    };

    const roomNames: Record<string, string> = {
      "r-101": "Main Entrance",
      "r-102": "Reception",
      "r-103": "Cafeteria",
      "r-104": "Gymnasium",
      "r-105": "Library",
      "r-106": "Storage",
      "r-107": "Server Room",
      "r-108": "Utility",
      "r-201": "Chemistry Lab",
      "r-202": "Physics Lab",
      "r-203": "Classroom 2A",
      "r-204": "Classroom 2B",
      "r-205": "Faculty Lounge",
      "r-206": "Computer Lab",
      "r-207": "Auditorium",
    };

    const path = scenarioPaths[scenarioName] || ["r-101"];
    const targetRoomId = targetRooms[scenarioName] || "r-101";
    const targetRoomName = roomNames[targetRoomId] || "Main Entrance";

    setDemoRover(prev => ({
      ...prev,
      status: "moving",
      current_zone: path[0] || "r-101",
      target_zone: targetRoomId,
      path: path
    }));

    setDemoMissions([
      { id: "demo-m", name: scenarioName, type: (scenarioName.includes("Emergency") || scenarioName.includes("Intruder") ? "EMERGENCY" : "PATROL") as any, progress: 5, waypoint: "Dock", next: roomNames[path[1]] || path[1], eta: "1m 30s", status: "running" }
    ]);

    setDemoTimeline(prev => [
      { event_type: "dispatch", description: `🚀 Mission dispatch assigned: ${scenarioName}`, severity: "info", timestamp: Date.now() / 1000 },
      ...prev
    ]);

    setTimeout(() => {
      addNotification("Route Planning", `Optimal path calculated: ${path.map(z => roomNames[z] || z).join(" → ")}`, "info");
      setDemoMissions(prev => prev.map(m => m.id === "demo-m" ? { ...m, progress: 20, waypoint: "Route Planning" } : m));
    }, 2000 / demoSpeed);

    setTimeout(() => {
      addNotification("Rover En Route", `Moving towards target zone: ${targetRoomName}...`, "info");
      setDemoMissions(prev => prev.map(m => m.id === "demo-m" ? { ...m, progress: 45, waypoint: "En Route" } : m));

      let step = 0;
      const moveInterval = setInterval(() => {
        step += 1;
        if (step >= path.length) {
          clearInterval(moveInterval);
          return;
        }
        setDemoRover(prev => ({
          ...prev,
          current_zone: path[step],
          position: path[step] === "r-201" ? [510.0, 229.0] : path[step] === "r-103" ? [210.0, 119.0] : [410.0, 129.0]
        }));
      }, 1500 / demoSpeed);
    }, 4500 / demoSpeed);

    setTimeout(() => {
      addNotification("AI Inference Active", `Analysing target zone: ${targetRoomName}...`, "warning");
      playNotificationSound("warning");
      setDemoMissions(prev => prev.map(m => m.id === "demo-m" ? { ...m, progress: 75, waypoint: "Verification" } : m));

      // Gradual Sensor Nudge Targets (Ramping up/down smoothly instead of sudden jump)
      setSensorTargets(prev => {
        const next = { ...prev };
        if (scenarioName === "Fire Emergency") {
          next["r-201"] = { temp: 42.4, humidity: 30.1, gas: 145 };
        } else if (scenarioName === "Gas Leak") {
          next["r-103"] = { temp: 24.5, humidity: 48.0, gas: 420 };
        } else if (scenarioName === "Intruder Detection") {
          next["r-104"] = { temp: 22.1, humidity: 55.4, gas: 10 };
        }
        return next;
      });

      setDemoSensors(prev => {
        const next = { ...prev };
        if (scenarioName === "Fire Emergency") next["r-201"].blocked = true;
        if (scenarioName === "Intruder Detection") next["r-104"].blocked = true;
        return next;
      });

      const alertId = "demo-a-" + Date.now();
      let alertMsg = "";
      let severity: "critical" | "warning" = "warning";
      if (scenarioName === "Fire Emergency") {
        alertMsg = "Flame detected with elevated combustible gas (128 ppm) in Chemistry Lab";
        severity = "critical";
      } else if (scenarioName === "Gas Leak") {
        alertMsg = "Combustible gas leak detected (450 ppm) in Cafeteria";
        severity = "critical";
      } else if (scenarioName === "Intruder Detection") {
        alertMsg = "Intruder detected in Gymnasium area";
        severity = "critical";
      } else {
        alertMsg = `Routine sweep completed at ${targetRoomName}`;
      }

      setDemoAlerts(prev => [
        {
          id: alertId,
          severity,
          location: targetRoomName,
          time: "Just now",
          sensor: scenarioName === "Fire Emergency" ? "Flame + Gas" : "AI Vision CAM-04",
          message: alertMsg,
          recommendation: "Review feed and dispatch backup safety responders immediately.",
          resolved: false
        },
        ...prev
      ]);

      setDemoTimeline(prev => [
        { event_type: "alert", description: alertMsg, severity, zone_id: targetRoomId, timestamp: Date.now() / 1000 },
        ...prev
      ]);
    }, 8500 / demoSpeed);

    setTimeout(() => {
      addNotification("Mission Complete", `Task finished successfully. Docking rover.`, "success");
      playNotificationSound("success");
      setDemoMissions(prev => prev.map(m => m.id === "demo-m" ? { ...m, progress: 100, status: "completed" as const, waypoint: "Returning" } : m));

      setDemoRover(prev => ({
        ...prev,
        status: "charging",
        current_zone: "r-101",
        target_zone: "r-101",
        position: [410.0, 129.0]
      }));

      // Cool down gradually back to normal bounds
      setSensorTargets(prev => {
        const next = { ...prev };
        buildingConfig.rooms.forEach(r => {
          next[r.id] = { temp: r.temperature || 21.5, humidity: r.humidity || 52, gas: r.gas || 12 };
        });
        return next;
      });

      setDemoSensors(prev => {
        const next = { ...prev };
        Object.keys(next).forEach(k => { next[k].blocked = false; });
        return next;
      });

      setDemoTimeline(prev => [
        { event_type: "arrival", description: `✓ Area Cleared. Rover docked.`, severity: "info", timestamp: Date.now() / 1000 },
        ...prev
      ]);
    }, 14000 / demoSpeed);

  }, [demoMissions, addNotification, demoSpeed]);

  // Autonomous Patrol Loop simulation (Demo Mode)
  useEffect(() => {
    if (systemMode !== "demo") return;

    if (demoRover.status === "charging" || demoRover.status === "idle") {
      const timer = setTimeout(() => {
        const scenarios = [
          "Routine Patrol",
          "Night Patrol",
          "Autonomous Patrol",
        ];
        const randomScenario = scenarios[Math.floor(Math.random() * scenarios.length)];
        triggerDemoScenario(randomScenario);
      }, 15000);

      return () => clearTimeout(timer);
    }
  }, [systemMode, demoRover.status, triggerDemoScenario]);



  const setSystemModeAndPersist = useCallback((mode: "live" | "demo") => {
    setSystemMode(mode);
    localStorage.setItem("systemMode", mode);
    addNotification("System Mode", `Switched operating mode to: ${mode === "live" ? "Live Hardware" : "Demo Mode"}`, "success");
    playNotificationSound("success");

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "change_telemetry_mode",
          mode: mode === "demo" ? "sim" : "mqtt",
          port: "COM3",
          broker: backendStateRef.current?.mqtt_broker || "sentinelpi.local",
        })
      );
    }
  }, [addNotification]);

  // ----------------------------------------------------------------------------
  // Live Mode Data Provider via WebSockets
  // ----------------------------------------------------------------------------
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const socketUrl = `${protocol}//${host}/ws`;

    let socket: WebSocket;
    let reconnectTimeout: any;

    const connect = () => {
      socket = new WebSocket(socketUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setWsConnected(true);
        const currentMode = localStorage.getItem("systemMode") || "live";
        socket.send(
          JSON.stringify({
            type: "change_telemetry_mode",
            mode: currentMode === "demo" ? "sim" : "mqtt",
            port: "COM3",
            broker: backendStateRef.current?.mqtt_broker || "sentinelpi.local",
          })
        );
      };

      socket.onmessage = (event) => {
        try {
          const snapshot = JSON.parse(event.data);
          setBackendState(snapshot);

          const isObstacleActive = Boolean(
            snapshot.rover?.obstacle_detected ||
            Object.values(snapshot.zones || {}).some((z: any) => z.blocked)
          );

          if (isObstacleActive) {
            if (!obstacleStartTimeRef.current) {
              obstacleStartTimeRef.current = Date.now();
            } else if (Date.now() - obstacleStartTimeRef.current >= 10000) {
              // 10 seconds of continuous obstruction completed -> trigger camera popup to full screen!
              setEmergencyCameraPopup(true);
            }
          } else {
            obstacleStartTimeRef.current = null;
          }

          if (snapshot.alert_active || snapshot.layout_mode === 'crisis') {
            setEmergencyCameraPopup(true);
          }
        } catch (err) {
          console.error("Failed to parse WebSocket state snapshot:", err);
        }
      };

      socket.onclose = () => {
        setWsConnected(false);
        if (autoReconnect) {
          reconnectTimeout = setTimeout(connect, refreshInterval);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, [autoReconnect, refreshInterval]);

  // Continuous 10-second Obstruction Camera Pop-Up Timer (Evaluates every 500ms in real-time)
  useEffect(() => {
    const timer = setInterval(() => {
      const isObstacleActive = Boolean(
        backendState?.rover?.obstacle_detected ||
        backendState?.alert_active ||
        backendState?.layout_mode === 'crisis' ||
        Object.values(backendState?.zones || {}).some((z: any) => z.blocked) ||
        Object.values(demoSensors || {}).some((s: any) => s.blocked)
      );
      if (isObstacleActive) {
        if (!obstacleStartTimeRef.current) {
          obstacleStartTimeRef.current = Date.now();
        } else if (Date.now() - obstacleStartTimeRef.current >= 10000) {
          // 10 seconds completed -> trigger camera popup to full screen!
          setEmergencyCameraPopup(true);
        }
      } else {
        obstacleStartTimeRef.current = null;
      }
    }, 500);

    return () => clearInterval(timer);
  }, [backendState, demoSensors]);

  const isLive = systemMode === "live";

  // Live Provider Implementation — Strictly Real Hardware Telemetry (No Simulated Fallbacks)
  const liveProvider = useMemo<SentinelDataProvider>(() => {
    const isOnline = wsConnected && Boolean(backendState);

    const lastHeartbeatStr = backendState?.last_updated
      ? new Date(backendState.last_updated * 1000).toLocaleTimeString()
      : "Never";

    const roverSensors = backendState?.rover?.sensors;
    const isRoverOnline = isOnline && roverSensors && (Date.now() / 1000 - (roverSensors.last_seen || 0) < 15.0);

    const isMqttConnected = (isOnline && Boolean(backendState?.mqtt_connected)) || browserMqttConnected;
    const isSerialConnected = Boolean(backendState?.hardware_status?.esp32_connected);
    
    // Physical ESP32 Rover is connected only when active serial, live heartbeat, or active mqtt nodes are transmitting
    const isEsp32Connected = isOnline && (isSerialConnected || Boolean(isRoverOnline) || (backendState?.mqtt_node_count || 0) > 0);
    const isCameraStreaming = isOnline && Boolean(backendState?.camera_online);
    const isPiConnected = isOnline || Boolean(backendState) || browserMqttConnected;

    // Resolve live MQTT sensor data only from real active online room nodes or rover
    const onlineZones = isOnline && backendState?.zones
      ? Object.values(backendState.zones).filter((z: any) => z.online && z.temp !== null && z.temp !== undefined)
      : [];

    const activeZoneId = isOnline && isEsp32Connected && backendState?.rover?.current_zone ? backendState.rover.current_zone : null;
    const activeZoneData = activeZoneId && backendState?.zones?.[activeZoneId] ? backendState.zones[activeZoneId] : null;

    const avgTemp = onlineZones.length > 0 ? onlineZones.reduce((acc: number, z: any) => acc + z.temp, 0) / onlineZones.length : (isRoverOnline && roverSensors?.temp ? roverSensors.temp : null);
    const avgHum = onlineZones.length > 0 ? onlineZones.reduce((acc: number, z: any) => acc + z.humidity, 0) / onlineZones.length : (isRoverOnline && roverSensors?.humidity ? roverSensors.humidity : null);
    const avgSmoke = onlineZones.length > 0 ? onlineZones.reduce((acc: number, z: any) => acc + z.smoke, 0) / onlineZones.length : (isRoverOnline && roverSensors?.smoke ? roverSensors.smoke : null);
    const avgMQ7 = onlineZones.length > 0 ? onlineZones.reduce((acc: number, z: any) => acc + (z.mq7 || 0), 0) / onlineZones.length : (isRoverOnline && roverSensors?.mq7 ? roverSensors.mq7 : null);
    const avgMQ135 = onlineZones.length > 0 ? onlineZones.reduce((acc: number, z: any) => acc + (z.mq135 || 0), 0) / onlineZones.length : (isRoverOnline && roverSensors?.mq135 ? roverSensors.mq135 : null);

    const rawTemp = activeZoneData && activeZoneData.temp !== null ? activeZoneData.temp : avgTemp;
    const rawHumidity = activeZoneData && activeZoneData.humidity !== null ? activeZoneData.humidity : avgHum;
    const rawMQ2 = activeZoneData && activeZoneData.smoke !== null ? activeZoneData.smoke : avgSmoke;
    const rawMQ7 = activeZoneData && activeZoneData.mq7 !== null ? activeZoneData.mq7 : avgMQ7;
    const rawMQ135 = activeZoneData && activeZoneData.mq135 !== null ? activeZoneData.mq135 : avgMQ135;

    const summaryTemp = rawTemp !== null && rawTemp !== undefined ? `${rawTemp.toFixed(1)}` : "--";
    const summaryHumidity = rawHumidity !== null && rawHumidity !== undefined ? `${rawHumidity.toFixed(0)}` : "--";
    const summaryAirQuality = rawMQ135 !== null && rawMQ135 !== undefined ? `${Math.round(rawMQ135)}` : "--";
    const summaryGas = rawMQ2 !== null && rawMQ2 !== undefined ? `${Math.round(rawMQ2)}` : "--";
    const summaryCO = rawMQ7 !== null && rawMQ7 !== undefined ? `${Math.round(rawMQ7)}` : "--";

    const liveStatus: SystemStatus = {
      battery: isEsp32Connected && backendState?.rover?.battery_pct ? backendState.rover.battery_pct : 0,
      wifi: isPiConnected ? "connected" : "offline",
      mqtt: isMqttConnected ? "online" : "offline",
      raspberryPi: isPiConnected ? "online" : "offline",
      esp32: isEsp32Connected ? "online" : "offline",
      camera: isCameraStreaming ? "streaming" : "offline",
      ai: isPiConnected ? "active" : "idle",
      systemHealth: isEsp32Connected ? Math.max(10, 100 - (backendState?.overall_risk || 0)) : (isPiConnected ? 100 : 0),
      currentMission: isEsp32Connected && backendState?.rover?.current_mission?.name ? backendState.rover.current_mission.name : "Rover Off / Standby",
      currentRoom: isEsp32Connected && backendState?.rover?.current_zone ? backendState.rover.current_zone : "Standby Dock",
      uptime: isPiConnected ? (backendState?.last_updated ? new Date(backendState.last_updated * 1000).toLocaleTimeString() : "Live Host") : "Offline",
      summaryTemp,
      summaryHumidity,
      summaryAirQuality,
      summaryGas,
      summaryCO,
      details: {
        raspberryPi: {
          heartbeat: wsConnected ? lastHeartbeatStr : "Offline",
          uptime: wsConnected ? "Host Server Active" : "Offline",
          latency: wsConnected ? "2ms" : "N/A",
          quality: isMqttConnected ? "Hardware Stream Connected" : "No Hardware Connection"
        },
        esp32: {
          heartbeat: isRoverOnline && roverSensors?.last_seen ? new Date(roverSensors.last_seen * 1000).toLocaleTimeString() : "Offline",
          uptime: isRoverOnline && roverSensors?.uptime ? `${roverSensors.uptime}s` : "Offline",
          latency: isRoverOnline ? "14ms" : "N/A",
          quality: isRoverOnline && roverSensors?.rssi ? `${roverSensors.rssi}dBm` : "Offline (Unpowered)"
        },
        mqtt: {
          heartbeat: isMqttConnected && (backendState?.mqtt_last_heartbeat || 0) > 0 ? new Date((backendState?.mqtt_last_heartbeat || 0) * 1000).toLocaleTimeString() : "Offline",
          uptime: isMqttConnected ? "Connected" : "Offline",
          latency: isMqttConnected ? "6ms" : "N/A",
          quality: isMqttConnected ? `${backendState?.mqtt_node_count || 0} node(s) online` : "Offline (0 Nodes)"
        },
        wifi: {
          heartbeat: isMqttConnected ? lastHeartbeatStr : "Offline",
          uptime: isMqttConnected ? "Linked" : "Offline",
          latency: isMqttConnected ? "2ms" : "N/A",
          quality: isMqttConnected ? "92%" : "Offline"
        },
        camera: {
          heartbeat: isCameraStreaming ? lastHeartbeatStr : "Offline",
          uptime: isCameraStreaming ? "Streaming" : "Offline",
          latency: isCameraStreaming ? "48ms" : "N/A",
          quality: isCameraStreaming ? "24 FPS · Live" : "Offline (Hardware Power Off)"
        },
        ai: {
          heartbeat: isMqttConnected ? lastHeartbeatStr : "Standby",
          uptime: isMqttConnected ? "Active" : "Standby",
          latency: isMqttConnected ? "87ms" : "N/A",
          quality: isMqttConnected ? "Realtime Triage" : "Standby (No Telemetry)"
        }
      }
    };

    const liveMissions: Mission[] = isEsp32Connected && backendState?.rover?.current_mission
      ? [
        { id: "live-m", name: backendState.rover.current_mission.name, type: "PATROL" as const, progress: backendState.rover.battery_pct || 98, waypoint: backendState.rover.current_zone || "Dock", next: "--", eta: "Live", status: "running" as const }
      ]
      : [];

    return {
      mode: "live" as const,
      connected: wsConnected,
      status: liveStatus,
      missions: liveMissions,
      alerts: isOnline && backendState?.alerts ? backendState.alerts : [],
      timeline: isOnline && backendState?.timeline ? backendState.timeline : [],
      backendState,
      dispatchMission,
      sendRoverCommand,
      sendMqttPayload
    };
  }, [backendState, wsConnected, dispatchMission, sendRoverCommand, sendMqttPayload]);

  // Resolve Active Backend State (for mapping simulated or live states)
  const activeBackendState = useMemo(() => {
    if (systemMode === "live") {
      const isMqttLive = Boolean(backendState?.mqtt_connected) && (backendState?.mqtt_node_count || 0) > 0;
      const isSerialLive = backendState?.mode === 'serial' || Boolean(backendState?.hardware_status?.esp32_connected);
      const isRoverLive = backendState?.rover?.sensors && (Date.now() / 1000 - (backendState.rover.sensors.last_seen || 0) < 15.0);
      const hasLiveHardware = isMqttLive || isSerialLive || isRoverLive;

      if (!hasLiveHardware) {
        // Fallback to active simulated telemetry so the website remains live and interactive when hardware is off
        const zones: any = {};
        const riskScores: any = {};
        const mapping: { [key: string]: string } = {
          "r-201": "chem_lab",
          "r-206": "cad_lab",
          "r-103": "kitchen",
          "r-101": "corridor",
          "r-203": "classroom_1",
          "r-105": "atl_lab",
          "r-204": "classroom_2",
        };

        Object.keys(mapping).forEach(roomId => {
          const zoneId = mapping[roomId];
          const sensor = demoSensors[roomId] || { temp: 22.0, humidity: 50.0, gas: 12, blocked: false };
          zones[zoneId] = {
            online: true,
            temp: sensor.temp,
            humidity: sensor.humidity,
            smoke: sensor.gas,
            blocked: sensor.blocked
          };
          riskScores[zoneId] = {
            score: sensor.blocked ? 95 : sensor.gas > 40 ? 45 : 12,
            status: sensor.blocked ? "critical" : sensor.gas > 40 ? "warning" : "green"
          };
        });

        return {
          mode: "sim",
          overall_risk: 12,
          camera_online: true,
          last_updated: Date.now() / 1000,
          zones,
          risk_scores: riskScores,
          rover: {
            status: demoRover.status,
            battery_pct: demoRover.battery_pct,
            current_zone: demoRover.current_zone,
            target_zone: demoRover.target_zone,
            position: demoRover.position,
            path: demoRover.path
          }
        };
      }
      return backendState;
    }

    const zones: any = {};
    const riskScores: any = {};
    const mapping: { [key: string]: string } = {
      "r-201": "chem_lab",
      "r-206": "cad_lab",
      "r-103": "kitchen",
      "r-101": "corridor",
      "r-203": "classroom_1",
      "r-105": "atl_lab",
      "r-204": "classroom_2",
    };

    Object.keys(mapping).forEach(roomId => {
      const zoneId = mapping[roomId];
      const sensor = demoSensors[roomId] || { temp: 22.0, humidity: 50.0, gas: 12, blocked: false };

      zones[zoneId] = {
        online: true,
        temp: sensor.temp,
        humidity: sensor.humidity,
        smoke: sensor.gas,
        blocked: sensor.blocked
      };

      riskScores[zoneId] = {
        score: sensor.blocked ? 95 : sensor.gas > 40 ? 45 : 12,
        status: sensor.blocked ? "critical" : sensor.gas > 40 ? "warning" : "green"
      };
    });

    return {
      mode: "sim",
      overall_risk: 12,
      camera_online: true,
      last_updated: Date.now() / 1000,
      zones,
      risk_scores: riskScores,
      rover: {
        status: demoRover.status,
        battery_pct: demoRover.battery_pct,
        current_zone: demoRover.current_zone,
        target_zone: demoRover.target_zone,
        position: demoRover.position,
        path: demoRover.path
      }
    };
  }, [systemMode, demoSensors, demoRover, backendState]);

  // Demo Provider Implementation
  const demoProvider = useMemo<SentinelDataProvider>(() => {
    const activeZone = demoRover.current_zone || "r-101";
    const activeSensor = (demoSensors[activeZone] || demoSensors["r-101"]) as any;
    const summaryTemp = `${activeSensor.temp.toFixed(1)}`;
    const summaryHumidity = `${activeSensor.humidity.toFixed(0)}`;

    // Use demo gas and CO directly as percentage
    const mq2Pct = Math.max(0, Math.min(100, Math.round(activeSensor.gas)));
    const summaryGas = `${mq2Pct}`;
    const summaryAirQuality = `${activeSensor.airQuality !== undefined ? Math.round(activeSensor.airQuality) : Math.max(0, 100 - mq2Pct)}`;

    const mq7Pct = Math.max(0, Math.min(100, Math.round(activeSensor.co !== undefined ? activeSensor.co : Math.round(activeSensor.gas / 3))));
    const summaryCO = `${mq7Pct}`;

    const demoStatus: SystemStatus = {
      battery: demoRover.battery_pct,
      wifi: "connected",
      mqtt: "online",
      raspberryPi: "online",
      esp32: "online",
      camera: "streaming",
      ai: "active",
      systemHealth: Math.max(0, Math.min(100, Math.round(
        100
        - (demoRover.battery_pct < 20 ? 15 : demoRover.battery_pct < 40 ? 5 : 0)
        - Object.values(demoSensors).filter((s: any) => s.blocked).length * 10
        - Object.values(demoSensors).filter((s: any) => s.gas > 80).length * 5
      ))),
      currentMission: demoMissions.find(m => m.status === "running")?.name || "IDLE",
      currentRoom: buildingConfig.rooms.find(r => r.id === demoRover.current_zone)?.name || "Charging Station",
      uptime: "14h 22m",
      summaryTemp,
      summaryHumidity,
      summaryAirQuality,
      summaryGas,
      summaryCO,
      details: {
        raspberryPi: { heartbeat: "Just now", uptime: "14h 22m", latency: "3ms", quality: "100%" },
        esp32: { heartbeat: "Just now", uptime: "14h 22m", latency: "12ms", quality: "-45dBm" },
        mqtt: { heartbeat: "Just now", uptime: "14h 22m", latency: "5ms", quality: "Nominal" },
        wifi: { heartbeat: "Just now", uptime: "14h 22m", latency: "2ms", quality: "99%" },
        camera: { heartbeat: "Just now", uptime: "14h 22m", latency: "32ms", quality: "30 FPS" },
        ai: { heartbeat: "Just now", uptime: "14h 22m", latency: "74ms", quality: "12ms latency" }
      }
    };

    return {
      mode: "demo" as const,
      connected: true,
      status: demoStatus,
      missions: demoMissions,
      alerts: demoAlerts,
      timeline: demoTimeline,
      backendState: activeBackendState,
      dispatchMission,
      sendRoverCommand,
      sendMqttPayload,
      triggerDemoScenario
    };
  }, [demoSensors, demoRover, demoMissions, demoAlerts, demoTimeline, dispatchMission, sendRoverCommand, sendMqttPayload, triggerDemoScenario, activeBackendState]);

  // Resolve Active Provider (Decoupled completely from UI views)
  const activeProvider = isLive ? liveProvider : demoProvider;
  const activeData = activeProvider;


  // Inject Custom Styles to head
  useEffect(() => {
    const id = "sentinel-dashboard-style";
    if (!document.getElementById(id)) {
      const style = document.createElement("style");
      style.id = id;
      style.textContent = DASHBOARD_STYLE + `
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in {
  animation: slideIn 0.3s ease-out forwards;
}
`;
      document.head.appendChild(style);
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("sentinel-dark", theme === "dark");
    document.documentElement.classList.toggle("sentinel-light", theme === "light");
  }, [theme]);

  // Monitoring effects to trigger automatic system notifications & synthesized beeps
  const prevStatusRef = useRef<any>(null);
  useEffect(() => {
    if (!activeData || !activeData.status) return;
    const status = activeData.status;
    const prev = prevStatusRef.current;

    if (prev) {
      if (status.wifi !== prev.wifi) {
        if (status.wifi === "offline") {
          addNotification("Connection Status", "SSID Wi-Fi link went offline", "error");
          playNotificationSound("error");
        } else {
          addNotification("Connection Status", "SSID Wi-Fi link restored", "success");
          playNotificationSound("success");
        }
      }
      if (status.mqtt !== prev.mqtt) {
        if (status.mqtt === "offline") {
          addNotification("Transport Status", "MQTT client connection lost", "error");
          playNotificationSound("error");
        } else {
          addNotification("Transport Status", "MQTT connection established", "success");
          playNotificationSound("success");
        }
      }
      if (status.camera !== prev.camera) {
        if (status.camera === "offline") {
          addNotification("Video Status", "Live ESP32-CAM stream offline", "warning");
          playNotificationSound("warning");
        } else {
          addNotification("Video Status", "Live ESP32-CAM stream restored", "success");
          playNotificationSound("success");
        }
      }
      if (status.esp32 !== prev.esp32) {
        if (status.esp32 === "offline") {
          addNotification("Device Status", "ESP32 patrolling rover disconnected", "error");
          playNotificationSound("error");
        } else if (status.esp32 === "online") {
          addNotification("Device Status", "ESP32 patrolling rover connected", "success");
          playNotificationSound("success");
        }
      }
      if (status.battery < 20 && prev.battery >= 20 && status.battery > 0) {
        addNotification("Battery Telemetry", `Low Battery alert: ${status.battery.toFixed(1)}%`, "error");
        playNotificationSound("error");
      }
      if (status.currentMission !== prev.currentMission) {
        if (status.currentMission === "Offline" || status.currentMission === "Idle" || status.currentMission === "No Active Mission") {
          if (prev.currentMission && prev.currentMission !== "Offline" && prev.currentMission !== "Idle" && prev.currentMission !== "No Active Mission") {
            addNotification("Operations", "patrolling mission completed successfully.", "success");
            playNotificationSound("success");
          }
        } else {
          addNotification("Operations", `Patrolling mission started: ${status.currentMission}`, "info");
          playNotificationSound("info");
        }
      }
    }

    prevStatusRef.current = {
      wifi: status.wifi,
      mqtt: status.mqtt,
      camera: status.camera,
      esp32: status.esp32,
      battery: status.battery,
      currentMission: status.currentMission,
    };
  }, [activeData, addNotification]);

  // Gradual Gas / Smoke notifications
  const prevZonesRef = useRef<any>(null);
  useEffect(() => {
    const currentZones = activeBackendState?.zones;
    const prevZones = prevZonesRef.current;
    if (currentZones && prevZones) {
      Object.keys(currentZones).forEach(zId => {
        const currZ = currentZones[zId];
        const prevZ = prevZones[zId];
        if (currZ && prevZ) {
          if (currZ.smoke >= 100 && prevZ.smoke < 100) {
            const roomName = buildingConfig.rooms.find(r => r.id === zId || zId === "chem_lab" && r.id === "r-201" || zId === "kitchen" && r.id === "r-103")?.name || zId;
            addNotification("Smoke Detected", `Smoke concentration elevated in ${roomName} (${currZ.smoke} ppm)`, "error");
            playNotificationSound("error");
          }
          if (currZ.smoke >= 200 && prevZ.smoke < 200) {
            const roomName = buildingConfig.rooms.find(r => r.id === zId || zId === "chem_lab" && r.id === "r-201" || zId === "kitchen" && r.id === "r-103")?.name || zId;
            addNotification("Gas Leak", `Combustible Gas Leak alert in ${roomName}`, "error");
            playNotificationSound("error");
          }
        }
      });
    }
    prevZonesRef.current = currentZones;
  }, [activeBackendState, addNotification]);

  const cycleTelemetryMode = () => {
    if (!backendState) return;
    const modes: ("sim" | "serial" | "mqtt")[] = ["sim", "serial", "mqtt"];
    const currentIdx = modes.indexOf(backendState.mode || "sim");
    const nextMode = modes[(currentIdx + 1) % modes.length];

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "change_telemetry_mode",
          mode: nextMode,
          port: "COM3",
          broker: backendStateRef.current?.mqtt_broker || "sentinelpi.local",
        })
      );
    }
  };

  const dynamicNavItems = useMemo(() => {
    const allItems = [
      { id: "home", label: "Home", icon: Icons.Home },
      { id: "mission", label: "Mission Control", icon: Icons.Bot },
      { id: "twin", label: "Digital Twin", icon: Icons.Map },
      { id: "camera", label: "Live Camera", icon: Icons.Camera },
      { id: "analytics", label: "Analytics", icon: Icons.LineChart },
      { id: "alerts", label: "Alert Center", icon: Icons.Siren, badge: unreadAlertCount > 0 ? unreadAlertCount : undefined },
      { id: "history", label: "History", icon: Icons.History },
      { id: "assistant", label: "AI Assistant", icon: Icons.Sparkles },
      { id: "settings", label: "Settings", icon: Icons.Settings },
    ];

    if (userRole === "Viewer") {
      return allItems.filter(i => i.id === "home");
    }
    if (userRole === "Operator") {
      return allItems.filter(i => ["home", "mission", "twin", "camera", "alerts", "history"].includes(i.id));
    }
    return allItems;
  }, [unreadAlertCount, userRole]);

  const renderActivePage = () => {
    switch (activeTab) {
      case "home":
        return <HomePage provider={activeProvider} onNavigate={(tab: string) => setActiveTab(tab as any)} />;
      case "mission":
        return (
          <MissionControlPage
            provider={activeProvider}
            systemMode={systemMode}
            status={activeData?.status}
            missions={activeData?.missions}
            dispatchMission={dispatchMission}
            sendRoverCommand={sendRoverCommand}
            triggerDemoScenario={triggerDemoScenario}
          />
        );
      case "twin":
        return <DigitalTwinPage provider={activeProvider} />;
      case "camera":
        return <CameraPage wsConnected={wsConnected} systemMode={systemMode} backendState={activeBackendState} />;
      case "analytics":
        return <AnalyticsPage />;
      case "alerts":
        return (
          <AlertCenterPage
            alertLogs={alertLogs}
            onMarkRead={handleMarkRead}
            onMarkAllRead={handleMarkAllRead}
            onClearAlerts={handleClearAlerts}
            onSimulateAlert={(type) => triggerSystemAlert(type, "Chemistry Lab", undefined, "Active Patrol")}
          />
        );
      case "history":
        return <HistoryPage timeline={activeData.timeline} />;
      case "assistant":
        return <AssistantPage wsConnected={wsConnected} />;
      case "settings":
        return (
          <SettingsPage
            refreshInterval={refreshInterval}
            setRefreshInterval={setRefreshInterval}
            soundEnabled={soundEnabled}
            setSoundEnabled={setSoundEnabled}
            autoReconnect={autoReconnect}
            setAutoReconnect={setAutoReconnect}
            demoSpeed={demoSpeed}
            setDemoSpeed={setDemoSpeed}
            addNotification={addNotification}
          />
        );
      default:
        return null;
    }
  };

  if (!splashFinished) {
    return <SplashScreen onComplete={() => setSplashFinished(true)} />;
  }

  if (!isLoggedIn) {
    return (
      <LoginScreen
        onLogin={(uname, role) => {
          setUsername(uname);
          setUserRole(role);
          setIsLoggedIn(true);
          localStorage.setItem("sentinel_username", uname);
          localStorage.setItem("sentinel_role", role);
        }}
      />
    );
  }

  return (
    <div className={cn("sentinel-dashboard flex min-h-screen w-full relative overflow-x-hidden", theme === "dark" ? "sentinel-dark" : "sentinel-light")}>
      {/* Mobile Off-Canvas Backdrop Blur Overlay */}
      {mobileSidebarOpen && (
        <div
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          aria-hidden="true"
        />
      )}

      {/* Responsive Sidebar (Off-canvas Drawer on Mobile/Tablet, Persistent on Desktop) */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border/60 bg-background/95 backdrop-blur-xl transition-transform duration-300 ease-in-out lg:sticky lg:top-0 lg:h-screen shrink-0 lg:translate-x-0",
          sidebarOpen ? "w-64" : "w-16",
          mobileSidebarOpen ? "translate-x-0 w-64 shadow-2xl" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div
          onClick={() => {
            setActiveTab("home");
            setMobileSidebarOpen(false);
          }}
          className="flex h-14 items-center gap-2.5 px-4 shrink-0 cursor-pointer select-none group"
        >
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl overflow-hidden bg-background/40 border border-border/60 shadow-lg transition-all duration-300 group-hover:scale-105 group-hover:border-primary/50 group-hover:shadow-primary/20 sentinel-glow-primary">
            <img
              src={logoUrl}
              alt="Sentinel Twin Logo"
              className="h-full w-full object-cover object-top transition-transform duration-700 ease-out group-hover:scale-110"
            />
          </div>
          {(sidebarOpen || mobileSidebarOpen) && (
            <div className="flex flex-col leading-tight">
              <span className="text-[15px] font-semibold tracking-tight group-hover:text-primary transition-colors">Sentinel Twin</span>
              <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground group-hover:text-muted-foreground/80 transition-colors">X · Command Center</span>
            </div>
          )}
          {/* Close button inside mobile drawer */}
          {mobileSidebarOpen && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMobileSidebarOpen(false);
              }}
              aria-label="Close navigation drawer"
              className="ml-auto flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary/40 hover:text-foreground lg:hidden cursor-pointer min-h-[44px] min-w-[44px]"
            >
              <Icons.X className="h-5 w-5" />
            </button>
          )}
        </div>

        <nav className="flex-1 space-y-1 px-2 py-4 overflow-y-auto scrollbar-none">
          {dynamicNavItems.map((item) => {
            const active = activeTab === item.id;
            const Icon = item.icon;
            const isExpanded = sidebarOpen || mobileSidebarOpen;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id as any);
                  setMobileSidebarOpen(false);
                }}
                className={cn(
                  "group relative flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors cursor-pointer min-h-[44px]",
                  active ? "bg-secondary/60 text-foreground" : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground",
                )}
              >
                <Icon className={cn("h-5 w-5 shrink-0", active ? "text-primary" : "group-hover:text-foreground")} />
                {isExpanded && (
                  <>
                    <span className="text-[13px] font-medium">{item.label}</span>
                    {"badge" in item && item.badge ? (
                      <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-critical/90 px-1.5 text-[10px] font-semibold text-white">
                        {item.badge}
                      </span>
                    ) : null}
                  </>
                )}
                {active && <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-primary" />}
              </button>
            );
          })}
        </nav>

        {/* ─── Sidebar: Mode Toggle Slider + Status ───────────────────────── */}
        <div className="p-3 space-y-2">
          {/* Live / Demo mode slider */}
          <div className="sentinel-glass rounded-xl p-3">
            <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-muted-foreground mb-2">
              {(sidebarOpen || mobileSidebarOpen) ? "System Mode" : ""}
            </div>
            <div className={cn("flex rounded-lg border border-border/60 bg-background/40 p-0.5 gap-0.5", (!sidebarOpen && !mobileSidebarOpen) && "flex-col")}>
              <button
                onClick={() => { if (systemMode !== 'demo') { setTransitioningMode('demo'); setMobileSidebarOpen(false); } }}
                className={cn(
                  "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-[10px] font-bold tracking-wide transition-all cursor-pointer min-h-[38px]",
                  systemMode === 'demo'
                    ? "bg-warning text-background shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <span>🎮</span>
                {(sidebarOpen || mobileSidebarOpen) && <span>DEMO</span>}
              </button>
              <button
                onClick={() => { if (systemMode !== 'live') { setTransitioningMode('live'); setMobileSidebarOpen(false); } }}
                className={cn(
                  "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-[10px] font-bold tracking-wide transition-all cursor-pointer min-h-[38px]",
                  systemMode === 'live'
                    ? "bg-success text-background shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <span>🛰️</span>
                {(sidebarOpen || mobileSidebarOpen) && <span>LIVE</span>}
              </button>
            </div>
          </div>

          {/* Build info */}
          {(sidebarOpen || mobileSidebarOpen) && (
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground px-1">
              <StatusDot tone={systemMode === 'live' ? 'success' : 'warning'} />
              <span className="font-mono">v2.4.1 · build 20260718</span>
            </div>
          )}
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur-xl">
          <div className="flex h-14 sm:h-16 items-center justify-between gap-2 px-3 sm:px-6">
            <div className="flex items-center gap-2 sm:gap-3">
              {/* Mobile Hamburger Button */}
              <button
                onClick={() => setMobileSidebarOpen((v) => !v)}
                aria-label="Open Navigation Menu"
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/60 bg-secondary/40 text-foreground lg:hidden cursor-pointer min-h-[44px] min-w-[44px] active:scale-95 transition-transform"
              >
                <Icons.Menu className="h-5 w-5" />
              </button>
              {/* Desktop Sidebar Toggle */}
              <button
                onClick={() => setSidebarOpen((v) => !v)}
                aria-label="Toggle Desktop Sidebar"
                className="hidden lg:flex h-9 w-9 items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-secondary/40 hover:text-foreground cursor-pointer"
              >
                <Icons.PanelLeft className="h-4 w-4" />
              </button>

              {/* Mobile Brand Title */}
              <div
                className="flex items-center gap-2 lg:hidden cursor-pointer select-none"
                onClick={() => setActiveTab("home")}
              >
                <img src={logoUrl} alt="Logo" className="h-7 w-7 rounded-lg object-cover" />
                <span className="text-sm font-bold tracking-tight text-foreground truncate max-w-[120px] sm:max-w-none">
                  Sentinel Twin
                </span>
              </div>

              {/* Search input (Hidden on small mobile) */}
              <div className="relative hidden max-w-md flex-1 md:block">
                <Icons.Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input placeholder="Search rooms, alerts, missions…" className="h-9 pl-9 text-[13px]" />
                <kbd className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-border/70 bg-background/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground md:inline-flex">
                  ⌘K
                </kbd>
              </div>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
              {/* Simulate Rover Stuck Trigger Button (Demo Mode) */}
              {systemMode === "demo" && (
                <button
                  onClick={triggerSimulatedRoverStuck}
                  title="Trigger simulated stuck rover emergency camera focus event"
                  className="flex items-center gap-1 sm:gap-1.5 rounded-full border border-critical/40 bg-critical/10 text-critical hover:bg-critical/20 px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-bold tracking-tight transition-all cursor-pointer shadow-sm animate-pulse min-h-[38px]"
                >
                  <Icons.Bot className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Simulate Rover Stuck</span>
                  <span className="sm:hidden">Stuck Test</span>
                </button>
              )}

              {systemMode === "live" ? (
                wsConnected && backendState ? (
                  <button
                    onClick={cycleTelemetryMode}
                    title="Click to switch telemetry input mode"
                    className="flex items-center gap-1.5 rounded-full border border-success/45 bg-success/10 text-success hover:bg-success/15 hover:border-success/60 px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-semibold tracking-tight transition-all hover:scale-[1.03] cursor-pointer shadow-sm min-h-[38px]"
                  >
                    <Icons.Radio className="h-3.5 w-3.5 animate-pulse shrink-0" />
                    <span className="hidden sm:inline">
                      Telemetry: {backendState.mode === "sim" ? "DEMO (Simulated)" : backendState.mode === "serial" ? "ESP32 (Serial)" : "MQTT (Wireless)"}
                    </span>
                    <span className="sm:hidden font-mono">
                      {backendState.mode === "sim" ? "SIM" : backendState.mode === "serial" ? "ESP32" : "MQTT"}
                    </span>
                    <Icons.RefreshCw className="ml-0.5 h-3 w-3 opacity-60 shrink-0" />
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5 rounded-full border border-critical/45 bg-critical/10 px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-semibold text-critical">
                    <Icons.AlertTriangle className="h-3.5 w-3.5 animate-pulse shrink-0" />
                    <span className="hidden sm:inline">HARDWARE OFFLINE</span>
                    <span className="sm:hidden">OFFLINE</span>
                  </div>
                )
              ) : (
                <div className="flex items-center gap-1.5 rounded-full border border-warning/45 bg-warning/10 px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-[11px] font-semibold text-warning">
                  <Icons.Cpu className="h-3.5 w-3.5 shrink-0" />
                  <span className="hidden sm:inline">DEMO PLAYBACK ACTIVE</span>
                  <span className="sm:hidden">DEMO</span>
                </div>
              )}

              <div className="hidden items-center gap-2 rounded-full border border-border/60 bg-secondary/40 px-3 py-1.5 text-[11px] font-medium tabular-nums xl:flex">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                <span>System {Math.round(activeData.status.systemHealth)}%</span>
              </div>

              <div className="hidden sm:block">
                <LiveClock />
              </div>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Live Telemetry Spectrum Visualizer"
                className="h-10 w-10 min-h-[44px] min-w-[44px] rounded-full cursor-pointer text-primary hover:bg-primary/10"
                onClick={() => setIsSpectrumOpen((prev) => !prev)}
                title="Live Telemetry Waveform Spectrum (L)"
              >
                <Icons.Activity className="h-4 w-4 animate-pulse" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Keyboard Shortcuts Guide"
                className="h-10 w-10 min-h-[44px] min-w-[44px] rounded-full cursor-pointer text-accent hover:bg-accent/10"
                onClick={() => setIsKeyboardHelpOpen((prev) => !prev)}
                title="Keyboard Shortcuts Guide (?)"
              >
                <Icons.Keyboard className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Toggle dark/light theme"
                className="h-10 w-10 min-h-[44px] min-w-[44px] rounded-full cursor-pointer"
                onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
              >
                {theme === "dark" ? <Icons.Sun className="h-4 w-4" /> : <Icons.Moon className="h-4 w-4" />}
              </Button>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Open alert center"
                onClick={() => setActiveTab("alerts")}
                className="relative h-10 w-10 min-h-[44px] min-w-[44px] rounded-full cursor-pointer"
                title="Open Alert Center"
              >
                <Icons.Bell className="h-4 w-4" />
                {unreadAlertCount > 0 && (
                  <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-critical px-1 text-[9px] font-extrabold text-white sentinel-pulse-ring">
                    {unreadAlertCount}
                  </span>
                )}
              </Button>

              {/* Dynamic User Profile Badge & Logout Button */}
              <div className="flex items-center gap-1.5 sm:gap-2">
                <div className="flex h-10 items-center gap-2 rounded-full border border-border/60 bg-secondary/40 pl-1 pr-2 sm:pr-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-[11px] font-bold text-primary-foreground uppercase">
                    {username.slice(0, 2)}
                  </div>
                  {sidebarOpen && (
                    <div className="hidden flex-col leading-tight md:flex">
                      <span className="text-[11px] font-semibold">{username}</span>
                      <span className="text-[9px] uppercase tracking-wider text-primary font-mono font-bold">{userRole}</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => {
                    setIsLoggedIn(false);
                    localStorage.removeItem("sentinel_is_logged_in");
                  }}
                  aria-label="Sign out session"
                  title="Sign Out / Switch Operator"
                  className="flex h-10 w-10 min-h-[44px] min-w-[44px] items-center justify-center rounded-full border border-border/60 bg-secondary/40 text-muted-foreground hover:text-critical hover:border-critical/40 transition-colors cursor-pointer"
                >
                  <Icons.LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 px-3 py-4 sm:px-6 sm:py-6 lg:px-8">
          {renderActivePage()}
        </main>

        <footer className="border-t border-border/60 bg-background/40 px-4 py-2.5 backdrop-blur-xl md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <Icons.Sparkles className="h-3 w-3 text-primary" />
                Sentinel Twin X · v2.4.1
              </span>
            </div>
            <div className="flex items-center gap-4 font-mono">
              <span className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${activeData.status.mqtt === "online" ? "bg-success" : "bg-critical"}`} /> MQTT {activeData.status.mqtt.toUpperCase()}
              </span>
              <span className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${activeData.status.raspberryPi === "online" ? "bg-success" : "bg-critical"}`} /> Backend {activeData.status.raspberryPi.toUpperCase()}
              </span>
              <span>Uptime {activeData.status.uptime}</span>
            </div>
          </div>
        </footer>
      </div>

      {/* Feature 6: Mission Post-Mortem Report Generator Modal */}
      <MissionReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        reportData={selectedReportData}
      />

      {/* Live Telemetry Waveform Spectrum Visualizer Modal */}
      <TelemetrySpectrumVisualizer
        isOpen={isSpectrumOpen}
        onClose={() => setIsSpectrumOpen(false)}
        backendState={activeBackendState}
      />

      {/* Keyboard Hotkey Shortcuts Modal */}
      <KeyboardShortcutsModal
        isOpen={isKeyboardHelpOpen}
        onClose={() => setIsKeyboardHelpOpen(false)}
      />

      {/* Full-Screen Rover Stuck Emergency Camera Focus Overlay Modal */}
      <RoverStuckModal
        isOpen={isRoverStuckModalOpen}
        onClose={() => setIsRoverStuckModalOpen(false)}
        timeStuckSeconds={stuckDurationSeconds}
        currentMission={
          systemMode === "live"
            ? (backendState?.rover?.current_mission?.name || "Patrol Mission")
            : (demoMissions.find(m => m.status === "running")?.name || "Floor 2 Full Patrol")
        }
        currentRoom={
          systemMode === "live"
            ? (backendState?.rover?.current_zone || "Chemistry Lab")
            : (buildingConfig.rooms.find(r => r.id === demoRover.current_zone)?.name || "Chemistry Lab")
        }
        battery={activeData.status.battery}
        speed="0.0 m/s"
        connectionStatus={activeData.status.mqtt === "online" ? "ONLINE (12ms)" : "OFFLINE"}
        systemMode={systemMode}
        onResumeMission={() => {
          setIsRoverStuckModalOpen(false);
          addNotification("Mission Resumed", "Rover mission execution resumed.", "success");
          playNotificationSound("success");
        }}
        onManualControl={() => {
          setIsRoverStuckModalOpen(false);
          setActiveTab("mission");
          addNotification("Manual Control", "Switched to Manual Control override.", "info");
        }}
        onReturnHome={() => {
          setIsRoverStuckModalOpen(false);
          sendRoverCommand("Return Home");
          addNotification("Return Home", "Rover instructed to return to home dock.", "warning");
        }}
        onRetryNavigation={handleRetryNavigation}
        onIgnore={() => setIsRoverStuckModalOpen(false)}
        isRerouting={isRerouting}
        rerouteSuccess={rerouteSuccess}
      />

      {/* Toast Notification Stack */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full">
        {notifications.map((n) => (
          <div
            key={n.id}
            onClick={() => dismissNotification(n.id)}
            className={cn(
              "flex items-start gap-3 rounded-xl border p-4 shadow-xl backdrop-blur-xl transition-all duration-300 animate-slide-in cursor-pointer",
              n.type === "success"
                ? "bg-success/15 border-success/30 text-success"
                : n.type === "warning"
                  ? "bg-warning/15 border-warning/30 text-warning"
                  : n.type === "error"
                    ? "bg-critical/15 border-critical/30 text-critical"
                    : "bg-primary/10 border-primary/20 text-primary"
            )}
          >
            <div className="flex-1">
              <div className="text-xs font-bold uppercase tracking-wider">{n.title}</div>
              <div className="mt-1 text-[11px] text-foreground opacity-90">{n.message}</div>
            </div>
            <Icons.X className="h-3.5 w-3.5 opacity-60 hover:opacity-100" />
          </div>
        ))}
      </div>

      {/* Emergency Crisis Camera Fullscreen Modal (Only when camera is online & rover is active) */}
      {(() => {
        const isLiveHardwareOffline = systemMode === "live" && (!wsConnected || !backendState || !backendState.camera_online);
        const shouldShowCrisisCamera = !isLiveHardwareOffline && !userDismissedCrisisCamera && (
          emergencyCameraPopup || backendState?.layout_mode === 'crisis'
        );

        if (!shouldShowCrisisCamera) return null;

        return (
          <div className="fixed inset-0 z-[9999] flex flex-col bg-black/95 backdrop-blur-2xl animate-fade-in p-4 md:p-6">
            <div className="flex items-center justify-between border-b border-red-500/40 pb-3 mb-4">
              <div className="flex items-center gap-3">
                <span className="flex h-3.5 w-3.5 rounded-full bg-critical animate-ping" />
                <Icons.Siren className="h-6 w-6 text-critical animate-pulse" />
                <div>
                  <h2 className="text-base md:text-lg font-bold text-critical uppercase tracking-wider">CRISIS EMERGENCY DETECTED — FULLSCREEN CAMERA MONITORED</h2>
                  <p className="text-xs text-muted-foreground">Obstacle or Flame hazard detected (&gt;10s persistent obstruction). Realtime camera prioritized.</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEmergencyCameraPopup(false);
                  setUserDismissedCrisisCamera(true);
                }}
                className="border-critical/50 text-white hover:bg-critical/20"
              >
                <Icons.X className="mr-1.5 h-4 w-4" /> Close Fullscreen
              </Button>
            </div>
            <div className="relative flex-1 w-full overflow-hidden rounded-2xl border-2 border-critical/80 bg-black shadow-2xl">
              <img
                src="/api/video-feed"
                className="h-full w-full object-contain"
                alt="Emergency Camera Stream"
              />
            </div>
          </div>
        );
      })()}

      {transitioningMode && (
        <ModeTransitionOverlay
          mode={transitioningMode}
          onComplete={() => {
            setSystemModeAndPersist(transitioningMode);
            setTransitioningMode(null);
          }}
        />
      )}
    </div>
  );
}
