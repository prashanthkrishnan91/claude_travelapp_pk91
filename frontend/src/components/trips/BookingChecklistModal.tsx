"use client";

import { useEffect, useState } from "react";
import {
  X,
  ExternalLink,
  CheckSquare,
  Square,
  Loader2,
  Plane,
  Hotel,
  MapPin,
  Gift,
  ShieldCheck,
  Tag,
} from "lucide-react";
import type { BookingOption, ItineraryItem, ItemType } from "@/types";
import { fetchBookingLinks } from "@/lib/api";

// ─── Provider display config ──────────────────────────────────────────────────

const PROVIDER_LABELS: Record<string, string> = {
  booking_com:    "Booking.com",
  expedia:        "Expedia",
  hotels_com:     "Hotels.com",
  google_flights: "Google Flights",
  kayak:          "Kayak",
  airline_direct: "Book Direct",
  chase_portal:   "Chase Portal",
  amex_travel:    "Amex Travel",
  capital_one:    "Capital One Travel",
  viator:         "Viator",
  getyourguide:   "GetYourGuide",
  klook:          "Klook",
};

const PORTAL_PROVIDERS = new Set(["chase_portal", "amex_travel", "capital_one"]);

function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Type icon ────────────────────────────────────────────────────────────────

const TYPE_ICONS: Record<ItemType, React.ReactNode> = {
  flight:   <Plane   className="w-4 h-4" />,
  hotel:    <Hotel   className="w-4 h-4" />,
  activity: <MapPin  className="w-4 h-4" />,
  meal:     <MapPin  className="w-4 h-4" />,
  transit:  <Plane   className="w-4 h-4" />,
  note:     <MapPin  className="w-4 h-4" />,
};

// ─── Checklist config ─────────────────────────────────────────────────────────

const CHECKLIST = [
  {
    id: "transfer_bonus",
    icon: <Gift className="w-4 h-4 text-violet-500" />,
    label: "Check for active transfer bonuses",
    hint: "Some card issuers run limited-time transfer bonuses (up to 30% more points). Verify before transferring.",
  },
  {
    id: "cancellation",
    icon: <ShieldCheck className="w-4 h-4 text-sky-500" />,
    label: "Review cancellation policy",
    hint: "Confirm free cancellation window and any penalty fees before completing the booking.",
  },
  {
    id: "portal_pricing",
    icon: <Tag className="w-4 h-4 text-emerald-500" />,
    label: "Compare portal vs. cash pricing",
    hint: "Points portal rates sometimes differ from direct-book prices. Run the numbers before committing.",
  },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface BookingChecklistModalProps {
  item: ItineraryItem;
  onClose: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function BookingChecklistModal({ item, onClose }: BookingChecklistModalProps) {
  const [checked, setChecked]       = useState<Set<string>>(new Set());
  const [options, setOptions]       = useState<BookingOption[]>([]);
  const [loading, setLoading]       = useState(false);

  const allChecked = checked.size === CHECKLIST.length;

  // Populate booking options — prefer stored, fall back to API fetch
  useEffect(() => {
    const stored = item.details?.bookingOptions ?? [];
    if (stored.length > 0) {
      setOptions(stored);
    } else {
      setLoading(true);
      fetchBookingLinks(item.id)
        .then(setOptions)
        .finally(() => setLoading(false));
    }
  }, [item]);

  const toggle = (id: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });

  // Split into direct and portal options
  const directOptions = options.filter((o) => !PORTAL_PROVIDERS.has(o.provider));
  const portalOptions = options.filter((o) => PORTAL_PROVIDERS.has(o.provider));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start gap-3 px-5 pt-5 pb-4 border-b border-slate-100">
          <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
            {TYPE_ICONS[item.itemType]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">Book</p>
            <h2 className="text-base font-semibold text-slate-800 leading-tight truncate">{item.title}</h2>
            {item.location && (
              <p className="text-xs text-slate-400 mt-0.5">{item.location}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 w-7 h-7 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors"
            aria-label="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="px-5 py-4 flex flex-col gap-5 max-h-[70vh] overflow-y-auto">
          {/* Checklist */}
          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2.5">
              Before you book
            </h3>
            <ul className="flex flex-col gap-2">
              {CHECKLIST.map((item) => {
                const isChecked = checked.has(item.id);
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => toggle(item.id)}
                      className="w-full flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50 transition-colors text-left"
                    >
                      <span className="flex-shrink-0 mt-0.5">
                        {isChecked ? (
                          <CheckSquare className="w-4 h-4 text-sky-600" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-300" />
                        )}
                      </span>
                      <span className="flex-shrink-0 mt-0.5">{item.icon}</span>
                      <span className="flex-1 min-w-0">
                        <span className={`block text-sm font-medium ${isChecked ? "text-slate-400 line-through" : "text-slate-700"}`}>
                          {item.label}
                        </span>
                        <span className="block text-xs text-slate-400 mt-0.5 leading-snug">{item.hint}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Booking options */}
          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2.5">
              Booking options
            </h3>

            {loading ? (
              <div className="flex items-center justify-center py-6 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                <span className="text-sm">Loading options…</span>
              </div>
            ) : options.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">No booking options available.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {directOptions.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <p className="text-xs text-slate-400 font-medium">Direct booking</p>
                    <div className="flex flex-wrap gap-2">
                      {directOptions.map((opt) => (
                        <a
                          key={opt.provider}
                          href={opt.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            allChecked
                              ? "bg-sky-600 hover:bg-sky-700 text-white"
                              : "bg-slate-100 hover:bg-slate-200 text-slate-600"
                          }`}
                        >
                          {providerLabel(opt.provider)}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {portalOptions.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <p className="text-xs text-slate-400 font-medium">Points portals</p>
                    <div className="flex flex-wrap gap-2">
                      {portalOptions.map((opt) => (
                        <a
                          key={opt.provider}
                          href={opt.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            allChecked
                              ? "bg-violet-600 hover:bg-violet-700 text-white"
                              : "bg-slate-100 hover:bg-slate-200 text-slate-600"
                          }`}
                        >
                          {providerLabel(opt.provider)}
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {!allChecked && (
                  <p className="text-xs text-slate-400 text-center mt-1">
                    Complete the checklist above to highlight booking links.
                  </p>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
