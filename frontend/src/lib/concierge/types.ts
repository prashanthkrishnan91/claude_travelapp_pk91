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

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord {
  return (value !== null && typeof value === "object") ? (value as UnknownRecord) : {};
}

function readString(record: UnknownRecord, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") return value;
  }
  return undefined;
}

function normalizeAdviceSection(value: unknown): AdviceSection | null {
  const section = asRecord(value);
  const heading = readString(section, "heading");
  const bodyMarkdown = readString(section, "bodyMarkdown", "body_markdown");
  if (!heading || !bodyMarkdown) return null;
  return { heading, bodyMarkdown };
}

function normalizeAdviceCitation(value: unknown): AdviceCitation | null {
  const citation = asRecord(value);
  const label = readString(citation, "label");
  const url = readString(citation, "url");
  if (!label || !url) return null;
  return { label, url };
}

function readArray(record: UnknownRecord, ...keys: string[]): unknown[] {
  for (const key of keys) {
    const value = record[key];
    if (Array.isArray(value)) return value;
  }
  return [];
}

export function normalizeConciergeResponse(raw: unknown): ConciergeResponse {
  const record = asRecord(raw);
  const responseType = readString(record, "responseType", "response_type") ?? "unsupported";

  if (responseType === "place_recommendations") {
    return {
      responseType: "place_recommendations",
      response: readString(record, "response") ?? "",
      intent: readString(record, "intent") ?? "",
      retrievalUsed: Boolean(record.retrievalUsed ?? record.retrieval_used),
      sourceStatus: readString(record, "sourceStatus", "source_status") ?? "unknown",
      cached: typeof record.cached === "boolean" ? record.cached : undefined,
      liveProvider: readString(record, "liveProvider", "live_provider") ?? null,
      restaurants: readArray(record, "restaurants"),
      attractions: readArray(record, "attractions"),
      hotels: readArray(record, "hotels"),
      researchSources: readArray(record, "researchSources", "research_sources"),
      areas: readArray(record, "areas").filter((v): v is string => typeof v === "string"),
      areaComparisons: readArray(record, "areaComparisons", "area_comparisons"),
      suggestions: readArray(record, "suggestions").filter(
        (s): s is ConciergeSuggestion => typeof s === "object" && s !== null
          && typeof (s as UnknownRecord).name === "string"
          && typeof (s as UnknownRecord).type === "string"
          && typeof (s as UnknownRecord).reason === "string",
      ),
      sources: readArray(record, "sources").filter((v): v is string => typeof v === "string"),
      warnings: readArray(record, "warnings").filter((v): v is string => typeof v === "string"),
    };
  }

  if (responseType === "trip_advice") {
    const adviceSectionsRaw = Array.isArray(record.adviceSections)
      ? record.adviceSections
      : Array.isArray(record.advice_sections)
        ? record.advice_sections
        : [];
    const citationsRaw = readArray(record, "citations");
    return {
      responseType: "trip_advice",
      response: readString(record, "response") ?? "",
      adviceSections: adviceSectionsRaw
        .map((section) => normalizeAdviceSection(section))
        .filter((section): section is AdviceSection => Boolean(section)),
      citations: citationsRaw
        .map((citation) => normalizeAdviceCitation(citation))
        .filter((citation): citation is AdviceCitation => Boolean(citation)),
      suggestions: Array.isArray(record.suggestions) ? (record.suggestions as ConciergeSuggestion[]) : [],
      metadata: asRecord(record.metadata),
    };
  }

  return {
    responseType: "unsupported",
    code: readString(record, "code") ?? "unsupported_response_type",
    message: readString(record, "message") ?? `Response type '${responseType}' is not supported yet.`,
  };
}
