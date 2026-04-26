import {
  normalizeConciergeResponse,
  type ConciergeResponse as ConciergeResponsePayload,
} from "@/lib/concierge/types";
import { PlaceRecommendationsView } from "./PlaceRecommendationsView";
import { TripAdviceView } from "./TripAdviceView";
import { UnsupportedView } from "./UnsupportedView";

interface ConciergeResponseProps {
  response: ConciergeResponsePayload | Record<string, unknown>;
}

export function ConciergeResponse({ response }: ConciergeResponseProps) {
  const normalizedResponse = normalizeConciergeResponse(response);
  const responseType = normalizedResponse.responseType;

  if (responseType === "place_recommendations") {
    return <PlaceRecommendationsView response={normalizedResponse} />;
  }

  if (responseType === "trip_advice") {
    return <TripAdviceView response={normalizedResponse} />;
  }

  return <UnsupportedView response={normalizedResponse} />;
}
