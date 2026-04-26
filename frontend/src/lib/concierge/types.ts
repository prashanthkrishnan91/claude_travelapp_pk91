import { z } from "zod";

export const responseTypeSchema = z.enum([
  "place_recommendations",
  "trip_advice",
  "unsupported",
]);

const suggestionSchema = z.object({
  type: z.enum(["attraction", "restaurant"]),
  name: z.string(),
  reason: z.string(),
});

export const placeRecommendationsSchema = z.object({
  responseType: z.literal("place_recommendations"),
  response: z.string(),
  intent: z.string(),
  retrievalUsed: z.boolean(),
  sourceStatus: z.string(),
  cached: z.boolean().optional(),
  liveProvider: z.string().nullable().optional(),
  restaurants: z.array(z.unknown()),
  attractions: z.array(z.unknown()),
  hotels: z.array(z.unknown()),
  researchSources: z.array(z.unknown()),
  areas: z.array(z.string()),
  areaComparisons: z.array(z.unknown()),
  suggestions: z.array(suggestionSchema),
  sources: z.array(z.string()),
  warnings: z.array(z.string()),
});

export const tripAdviceSchema = z.object({
  responseType: z.literal("trip_advice"),
  response: z.string(),
  suggestions: z.array(suggestionSchema).default([]),
  metadata: z.record(z.unknown()).default({}),
});

export const unsupportedSchema = z.object({
  responseType: z.literal("unsupported"),
  code: z.string(),
  message: z.string(),
});

export const conciergeResponseSchema = z.discriminatedUnion("responseType", [
  placeRecommendationsSchema,
  tripAdviceSchema,
  unsupportedSchema,
]);

export type ConciergeResponse = z.infer<typeof conciergeResponseSchema>;
