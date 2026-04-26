import type { ConciergeResponse as ConciergeResponsePayload, UnsupportedResponse } from "@/lib/concierge/types";
import { PlaceRecommendationsView } from "./PlaceRecommendationsView";
import { TripAdviceView } from "./TripAdviceView";
import { UnsupportedView } from "./UnsupportedView";

interface ConciergeResponseProps {
  response: ConciergeResponsePayload | (Record<string, unknown> & { response_type?: string });
}

function responseTypeOf(response: ConciergeResponseProps["response"]): string {
  const snake = "response_type" in response ? response.response_type : undefined;
  const camel = "responseType" in response ? response.responseType : undefined;
  return typeof snake === "string" ? snake : typeof camel === "string" ? camel : "unsupported";
}

export function ConciergeResponse({ response }: ConciergeResponseProps) {
  const responseType = responseTypeOf(response);

  if (responseType === "place_recommendations") {
    return <PlaceRecommendationsView response={response as ConciergeResponsePayload & { responseType: "place_recommendations" }} />;
  }

  if (responseType === "trip_advice") {
    return <TripAdviceView response={response as ConciergeResponsePayload & { responseType: "trip_advice" }} />;
  }

  const unsupportedResponse: UnsupportedResponse = {
    responseType: "unsupported",
    code: "unsupported_response_type",
    message: `Response type '${responseType}' is not supported yet.`,
  };
  return <UnsupportedView response={unsupportedResponse} />;
}
