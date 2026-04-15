import type { Metadata } from "next";
import { Settings } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="Settings"
        description="Manage your account preferences."
      />
      <div className="card p-8 text-center text-slate-400">
        <Settings className="w-8 h-8 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Settings coming soon.</p>
      </div>
    </>
  );
}
