"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-rose-50 text-rose-500 mb-4">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h2 className="text-lg font-semibold text-slate-900 mb-1">Something went wrong</h2>
      <p className="text-sm text-slate-500 max-w-sm mb-6">
        {error.message || "An unexpected error occurred. Please try again."}
      </p>
      <button onClick={reset} className="btn-primary">
        <RefreshCw className="w-4 h-4" />
        Try again
      </button>
    </div>
  );
}
