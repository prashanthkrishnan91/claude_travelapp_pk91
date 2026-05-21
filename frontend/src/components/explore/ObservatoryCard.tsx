/**
 * Observatory editorial plate — the honest typeset fallback header for
 * Explore place cards. Production result types carry NO photo/image field,
 * so this is a token-built editorial gradient (never a stock or real photo).
 * Purely presentational; decorative (aria-hidden) — the serial and category
 * it shows are repeated as real text in the card body.
 */

const PLATE_VARIANTS = ["", "obs-card-plate--b", "obs-card-plate--c", "obs-card-plate--d"];

export function ObservatoryPlate({
  index,
  category,
}: {
  index: number;
  category?: string;
}) {
  const variant = PLATE_VARIANTS[index % PLATE_VARIANTS.length];
  const serial = `No. ${String(index + 1).padStart(2, "0")}`;
  return (
    <div className={`obs-card-plate ${variant}`.trim()} aria-hidden="true">
      <span className="obs-card-serial">{serial}</span>
      {category ? <span className="obs-card-plate-cat">{category}</span> : null}
    </div>
  );
}
