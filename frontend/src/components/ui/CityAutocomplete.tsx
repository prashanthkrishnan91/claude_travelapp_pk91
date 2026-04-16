"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2, MapPin, X } from "lucide-react";
import { resolveAirports } from "@/lib/api";
import type { AirportMatch } from "@/lib/api";

export interface AirportSelection {
  city: string;
  country: string;
  airports: string[];
}

interface CityAutocompleteProps {
  placeholder?: string;
  value: AirportSelection | null;
  onChange: (selection: AirportSelection | null) => void;
  className?: string;
  inputClassName?: string;
}

export function formatAirportSelection(sel: AirportSelection): string {
  return `${sel.city}, ${sel.country} (${sel.airports.join(", ")})`;
}

export function CityAutocomplete({
  placeholder = "City or airport…",
  value,
  onChange,
  className = "",
  inputClassName = "",
}: CityAutocompleteProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<AirportMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 2) {
      setSuggestions([]);
      setOpen(false);
      setShowManual(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const result = await resolveAirports(query);
        setSuggestions(result.matches);
        setOpen(result.matches.length > 0);
        setShowManual(result.matches.length === 0);
      } catch {
        setSuggestions([]);
        setShowManual(true);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(match: AirportMatch) {
    onChange({ city: match.city, country: match.country, airports: match.airports });
    setQuery("");
    setOpen(false);
    setShowManual(false);
    setSuggestions([]);
  }

  function handleClear() {
    onChange(null);
    setQuery("");
    setSuggestions([]);
    setOpen(false);
    setShowManual(false);
    setManualCode("");
  }

  function handleManualSubmit() {
    const code = manualCode.trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(code)) {
      onChange({ city: code, country: "", airports: [code] });
      setManualCode("");
      setShowManual(false);
      setQuery("");
    }
  }

  if (value) {
    return (
      <div className={`flex items-center gap-2 input ${className}`}>
        <MapPin className="w-3.5 h-3.5 text-sky-500 flex-shrink-0" />
        <span className="flex-1 text-sm truncate">{formatAirportSelection(value)}</span>
        <button
          type="button"
          onClick={handleClear}
          className="text-slate-400 hover:text-slate-600 flex-shrink-0"
          aria-label="Clear selection"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          type="text"
          placeholder={loading ? "Finding airports…" : placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowManual(false);
          }}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          className={`input w-full ${inputClassName}`}
          autoComplete="off"
        />
        {loading && (
          <Loader2 className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 animate-spin pointer-events-none" />
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {suggestions.map((s) => (
            <li key={`${s.city}-${s.country}`}>
              <button
                type="button"
                className="w-full text-left px-3 py-2.5 hover:bg-slate-50 flex items-start gap-2.5 border-b border-slate-100 last:border-0"
                onClick={() => handleSelect(s)}
              >
                <MapPin className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <span className="text-sm font-medium text-slate-800">{s.city}</span>
                  <span className="text-sm text-slate-500">, {s.country}</span>
                  <span className="ml-2 text-xs text-sky-600 font-mono">{s.airports.join(", ")}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {showManual && !loading && query.length >= 2 && (
        <div className="mt-1.5 p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800">
          <p className="mb-1.5 font-medium">No cities found — enter IATA code directly:</p>
          <div className="flex gap-1.5 items-center">
            <input
              type="text"
              placeholder="e.g. JFK"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value.toUpperCase().slice(0, 3))}
              onKeyDown={(e) => e.key === "Enter" && handleManualSubmit()}
              maxLength={3}
              className="input py-1 text-xs w-20 uppercase"
            />
            <button
              type="button"
              onClick={handleManualSubmit}
              disabled={!/^[A-Z]{3}$/.test(manualCode)}
              className="btn-primary py-1 px-2 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Use code
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
