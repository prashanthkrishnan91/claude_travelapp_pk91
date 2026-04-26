import type { TripAdviceResponse } from "@/lib/concierge/types";

interface TripAdviceViewProps {
  response: TripAdviceResponse;
}

export function TripAdviceView({ response }: TripAdviceViewProps) {
  return (
    <section aria-label="trip advice" className="space-y-3">
      <p className="text-sm leading-relaxed text-slate-700">{response.response}</p>
      {response.suggestions.length > 0 ? (
        <ul className="space-y-2">
          {response.suggestions.map((suggestion) => (
            <li key={`${suggestion.type}-${suggestion.name}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <p className="font-medium text-slate-900">{suggestion.name}</p>
              <p className="text-xs text-slate-600">{suggestion.reason}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
