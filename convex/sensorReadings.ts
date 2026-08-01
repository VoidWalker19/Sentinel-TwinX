import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addReading = mutation({
  args: {
    zone_id: v.string(),
    temp: v.union(v.number(), v.null()),
    smoke: v.number(),
    humidity: v.union(v.number(), v.null()),
    blocked: v.boolean(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("sensorReadings", {
      zone_id: args.zone_id,
      temp: args.temp,
      smoke: args.smoke,
      humidity: args.humidity,
      blocked: args.blocked,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getLatestReadings = query({
  args: { limit: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sensorReadings")
      .order("desc")
      .take(args.limit);
  },
});
