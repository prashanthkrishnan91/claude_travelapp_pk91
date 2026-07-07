"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { AtelierBackdrop } from "@/components/atmosphere/AtelierBackdrop";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    const { error: authError } = await supabase.auth.signUp({
      email,
      password,
    });

    setLoading(false);

    if (authError) {
      setError(authError.message);
    } else {
      // Supabase may require email confirmation; redirect to login
      router.push("/auth/login?signup=success");
    }
  }

  return (
    <div className="atelier-backdrop-host relative min-h-screen flex items-center justify-center px-4 overflow-hidden">
      {/* Atmospheric Background System v1 — shares the cinematic auth-hero
          backdrop with the login screen (registry-driven). */}
      <AtelierBackdrop role="auth-hero" priority />

      <div className="relative z-10 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-2 text-center" style={{ textShadow: "0 2px 12px rgba(0,0,0,0.4)" }}>
          Travel Concierge
        </h1>
        <p className="text-sm text-white/75 text-center mb-8">
          Create your account
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
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input placeholder:text-cream-500 [&:-webkit-autofill]:!text-cream-100 [&:-webkit-autofill]:[-webkit-text-fill-color:#f2ede4] [&:-webkit-autofill]:shadow-[inset_0_0_0_1000px_rgba(22,22,42,0.92)]"
            />
          </div>

          <div>
            <label className="label">
              Confirm password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input placeholder:text-cream-500 [&:-webkit-autofill]:!text-cream-100 [&:-webkit-autofill]:[-webkit-text-fill-color:#f2ede4] [&:-webkit-autofill]:shadow-[inset_0_0_0_1000px_rgba(22,22,42,0.92)]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full justify-center py-2.5 disabled:opacity-50"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>

          <p className="text-center text-sm text-cream-300">
            Already have an account?{" "}
            <Link
              href="/auth/login"
              className="text-brand-400 hover:underline font-medium"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
