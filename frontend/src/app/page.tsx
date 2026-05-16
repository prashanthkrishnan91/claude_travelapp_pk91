import type { Metadata } from "next";
import { DashboardClient } from "@/components/dashboard/DashboardClient";

export const metadata: Metadata = { title: "Home" };

export default function DashboardPage() {
  return <DashboardClient />;
}
