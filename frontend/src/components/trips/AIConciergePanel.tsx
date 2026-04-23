"use client";

import { useState, useRef, useEffect } from "react";
import { X, Send, Sparkles, Plus, Loader2, UtensilsCrossed, MapPin } from "lucide-react";
import { callConcierge, addConciergeItemToTrip } from "@/lib/api";
import type { ConciergeSuggestion } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
  suggestions?: ConciergeSuggestion[];
}

interface Props {
  tripId: string;
  destination: string;
  isOpen: boolean;
  onClose: () => void;
  onItemAdded?: () => void;
}

export function AIConciergePanel({ tripId, destination, isOpen, onClose, onItemAdded }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: `Hi! I'm your AI Concierge for ${destination || "your trip"}. Ask me anything — local tips, what to do, where to eat, hidden gems…`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [addingItems, setAddingItems] = useState<Set<string>>(new Set());
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const QUICK_ACTIONS = [
    { label: "Plan my day", query: "Plan my day in " + (destination || "this destination") },
    { label: "Best restaurants", query: "What are the best restaurants in " + (destination || "this area") + "?" },
    { label: "Romantic ideas", query: "Give me romantic ideas and experiences in " + (destination || "this destination") },
    { label: "Hidden gems", query: "What are the hidden gems and off-the-beaten-path spots in " + (destination || "this destination") + "?" },
  ];

  async function sendQuery(query: string) {
    if (!query || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    setLoading(true);
    try {
      const result = await callConcierge(tripId, query);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: result.response, suggestions: result.suggestions },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    await sendQuery(input.trim());
  }

  async function handleAddToTrip(suggestion: ConciergeSuggestion) {
    if (addingItems.has(suggestion.name) || addedItems.has(suggestion.name)) return;
    setAddingItems((prev) => new Set(prev).add(suggestion.name));
    try {
      await addConciergeItemToTrip(tripId, suggestion);
      setAddedItems((prev) => new Set(prev).add(suggestion.name));
      onItemAdded?.();
    } catch {
      // silently fail — user can retry
    } finally {
      setAddingItems((prev) => {
        const next = new Set(prev);
        next.delete(suggestion.name);
        return next;
      });
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={(e) => e.target === e.currentTarget && onClose()}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="relative flex flex-col w-full max-w-md h-full bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-violet-600 to-sky-500">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-white" />
            <span className="text-sm font-semibold text-white">AI Concierge</span>
            {destination && (
              <span className="text-xs text-white/70">· {destination}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-white/20 text-white/80 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-sky-500 text-white rounded-br-sm"
                      : "bg-slate-100 text-slate-800 rounded-bl-sm"
                  }`}
                >
                  {msg.text}
                </div>
              </div>

              {/* Suggestion cards */}
              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.suggestions.map((s, si) => {
                    const added = addedItems.has(s.name);
                    const adding = addingItems.has(s.name);
                    return (
                      <div
                        key={si}
                        className="border border-slate-200 rounded-xl p-3 bg-white shadow-sm"
                      >
                        <div className="flex items-start gap-2">
                          <div className="mt-0.5 flex-shrink-0">
                            {s.type === "restaurant" ? (
                              <UtensilsCrossed className="w-4 h-4 text-amber-500" />
                            ) : (
                              <MapPin className="w-4 h-4 text-violet-500" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-800 truncate">{s.name}</p>
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{s.reason}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleAddToTrip(s)}
                          disabled={adding || added}
                          className={`mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                            added
                              ? "bg-emerald-50 text-emerald-600 cursor-default"
                              : "bg-sky-50 text-sky-600 hover:bg-sky-100 active:scale-95"
                          }`}
                        >
                          {adding ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : added ? (
                            "✓ Added to Trip"
                          ) : (
                            <>
                              <Plus className="w-3 h-3" />
                              Add to Trip
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}

          {/* Quick action buttons — shown only before conversation starts */}
          {messages.length === 1 && !loading && (
            <div className="flex flex-wrap gap-2 mt-1">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => sendQuery(action.query)}
                  className="px-3 py-1.5 rounded-full border border-violet-200 bg-violet-50 text-violet-700 text-xs font-medium hover:bg-violet-100 active:scale-95 transition"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-3 py-2 flex items-center gap-2">
                <Loader2 className="w-3 h-3 text-slate-400 animate-spin" />
                <span className="text-xs text-slate-500">Thinking…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-slate-100 bg-white">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="Ask about restaurants, activities, tips…"
              disabled={loading}
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-60"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="btn-primary px-3 py-2 disabled:opacity-50"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
