import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const updateStatus = mutation({
  args: {
    status: v.string(),
    battery: v.number(),
    x: v.number(),
    y: v.number(),
    wifi_rssi: v.number(),
    uptime: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("roverStatus", {
      status: args.status,
      battery: args.battery,
      x: args.x,
      y: args.y,
      wifi_rssi: args.wifi_rssi,
      uptime: args.uptime,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getLatestStatus = query({
  handler: async (ctx) => {
    return await ctx.db
      .query("roverStatus")
      .order("desc")
      .first();
  },
});
