import type { Metadata } from "next";
import { Fraunces } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

const fraunces = Fraunces({
  subsets: ["latin"],
  axes: ["opsz"],
  variable: "--font-fraunces",
  display: "swap",
  style: ["normal", "italic"],
});

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
    <html lang="en" className={`h-full ${fraunces.variable}`}>
      <body className="h-full">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
