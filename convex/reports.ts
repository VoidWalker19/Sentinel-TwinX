import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const addReport = mutation({
  args: {
    summary: v.string(),
    analysis: v.string(),
    severity: v.string(),
    confidence: v.string(),
    recommendations_json: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("reports", {
      summary: args.summary,
      analysis: args.analysis,
      severity: args.severity,
      confidence: args.confidence,
      recommendations_json: args.recommendations_json,
      timestamp: Date.now() / 1000,
    });
  },
});

export const getReports = query({
  args: { limit: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("reports")
      .order("desc")
      .take(args.limit);
  },
});
