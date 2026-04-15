import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripBuilderForm } from "@/components/trips/TripBuilderForm";

export const metadata: Metadata = { title: "New Trip" };

export default function NewTripPage() {
  return (
    <>
      <PageHeader
        title="Plan a New Trip"
        description="Fill in the details and let the AI concierge build your perfect itinerary."
      />
      <TripBuilderForm />
    </>
  );
}
