import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addRecord = mutation({
  args: {
    voltage: v.number(),
    percentage: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("batteryHistory", {
      voltage: args.voltage,
      percentage: args.percentage,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getHistory = query({
  args: { limit: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("batteryHistory")
      .order("desc")
      .take(args.limit);
  },
});
