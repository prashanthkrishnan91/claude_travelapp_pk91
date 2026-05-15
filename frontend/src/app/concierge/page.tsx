import type { Metadata } from "next";
import { ConciergePage } from "@/components/concierge/ConciergePage";

export const metadata: Metadata = { title: "AI Concierge" };

export default function ConciergeRoute() {
  return <ConciergePage />;
}
