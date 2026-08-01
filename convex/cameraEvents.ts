import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addEvent = mutation({
  args: {
    event_type: v.string(),
    confidence: v.number(),
    image_path: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("cameraEvents", {
      event_type: args.event_type,
      confidence: args.confidence,
      image_path: args.image_path,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getEvents = query({
  args: { limit: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("cameraEvents")
      .order("desc")
      .take(args.limit);
  },
});
