"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, Plus, Star, X, MapPin, Layers } from "lucide-react";
import type { Map as LeafletMap, Marker as LeafletMarker, Circle as LeafletCircle } from "leaflet";
import type { AttractionSearchResult, BestAreaRecommendation, RestaurantSearchResult } from "@/types";
import { getMapProvider } from "@/lib/mapProvider";

type PopupItem =
  | { type: "attraction"; item: AttractionSearchResult }
  | { type: "restaurant"; item: RestaurantSearchResult };

type MapMode = "pins" | "heatmap";

interface HeatLayer {
  addTo(map: LeafletMap): this;
  remove(): void;
}

interface TripMapViewProps {
  destination: string;
  attractions: AttractionSearchResult[];
  restaurants: RestaurantSearchResult[];
  activeMarkerId?: string | null;
  bestArea?: BestAreaRecommendation | null;
  onMarkerClick?: (id: string) => void;
  onAddAttraction?: (a: AttractionSearchResult) => void;
  onAddRestaurant?: (r: RestaurantSearchResult) => void;
}

async function geocodeCity(city: string): Promise<[number, number]> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(city)}&format=json&limit=1`,
      { headers: { "User-Agent": "TravelConciergeApp/1.0" } }
    );
    const data = await res.json();
    if (data?.[0]) return [parseFloat(data[0].lat), parseFloat(data[0].lon)];
  } catch { /* silently fall back */ }
  return [40.7128, -74.006];
}

function goldenSpread(index: number): [number, number] {
  const angle = (index * 137.508 * Math.PI) / 180;
  const radius = 0.006 * Math.sqrt(index + 1);
  return [Math.sin(angle) * radius, Math.cos(angle) * radius];
}

// Weight: 40% rating, 30% review volume (log-scaled), 30% AI score
function computeWeight(item: AttractionSearchResult | RestaurantSearchResult): number {
  const rating = item.rating ?? 3;
  const reviews = item.numReviews ?? 100;
  const aiScore = item.aiScore ?? 50;
  const ratingScore = rating / 5;
  const reviewScore = Math.min(1, Math.log(Math.max(1, reviews)) / Math.log(500_000));
  const aiNorm = aiScore / 100;
  return ratingScore * 0.4 + reviewScore * 0.3 + aiNorm * 0.3;
}

export function TripMapView({
  destination,
  attractions,
  restaurants,
  activeMarkerId,
  bestArea,
  onMarkerClick,
  onAddAttraction,
  onAddRestaurant,
}: TripMapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);
  const markersRef = useRef<Map<string, LeafletMarker>>(new Map());
  const heatLayerRef = useRef<HeatLayer | null>(null);
  const bestAreaCircleRef = useRef<LeafletCircle | null>(null);
  const mapModeRef = useRef<MapMode>("pins");

  const [center, setCenter] = useState<[number, number] | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [geocoding, setGeocoding] = useState(true);
  const [popup, setPopup] = useState<PopupItem | null>(null);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<MapMode>("pins");
  const [heatScriptLoaded, setHeatScriptLoaded] = useState(false);

  // Keep ref in sync for use inside async callbacks
  useEffect(() => { mapModeRef.current = mapMode; }, [mapMode]);

  // Inject Leaflet CSS once
  useEffect(() => {
    const CSS_ID = "leaflet-css";
    if (document.getElementById(CSS_ID)) return;
    const link = document.createElement("link");
    link.id = CSS_ID;
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);
  }, []);

  // Inject leaflet.heat plugin once; it will extend the global window.L
  useEffect(() => {
    const SCRIPT_ID = "leaflet-heat-js";
    if (document.getElementById(SCRIPT_ID)) {
      // Script already in DOM — check if it already patched window.L
      type WinWithL = Record<string, unknown> & { L?: { heatLayer?: unknown } };
      if ((window as unknown as WinWithL).L?.heatLayer) setHeatScriptLoaded(true);
      return;
    }
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = "https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js";
    script.onload = () => setHeatScriptLoaded(true);
    document.head.appendChild(script);
  }, []);

  // Geocode destination city
  useEffect(() => {
    setGeocoding(true);
    geocodeCity(destination).then((coords) => {
      setCenter(coords);
      setGeocoding(false);
    });
  }, [destination]);

  // Initialize Leaflet map once center is known
  useEffect(() => {
    if (!center || !mapContainerRef.current) return;
    let cancelled = false;
    const markers = markersRef.current;

    import("leaflet").then((mod) => {
      if (cancelled || !mapContainerRef.current || mapInstanceRef.current) return;
      const L = mod.default ?? mod;

      // Expose L globally so the leaflet.heat CDN script can extend it
      (window as unknown as Record<string, unknown>).L = L;

      const map = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
      }).setView(center, 13);

      const tiles = getMapProvider();
      L.tileLayer(tiles.tileUrl, {
        attribution: tiles.attribution,
        maxZoom: tiles.maxZoom,
      }).addTo(map);

      mapInstanceRef.current = map;
      if (!cancelled) setMapReady(true);
    });

    return () => {
      cancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      markers.clear();
      heatLayerRef.current = null;
      setMapReady(false);
    };
  // center changes only when destination changes — intentional single-init
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center]);

  // Toggle pins / heatmap visibility
  const applyMode = useCallback((mode: MapMode) => {
    const map = mapInstanceRef.current;
    if (!map) return;
    markersRef.current.forEach((marker) => {
      if (mode === "pins") marker.addTo(map);
      else marker.remove();
    });
    if (heatLayerRef.current) {
      if (mode === "heatmap") heatLayerRef.current.addTo(map);
      else heatLayerRef.current.remove();
    }
  }, []);

  // Build / rebuild markers and heatmap whenever map, data, or heat script readiness changes
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !center) return;
    let cancelled = false;

    import("leaflet").then((mod) => {
      if (cancelled || !mapInstanceRef.current) return;
      const L = mod.default ?? mod;
      const map = mapInstanceRef.current;

      markersRef.current.forEach((m) => m.remove());
      markersRef.current.clear();
      if (heatLayerRef.current) {
        heatLayerRef.current.remove();
        heatLayerRef.current = null;
      }

      // Shared premium marker family (matches the Journey Desk pin language):
      // a warm paper-ringed disc — marine for attractions, brass/ember for
      // restaurants. Placement (lat/lng) is unchanged; only the visual changes.
      const makeIcon = (variant: "attraction" | "restaurant") =>
        L.divIcon({
          html: `<span class="atlas-map-marker-dot atlas-map-marker-dot--${variant}"></span>`,
          className: "atlas-map-marker",
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });

      const attractionIcon = makeIcon("attraction");
      const restaurantIcon = makeIcon("restaurant");
      const heatPoints: [number, number, number][] = [];

      attractions.forEach((a, i) => {
        const [dLat, dLng] = goldenSpread(i);
        const lat = (a as AttractionSearchResult & { lat?: number }).lat ?? center[0] + dLat;
        const lng = (a as AttractionSearchResult & { lng?: number }).lng ?? center[1] + dLng;
        heatPoints.push([lat, lng, computeWeight(a)]);
        const marker = L.marker([lat, lng], { icon: attractionIcon });
        marker.on("click", () => {
          onMarkerClick?.(a.id);
          setPopup({ type: "attraction", item: a });
        });
        marker.addTo(map);
        markersRef.current.set(a.id, marker);
      });

      restaurants.forEach((r, i) => {
        const [dLat, dLng] = goldenSpread(i + attractions.length);
        const lat = (r as RestaurantSearchResult & { lat?: number }).lat ?? center[0] + dLat;
        const lng = (r as RestaurantSearchResult & { lng?: number }).lng ?? center[1] + dLng;
        heatPoints.push([lat, lng, computeWeight(r)]);
        const marker = L.marker([lat, lng], { icon: restaurantIcon });
        marker.on("click", () => {
          onMarkerClick?.(r.id);
          setPopup({ type: "restaurant", item: r });
        });
        marker.addTo(map);
        markersRef.current.set(r.id, marker);
      });

      // Build heat layer using window.L extended by the leaflet.heat CDN script
      type LeafletWithHeat = typeof L & {
        heatLayer?: (pts: [number, number, number][], opts: unknown) => HeatLayer;
      };
      const gL = (window as unknown as Record<string, unknown>).L as LeafletWithHeat | undefined;
      if (heatPoints.length > 0 && heatScriptLoaded && gL?.heatLayer) {
        heatLayerRef.current = gL.heatLayer(heatPoints, {
          radius: 35,
          blur: 25,
          maxZoom: 15,
          max: 1.0,
          // blue (low) → amber (mid) → red → violet (peak density)
          gradient: { 0.2: "#60a5fa", 0.5: "#f59e0b", 0.8: "#ef4444", 1.0: "#7c3aed" },
        });
      }

      applyMode(mapModeRef.current);
    });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapReady, center, attractions, restaurants, onMarkerClick, heatScriptLoaded, applyMode]);

  // Re-apply visibility whenever the user flips the toggle
  useEffect(() => {
    applyMode(mapMode);
  }, [mapMode, applyMode]);

  // Pan to active marker when it changes, and reflect it with the shared
  // active-marker ring (brass lift) — visual only; placement is unchanged.
  useEffect(() => {
    markersRef.current.forEach((m, id) => {
      const el = m.getElement();
      if (el) el.classList.toggle("atlas-map-marker--active", id === activeMarkerId);
    });
    if (!activeMarkerId || !mapInstanceRef.current) return;
    const marker = markersRef.current.get(activeMarkerId);
    if (marker) mapInstanceRef.current.panTo(marker.getLatLng(), { animate: true });
  }, [activeMarkerId]);

  // Draw / remove best area highlight circle
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current) return;
    let cancelled = false;

    if (bestAreaCircleRef.current) {
      bestAreaCircleRef.current.remove();
      bestAreaCircleRef.current = null;
    }

    if (!bestArea) return;

    import("leaflet").then((mod) => {
      if (cancelled || !mapInstanceRef.current) return;
      const L = mod.default ?? mod;
      const radiusM = bestArea.radiusKm * 1000;
      const circle = L.circle([bestArea.centerLat, bestArea.centerLng], {
        radius: radiusM,
        color: "#7c3aed",
        weight: 2,
        opacity: 0.7,
        fillColor: "#7c3aed",
        fillOpacity: 0.08,
        dashArray: "6 4",
        className: "best-area-circle",
      }).addTo(mapInstanceRef.current);
      bestAreaCircleRef.current = circle;
    });

    return () => { cancelled = true; };
  }, [mapReady, bestArea]);

  const handleAddFromPopup = useCallback(async () => {
    if (!popup) return;
    setAddingId(popup.item.id);
    try {
      if (popup.type === "attraction") await onAddAttraction?.(popup.item);
      else await onAddRestaurant?.(popup.item as RestaurantSearchResult);
      setPopup(null);
    } finally {
      setAddingId(null);
    }
  }, [popup, onAddAttraction, onAddRestaurant]);

  return (
    <div className="relative flex flex-col gap-2" style={{ height: "100%" }}>
      {/* Loading overlay while geocoding */}
      {geocoding && (
        <div className="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-ds-paper/90">
          <Loader2 className="w-5 h-5 animate-spin text-ds-marine-ink" />
          <span className="ml-2 text-sm text-ds-folio-ink-mist">Locating {destination}…</span>
        </div>
      )}

      {/* Best area badge */}
      {bestArea && (
        <div className="flex items-start gap-2 px-3 py-2 rounded-xl bg-violet-50 border border-violet-200 shadow-sm">
          <span className="text-base leading-none mt-0.5">📍</span>
          <div className="min-w-0">
            <p className="text-sm font-bold text-violet-900 leading-tight">
              Best Area: {bestArea.areaName}
            </p>
            <p className="text-xs text-violet-600 mt-0.5 leading-snug">{bestArea.reason}</p>
          </div>
          <span className="ml-auto flex-shrink-0 text-[10px] font-bold text-violet-500 bg-violet-100 px-1.5 py-0.5 rounded-full">
            {bestArea.score.toFixed(0)}
          </span>
        </div>
      )}

      {/* Map element */}
      <div
        ref={mapContainerRef}
        className="atlas-map-surface flex-1 rounded-xl overflow-hidden border border-ds-hairline"
        style={{ minHeight: 380 }}
      />

      {/* Marker popup card — warm paper Atelier popup (matches Journey Desk) */}
      {popup && (
        <div className="atlas-map-popup absolute bottom-14 left-1 right-1 z-[900] p-3">
          <button
            onClick={() => setPopup(null)}
            aria-label="Close"
            className="absolute top-2 right-2 p-0.5 rounded text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          <p className="font-serif text-sm font-semibold text-ds-folio-ink pr-5 leading-tight">{popup.item.name}</p>
          <p className="text-xs text-ds-folio-ink-mist mt-0.5 leading-none">
            {popup.type === "attraction"
              ? (popup.item as AttractionSearchResult).category
              : (popup.item as RestaurantSearchResult).cuisine}
          </p>
          {popup.item.rating != null && (
            <div className="flex items-center gap-1 mt-1.5">
              <Star className="w-3 h-3 text-ds-accent fill-ds-accent" />
              <span className="text-xs font-semibold text-ds-folio-ink">{popup.item.rating.toFixed(1)}</span>
              {popup.item.numReviews != null && (
                <span className="text-xs text-ds-folio-ink-mist">({popup.item.numReviews.toLocaleString()})</span>
              )}
            </div>
          )}
          {popup.item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {popup.item.tags.slice(0, 4).map((t) => (
                <span key={t} className="atlas-map-popup-chip">
                  {t}
                </span>
              ))}
            </div>
          )}
          <button
            onClick={handleAddFromPopup}
            disabled={addingId !== null}
            className="mt-2.5 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-ds-marine-ink hover:bg-ds-marine-soft text-ds-paper text-xs font-semibold disabled:opacity-50 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
          >
            {addingId !== null
              ? <Loader2 className="w-3 h-3 animate-spin" />
              : <Plus className="w-3 h-3" />}
            Add to Trip
          </button>
        </div>
      )}

      {/* Legend + Pins/Heatmap toggle */}
      <div className="flex items-center gap-4 px-3 py-2 bg-ds-paper rounded-lg border border-ds-hairline shadow-sm text-xs text-ds-folio-ink-mist">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-ds-marine-ink flex-shrink-0" />
          {attractions.length} Attractions
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-ds-accent flex-shrink-0" />
          {restaurants.length} Restaurants
        </span>

        <div className="ml-auto flex rounded-lg overflow-hidden border border-ds-hairline">
          <button
            onClick={() => setMapMode("pins")}
            className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium transition-colors ${
              mapMode === "pins"
                ? "bg-ds-marine-ink text-ds-paper"
                : "bg-ds-paper text-ds-folio-ink-mist hover:bg-ds-linen"
            }`}
          >
            <MapPin className="w-3 h-3" />
            Pins
          </button>
          <button
            onClick={() => setMapMode("heatmap")}
            className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium transition-colors border-l border-ds-hairline ${
              mapMode === "heatmap"
                ? "bg-ds-accent text-ds-folio-ink"
                : "bg-ds-paper text-ds-folio-ink-mist hover:bg-ds-linen"
            }`}
          >
            <Layers className="w-3 h-3" />
            Heatmap
          </button>
        </div>
      </div>
    </div>
  );
}
