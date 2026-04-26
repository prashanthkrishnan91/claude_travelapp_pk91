import type { UnsupportedResponse } from "@/lib/concierge/types";

interface UnsupportedViewProps {
  response: UnsupportedResponse;
}

export function UnsupportedView({ response }: UnsupportedViewProps) {
  return (
    <section aria-label="unsupported response" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
      <p className="text-sm font-semibold text-amber-900">Unsupported response type</p>
      <p className="mt-1 text-xs text-amber-800">{response.message || response.code}</p>
    </section>
  );
}
