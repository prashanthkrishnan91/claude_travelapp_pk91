import type { ConciergeSuggestion, PlaceRecommendationsResponse } from "@/lib/concierge/types";

interface PlaceRecommendationsViewProps {
  response: PlaceRecommendationsResponse;
}

interface PlaceCard {
  name?: string;
  cuisine?: string;
  category?: string;
  mapsLink?: string;
  bookingLink?: string;
  sourceUrl?: string;
  supportingDetails?: {
    categoryLabel?: string | null;
    metaLine?: string | null;
    whyPick?: { text?: string | null; generationMethod?: string | null } | string | null;
  } | null;
  evidence?: string[];
  whyPick?: { text?: string | null; generationMethod?: string | null } | string | null;
}

function parsePlaceCards(response: PlaceRecommendationsResponse): PlaceCard[] {
  const toCards = (items: unknown[]): PlaceCard[] => items.filter((item): item is PlaceCard => typeof item === "object" && item !== null);
  return [...toCards(response.restaurants), ...toCards(response.attractions), ...toCards(response.hotels)].filter((card) => Boolean(card.name));
}

function reasonForCard(card: PlaceCard, suggestions: ConciergeSuggestion[]): string {
  const matchingSuggestion = suggestions.find((s) => s.name.toLowerCase() === (card.name ?? "").toLowerCase());
  const fromSupporting = typeof card.supportingDetails?.whyPick === "string"
    ? card.supportingDetails?.whyPick
    : card.supportingDetails?.whyPick?.text;
  const fromTopLevel = typeof card.whyPick === "string" ? card.whyPick : card.whyPick?.text;
  return fromTopLevel ?? fromSupporting ?? matchingSuggestion?.reason ?? "Strong fit for this trip based on trusted place signals.";
}

export function PlaceRecommendationsView({ response }: PlaceRecommendationsViewProps) {
  const cards = parsePlaceCards(response);

  return (
    <section aria-label="place recommendations" className="space-y-3">
      <p className="text-sm text-slate-700">{response.response}</p>
      <div className="space-y-2">
        {cards.map((card) => {
          const title = card.name ?? "Recommended place";
          const category = card.supportingDetails?.categoryLabel ?? card.cuisine ?? card.category ?? "Recommendation";
          const meta = card.supportingDetails?.metaLine;
          const reason = reasonForCard(card, response.suggestions);
          const sourceLink = card.bookingLink ?? card.sourceUrl;

          return (
            <article key={title} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-slate-900">{title}</p>
                <p className="mt-0.5 text-xs text-slate-500">{category}</p>
                {meta ? <p className="mt-0.5 text-xs text-slate-500">{meta}</p> : null}
              </div>
              <div className="mt-2 rounded-lg bg-slate-50 px-2 py-1.5 text-xs text-slate-600">
                <span className="font-medium">Why this pick:</span> {reason}
              </div>
              {card.evidence?.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {card.evidence.map((chip) => (
                    <span key={`${title}-${chip}`} className="rounded-full bg-sky-50 px-2 py-0.5 text-[11px] text-sky-700 ring-1 ring-sky-200">
                      {chip}
                    </span>
                  ))}
                </div>
              ) : null}
              <div className="mt-2 flex items-center gap-2">
                <button type="button" className="rounded-lg bg-sky-600 px-2.5 py-1.5 text-[11px] font-medium text-white hover:bg-sky-700">
                  Add to Trip
                </button>
                {card.mapsLink ? (
                  <a href={card.mapsLink} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
                    Map
                  </a>
                ) : null}
                {sourceLink ? (
                  <a href={sourceLink} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
                    Source
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
