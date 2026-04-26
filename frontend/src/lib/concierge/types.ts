export const responseTypeSchema = [
  "place_recommendations",
  "trip_advice",
  "unsupported",
] as const;

export type ResponseType = (typeof responseTypeSchema)[number];

export interface ConciergeSuggestion {
  type: "attraction" | "restaurant";
  name: string;
  reason: string;
}

export interface PlaceRecommendationsResponse {
  responseType: "place_recommendations";
  response: string;
  intent: string;
  retrievalUsed: boolean;
  sourceStatus: string;
  cached?: boolean;
  liveProvider?: string | null;
  restaurants: unknown[];
  attractions: unknown[];
  hotels: unknown[];
  researchSources: unknown[];
  areas: string[];
  areaComparisons: unknown[];
  suggestions: ConciergeSuggestion[];
  sources: string[];
  warnings: string[];
}



export interface AdviceSection {
  heading: string;
  bodyMarkdown: string;
}

export interface AdviceCitation {
  label: string;
  url: string;
}

export interface TripAdviceResponse {
  responseType: "trip_advice";
  response: string;
  adviceSections: AdviceSection[];
  citations: AdviceCitation[];
  suggestions: ConciergeSuggestion[];
  metadata: Record<string, unknown>;
}

export interface UnsupportedResponse {
  responseType: "unsupported";
  code: string;
  message: string;
}

export type ConciergeResponse =
  | PlaceRecommendationsResponse
  | TripAdviceResponse
  | UnsupportedResponse;
