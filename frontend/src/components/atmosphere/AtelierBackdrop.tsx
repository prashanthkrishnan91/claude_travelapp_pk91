import Image from "next/image";
import {
  getBackdrop,
  type BackdropRole,
} from "@/lib/atmosphere/backgrounds";

/**
 * AtelierBackdrop — the single shared component that paints an atmospheric
 * background for a surface. Driven entirely by the central registry in
 * lib/atmosphere/backgrounds.ts (role in → consistent treatment out).
 *
 * Layer order (all fixed / absolute, aria-hidden, pointer-events:none):
 *   1. color bed      — gradient placeholder (always present, sets the mood
 *                        and prevents any flash / layout shift before an image
 *                        decodes).
 *   2. photo layer    — optimized next/image (fill) ONLY when the registry has
 *                        a local image path. Soft-blurred per role for
 *                        atmosphere, never crisp detail behind dense UI.
 *   3. scrim          — cream-or-dark gradient that guarantees text/card
 *                        contrast on top.
 *   4. grain          — optional faint film grain (CSS data-URI, no asset).
 *
 * No layout shift: the component renders into a fixed/absolute full-bleed box,
 * so it never participates in document flow. Default is `fixed` (viewport
 * backdrop for whole surfaces); pass `mode="absolute"` to scope it inside a
 * positioned container (e.g. the Brief card).
 */
export function AtelierBackdrop({
  role,
  mode = "fixed",
  className = "",
  priority = false,
}: {
  role: BackdropRole;
  mode?: "fixed" | "absolute";
  className?: string;
  priority?: boolean;
}) {
  const asset = getBackdrop(role);

  return (
    <div
      className={`atelier-backdrop atelier-backdrop--${mode} atelier-backdrop--${role} ${className}`}
      data-testid="atelier-backdrop"
      data-backdrop-role={role}
      data-backdrop-image={asset.image ? "photo" : "placeholder"}
      aria-hidden="true"
    >
      {/* 1 — color bed (always present) */}
      <div
        className="atelier-backdrop__bed"
        style={{ backgroundImage: asset.placeholder }}
      />

      {/* 2 — optimized photo, only when a local curated asset is supplied */}
      {asset.image && (
        <div
          className="atelier-backdrop__photo"
          style={{ filter: asset.blurPx ? `blur(${asset.blurPx}px)` : undefined }}
        >
          <Image
            src={asset.image}
            alt=""
            fill
            priority={priority}
            sizes="100vw"
            style={{ objectFit: "cover", objectPosition: asset.focalPoint }}
          />
        </div>
      )}

      {/* 3 — contrast scrim */}
      <div
        className="atelier-backdrop__scrim"
        style={{ backgroundImage: asset.scrim }}
      />

      {/* 4 — optional film grain */}
      {asset.grain && <div className="atelier-backdrop__grain" />}
    </div>
  );
}
