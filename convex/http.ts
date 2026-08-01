import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

// 1. Sync Sensor Readings
http.route({
  path: "/sync_sensor_readings",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.sensorReadings.addReading, {
        zone_id: data.zone_id,
        temp: data.temp,
        smoke: data.smoke,
        humidity: data.humidity,
        blocked: data.blocked,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 2. Sync Alert
http.route({
  path: "/sync_alert",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.alerts.addAlert, {
        zone_id: data.zone_id,
        risk_score: data.risk_score,
        status: data.status,
        description: data.description,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 3. Sync Rover Status
http.route({
  path: "/sync_rover_status",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.roverStatus.updateStatus, {
        status: data.status,
        battery: data.battery,
        x: data.x,
        y: data.y,
        wifi_rssi: data.wifi_rssi,
        uptime: data.uptime,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 4. Sync Camera Event
http.route({
  path: "/sync_camera_event",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.cameraEvents.addEvent, {
        event_type: data.event_type,
        confidence: data.confidence,
        image_path: data.image_path,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 5. Sync AI Report
http.route({
  path: "/sync_ai_report",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.reports.addReport, {
        summary: data.summary,
        analysis: data.analysis,
        severity: data.severity,
        confidence: data.confidence,
        recommendations_json: data.recommendations_json,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 6. Sync Mission
http.route({
  path: "/sync_mission",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.missions.addMission, {
        mission_id: data.mission_id,
        mission_type: data.mission_type,
        status: data.status,
        target_zones: data.target_zones,
        priority: data.priority,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// 7. Sync Battery History
http.route({
  path: "/sync_battery_history",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const data = await request.json();
      await ctx.runMutation(api.batteryHistory.addRecord, {
        voltage: data.voltage,
        percentage: data.percentage,
      });
      return new Response(JSON.stringify({ status: "success" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }),
});

// Export the router
export default http;
