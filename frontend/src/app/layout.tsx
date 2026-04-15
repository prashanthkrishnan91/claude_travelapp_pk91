import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNav } from "@/components/layout/MobileNav";

export const metadata: Metadata = {
  title: {
    default: "Travel Concierge",
    template: "%s | Travel Concierge",
  },
  description:
    "Plan trips with dual cash + points pricing powered by AI — your personal travel concierge.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">
        {/* Mobile navigation (top bar + slide-out drawer) */}
        <MobileNav />

        <div className="flex h-full min-h-screen">
          {/* Desktop sidebar */}
          <Sidebar />

          {/* Main content area */}
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
