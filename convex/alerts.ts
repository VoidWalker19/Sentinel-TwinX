import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addAlert = mutation({
  args: {
    zone_id: v.string(),
    risk_score: v.number(),
    status: v.string(),
    description: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("alerts", {
      zone_id: args.zone_id,
      risk_score: args.risk_score,
      status: args.status,
      description: args.description,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getLatestAlerts = query({
  args: { limit: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("alerts")
      .order("desc")
      .take(args.limit);
  },
});
