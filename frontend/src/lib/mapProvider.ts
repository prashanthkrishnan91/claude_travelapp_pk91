// Map System v1 — shared frontend map tile provider config.
//
// Single source of truth for which basemap tile provider every map surface
// renders (Journey Desk Trip Lens + Explore/Build discovery map). Provider
// policy/governance lives in the backend central registry
// (`backend/app/services/provider_registry.py` → `maptiler_maps`, role MAP_TILE).
// This is the browser-side resolver of that policy.
//
// VISUAL tile provider ONLY. Never a place provider, geocoder, search provider,
// or card authority. The key is a public browser key — no server secret here.
// MapTiler is the preferred personal/non-commercial provider; OpenStreetMap
// public tiles remain the honest fallback when no key is configured.

export type MapProviderId = "maptiler" | "osm";

export interface MapProviderConfig {
  /** Stable provider id (mirrors the backend registry intent). */
  id: MapProviderId;
  /** Leaflet tile-layer URL template. */
  tileUrl: string;
  /** Attribution string — always rendered, never hidden. */
  attribution: string;
  /** True only when the preferred provider (MapTiler) is actually configured. */
  configured: boolean;
  /** Visual style name for the shared atlas look. */
  styleName: string;
  /** Max tile zoom. */
  maxZoom: number;
}

const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

function maptilerKey(): string | undefined {
  // NEXT_PUBLIC_* is inlined at build time and safe to read in client code.
  const key = process.env.NEXT_PUBLIC_MAPTILER_KEY;
  return typeof key === "string" && key.trim() ? key.trim() : undefined;
}

function preferredProviderId(): MapProviderId {
  const explicit = (process.env.NEXT_PUBLIC_MAP_PROVIDER ?? "").trim().toLowerCase();
  if (explicit === "maptiler") return "maptiler";
  if (explicit === "osm") return "osm";
  // No explicit choice: prefer MapTiler when a public key exists, else OSM.
  return maptilerKey() ? "maptiler" : "osm";
}

/**
 * Resolve the shared map tile provider for every map surface. MapTiler is used
 * only when it is the preferred provider AND a public key is present; otherwise
 * the OpenStreetMap public tiles are the fallback (never broken/blank tiles).
 */
export function getMapProvider(): MapProviderConfig {
  const key = maptilerKey();

  if (preferredProviderId() === "maptiler" && key) {
    return {
      id: "maptiler",
      // MapTiler "landscape" raster style — warm muted atlas tones that match
      // the paper world. Public browser key only.
      tileUrl: `https://api.maptiler.com/maps/landscape/{z}/{x}/{y}.png?key=${key}`,
      attribution:
        '© <a href="https://www.maptiler.com/copyright/">MapTiler</a> ' +
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      configured: true,
      styleName: "atlas-landscape",
      maxZoom: 19,
    };
  }

  return {
    id: "osm",
    tileUrl: OSM_TILE_URL,
    attribution: OSM_ATTRIBUTION,
    configured: false,
    styleName: "atlas-osm-fallback",
    maxZoom: 19,
  };
}

/** True when MapTiler is configured (preferred + public key present). */
export function isMapProviderConfigured(): boolean {
  return getMapProvider().id === "maptiler";
}
