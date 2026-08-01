import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  sensorReadings: defineTable({
    zone_id: v.string(),
    temp: v.union(v.number(), v.null()),
    smoke: v.number(),
    humidity: v.union(v.number(), v.null()),
    blocked: v.boolean(),
    timestamp: v.number(),
  })
    .index("by_zone", ["zone_id"])
    .index("by_timestamp", ["timestamp"]),

  alerts: defineTable({
    zone_id: v.string(),
    risk_score: v.number(),
    status: v.string(),
    description: v.string(),
    timestamp: v.number(),
  })
    .index("by_zone", ["zone_id"])
    .index("by_timestamp", ["timestamp"]),

  missions: defineTable({
    mission_id: v.string(),
    mission_type: v.string(),
    status: v.string(),
    target_zones: v.array(v.string()),
    priority: v.number(),
    timestamp: v.number(),
  })
    .index("by_mission_id", ["mission_id"])
    .index("by_status", ["status"]),

  roverStatus: defineTable({
    status: v.string(),
    battery: v.number(),
    x: v.number(),
    y: v.number(),
    wifi_rssi: v.number(),
    uptime: v.number(),
    timestamp: v.number(),
  })
    .index("by_timestamp", ["timestamp"]),

  batteryHistory: defineTable({
    voltage: v.number(),
    percentage: v.number(),
    timestamp: v.number(),
  })
    .index("by_timestamp", ["timestamp"]),

  cameraEvents: defineTable({
    event_type: v.string(),
    confidence: v.number(),
    image_path: v.string(),
    timestamp: v.number(),
  })
    .index("by_timestamp", ["timestamp"]),

  reports: defineTable({
    summary: v.string(),
    analysis: v.string(),
    severity: v.string(),
    confidence: v.string(),
    recommendations_json: v.string(),
    timestamp: v.number(),
  })
    .index("by_timestamp", ["timestamp"]),

  analytics: defineTable({
    event_type: v.string(),
    metric_value: v.number(),
    meta_json: v.optional(v.string()),
    timestamp: v.number(),
  })
    .index("by_event_type", ["event_type"])
    .index("by_timestamp", ["timestamp"]),

  settings: defineTable({
    key: v.string(),
    value: v.string(),
    timestamp: v.number(),
  })
    .index("by_key", ["key"]),
});
