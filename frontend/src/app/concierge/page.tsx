import type { Metadata } from "next";
import { Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = { title: "AI Concierge" };

export default function ConciergePage() {
  return (
    <>
      <PageHeader
        title="AI Concierge"
        description="Get personalized travel recommendations powered by Claude."
      />
      <div className="card p-8 text-center text-slate-400">
        <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-40" />
        <p className="text-sm">AI Concierge coming soon.</p>
      </div>
    </>
  );
}
