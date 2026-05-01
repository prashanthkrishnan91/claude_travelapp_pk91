"use client";

import { useEffect, useState } from "react";
import { CreditCard, PlusCircle, X, Pencil } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchCards, createCard, updateCard } from "@/lib/api";
import type { TravelCard } from "@/types";

const ISSUERS = [
  "American Express",
  "Chase",
  "Citi",
  "Capital One",
  "Bank of America",
  "Wells Fargo",
  "Discover",
  "Barclays",
  "US Bank",
  "Other",
];

function AddCardModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (card: TravelCard) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    cardKey: "",
    displayName: "",
    issuer: ISSUERS[0],
    pointsBalance: "",
    pointValueCpp: "",
    isPrimary: false,
  });

  function patch(update: Partial<typeof form>) {
    setForm((prev) => ({ ...prev, ...update }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.cardKey.trim() || !form.displayName.trim()) {
      setError("Card key and display name are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const card = await createCard({
        cardKey: form.cardKey.trim(),
        displayName: form.displayName.trim(),
        issuer: form.issuer,
        pointsBalance: form.pointsBalance ? Number(form.pointsBalance) : 0,
        pointValueCpp: form.pointValueCpp ? Number(form.pointValueCpp) : undefined,
        isPrimary: form.isPrimary,
      });
      onSaved(card);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save card.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="card rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-cream-100">Add Travel Card</h2>
          <button onClick={onClose} className="btn-ghost p-2" aria-label="Close add card modal">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="card-name">Card name</label>
            <input
              id="card-name"
              className="input"
              placeholder="e.g. Chase Sapphire Reserve"
              value={form.displayName}
              onChange={(e) => patch({ displayName: e.target.value, cardKey: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="card-key">Card key</label>
            <input
              id="card-key"
              className="input"
              placeholder="e.g. chase_sapphire_reserve"
              value={form.cardKey}
              onChange={(e) => patch({ cardKey: e.target.value })}
              required
            />
            <p className="mt-1 text-xs text-cream-400">Unique identifier, lowercase with underscores.</p>
          </div>

          <div>
            <label className="label" htmlFor="card-issuer">Issuer</label>
            <select
              id="card-issuer"
              className="select"
              value={form.issuer}
              onChange={(e) => patch({ issuer: e.target.value })}
            >
              {ISSUERS.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="card-points">Points balance</label>
              <input
                id="card-points"
                type="number"
                min="0"
                className="input"
                placeholder="0"
                value={form.pointsBalance}
                onChange={(e) => patch({ pointsBalance: e.target.value })}
              />
            </div>
            <div>
              <label className="label" htmlFor="card-cpp">Value (cpp)</label>
              <input
                id="card-cpp"
                type="number"
                min="0"
                step="0.01"
                className="input"
                placeholder="e.g. 1.5"
                value={form.pointValueCpp}
                onChange={(e) => patch({ pointValueCpp: e.target.value })}
              />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.isPrimary}
              onChange={(e) => patch({ isPrimary: e.target.checked })}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-cream-200">Set as primary card</span>
          </label>

          {error && (
            <div className="rounded-xl bg-rose-500/12 border border-rose-500/35 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Add Card"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditCardModal({
  card,
  onClose,
  onSaved,
}: {
  card: TravelCard;
  onClose: () => void;
  onSaved: (card: TravelCard) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    displayName: card.displayName,
    issuer: card.issuer,
    pointsBalance: String(card.pointsBalance ?? 0),
    pointValueCpp: card.pointValueCpp != null ? String(card.pointValueCpp) : "",
    isPrimary: card.isPrimary,
  });

  function patch(update: Partial<typeof form>) {
    setForm((prev) => ({ ...prev, ...update }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.displayName.trim()) {
      setError("Card name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateCard(card.id, {
        displayName: form.displayName.trim(),
        issuer: form.issuer,
        pointsBalance: form.pointsBalance ? Number(form.pointsBalance) : 0,
        pointValueCpp: form.pointValueCpp ? Number(form.pointValueCpp) : undefined,
        isPrimary: form.isPrimary,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update card.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="card rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-cream-100">Edit Card</h2>
          <button onClick={onClose} className="btn-ghost p-2" aria-label="Close edit card modal">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="edit-card-name">Card name</label>
            <input
              id="edit-card-name"
              className="input"
              value={form.displayName}
              onChange={(e) => patch({ displayName: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="edit-card-issuer">Issuer</label>
            <select
              id="edit-card-issuer"
              className="select"
              value={form.issuer}
              onChange={(e) => patch({ issuer: e.target.value })}
            >
              {ISSUERS.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="edit-card-points">Points balance</label>
              <input
                id="edit-card-points"
                type="number"
                min="0"
                className="input"
                placeholder="0"
                value={form.pointsBalance}
                onChange={(e) => patch({ pointsBalance: e.target.value })}
              />
            </div>
            <div>
              <label className="label" htmlFor="edit-card-cpp">Value (cpp)</label>
              <input
                id="edit-card-cpp"
                type="number"
                min="0"
                step="0.01"
                className="input"
                placeholder="e.g. 1.5"
                value={form.pointValueCpp}
                onChange={(e) => patch({ pointValueCpp: e.target.value })}
              />
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.isPrimary}
              onChange={(e) => patch({ isPrimary: e.target.checked })}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-cream-200">Set as primary card</span>
          </label>

          {error && (
            <div className="rounded-xl bg-rose-500/12 border border-rose-500/35 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CardsPage() {
  const [cards, setCards] = useState<TravelCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCard, setEditingCard] = useState<TravelCard | null>(null);

  useEffect(() => {
    fetchCards()
      .then(setCards)
      .catch(() => console.error("Failed to load cards"))
      .finally(() => setLoading(false));
  }, []);

  function handleSaved(card: TravelCard) {
    setCards((prev) => [...prev, card]);
    setShowModal(false);
  }

  function handleUpdated(updated: TravelCard) {
    setCards((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    setEditingCard(null);
  }

  return (
    <>
      <PageHeader
        title="Travel Cards"
        description="Manage your credit cards and track points balances."
        action={
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle className="w-4 h-4" />
            Add Card
          </button>
        }
      />

      {showModal && (
        <AddCardModal onClose={() => setShowModal(false)} onSaved={handleSaved} />
      )}

      {editingCard && (
        <EditCardModal
          card={editingCard}
          onClose={() => setEditingCard(null)}
          onSaved={handleUpdated}
        />
      )}

      {loading ? (
        <div className="card p-8 text-center text-sm text-slate-400">Loading cards…</div>
      ) : cards.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={<CreditCard className="w-6 h-6" />}
            title="No cards added yet"
            description="Add your travel credit cards to track points and get personalized redemption recommendations."
            action={
              <button className="btn-primary" onClick={() => setShowModal(true)}>
                <PlusCircle className="w-4 h-4" />
                Add Card
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cards.map((card) => (
            <div key={card.id} className="card p-5 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-cream-100">{card.displayName}</p>
                  <p className="text-xs text-cream-300 mt-0.5">{card.issuer}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {card.isPrimary && (
                    <span className="badge badge-value text-[10px] px-1.5 py-0.5">Primary</span>
                  )}
                  <button
                    onClick={() => setEditingCard(card)}
                    className="btn-ghost p-1.5 rounded-lg"
                    aria-label={`Edit ${card.displayName}`}
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex gap-4 text-xs text-cream-300">
                <span>
                  <span className="font-semibold text-cream-100">
                    {(card.pointsBalance ?? 0).toLocaleString()}
                  </span>{" "}
                  pts
                </span>
                {card.pointValueCpp && (
                  <span>
                    <span className="font-semibold text-cream-100">
                      {Number(card.pointValueCpp).toFixed(2)}¢
                    </span>{" "}
                    / pt
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
