"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { AtelierBackdrop } from "@/components/atmosphere/AtelierBackdrop";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (authError) {
      setError(authError.message);
    } else {
      router.push("/");
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 overflow-hidden">
      {/* Atmospheric Background System v1 — cinematic auth-hero backdrop.
          Registry-driven (lib/atmosphere/backgrounds.ts); placeholder gradient
          until a curated /atmosphere/auth-hero.jpg is supplied. */}
      <AtelierBackdrop role="auth-hero" priority />

      <div className="relative z-10 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-2 text-center" style={{ textShadow: "0 2px 12px rgba(0,0,0,0.4)" }}>
          Travel Concierge
        </h1>
        <p className="text-sm text-white/75 text-center mb-8">
          Sign in to your account
        </p>

        <form
          onSubmit={handleSubmit}
          className="card rounded-2xl p-8 space-y-5"
        >
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}

          <div>
            <label className="label">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input placeholder:text-cream-500 [&:-webkit-autofill]:!text-cream-100 [&:-webkit-autofill]:[-webkit-text-fill-color:#f2ede4] [&:-webkit-autofill]:shadow-[inset_0_0_0_1000px_rgba(22,22,42,0.92)]"
            />
          </div>

          <div>
            <label className="label">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input placeholder:text-cream-500 [&:-webkit-autofill]:!text-cream-100 [&:-webkit-autofill]:[-webkit-text-fill-color:#f2ede4] [&:-webkit-autofill]:shadow-[inset_0_0_0_1000px_rgba(22,22,42,0.92)]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full justify-center py-2.5 disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>

          <p className="text-center text-sm text-cream-300">
            No account?{" "}
            <Link
              href="/auth/signup"
              className="text-brand-400 hover:underline font-medium"
            >
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );

}
