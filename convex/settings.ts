import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const setSetting = mutation({
  args: {
    key: v.string(),
    value: v.string(),
  },
  handler: async (ctx, args) => {
    // Check if setting already exists and update
    const existing = await ctx.db
      .query("settings")
      .filter((q) => q.eq(q.field("key"), args.key))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, {
        value: args.value,
        timestamp: Date.now() / 1000,
      });
      return existing._id;
    } else {
      return await ctx.db.insert("settings", {
        key: args.key,
        value: args.value,
        timestamp: Date.now() / 1000,
      });
    }
  },
});

export const getSettings = query({
  handler: async (ctx) => {
    return await ctx.db.query("settings").collect();
  },
});
