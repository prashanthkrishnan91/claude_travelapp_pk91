"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { supabase } from "@/lib/supabase";
import gsap from "gsap";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthPage = pathname.startsWith("/auth");
  const [checking, setChecking] = useState(!isAuthPage);

  useEffect(() => {
    if (isAuthPage) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/auth/login");
      } else {
        setChecking(false);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session && !pathname.startsWith("/auth")) {
          router.push("/auth/login");
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [isAuthPage, pathname, router]);

  // GSAP card entrance on route change
  useEffect(() => {
    const timeout = setTimeout(() => {
      const cards = document.querySelectorAll(".card");
      if (cards.length) {
        gsap.from(cards, {
          y: 18,
          opacity: 0,
          duration: 0.42,
          stagger: 0.055,
          ease: "power2.out",
          clearProps: "all",
        });
      }
    }, 60);
    return () => clearTimeout(timeout);
  }, [pathname]);

  // Auth pages: render without sidebar
  if (isAuthPage) {
    return <>{children}</>;
  }

  // Protected pages: show loading until session confirmed
  if (checking) {
    return (
      <div className="flex h-full min-h-screen items-center justify-center">
        <p className="text-gray-500 text-sm">Loading…</p>
      </div>
    );
  }

  return (
    <>
      {/* Layer 2: ambient glow blobs */}
      <div
        className="fixed inset-0 overflow-hidden pointer-events-none"
        style={{ zIndex: -10 }}
        aria-hidden="true"
      >
        <div
          className="absolute rounded-full"
          style={{
            top: "-20%",
            left: "-10%",
            width: "60vw",
            height: "60vw",
            background: "radial-gradient(circle, rgba(186,230,253,0.55) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            bottom: "-15%",
            right: "-10%",
            width: "55vw",
            height: "55vw",
            background: "radial-gradient(circle, rgba(196,181,253,0.40) 0%, transparent 70%)",
            filter: "blur(70px)",
          }}
        />
        <div
          className="absolute rounded-full"
          style={{
            top: "35%",
            left: "25%",
            width: "40vw",
            height: "40vw",
            background: "radial-gradient(circle, rgba(254,243,199,0.45) 0%, transparent 70%)",
            filter: "blur(55px)",
          }}
        />
      </div>
      <MobileNav />
      <div className="flex h-full min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-24 lg:pb-8">
            {children}
          </div>
        </main>
      </div>
    </>
  );
}
