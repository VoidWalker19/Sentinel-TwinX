import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addMission = mutation({
  args: {
    mission_id: v.string(),
    mission_type: v.string(),
    status: v.string(),
    target_zones: v.array(v.string()),
    priority: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("missions", {
      mission_id: args.mission_id,
      mission_type: args.mission_type,
      status: args.status,
      target_zones: args.target_zones,
      priority: args.priority,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getMissions = query({
  handler: async (ctx) => {
    return await ctx.db
      .query("missions")
      .order("desc")
      .collect();
  },
});
