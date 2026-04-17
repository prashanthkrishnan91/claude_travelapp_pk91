"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, Plus, Star, X } from "lucide-react";
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet";
import type { AttractionSearchResult, RestaurantSearchResult } from "@/types";

type PopupItem =
  | { type: "attraction"; item: AttractionSearchResult }
  | { type: "restaurant"; item: RestaurantSearchResult };

interface TripMapViewProps {
  destination: string;
  attractions: AttractionSearchResult[];
  restaurants: RestaurantSearchResult[];
  activeMarkerId?: string | null;
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
  return [40.7128, -74.006]; // fallback: NYC
}

// Deterministic golden-angle spiral spread for items without coordinates
function goldenSpread(index: number): [number, number] {
  const angle = (index * 137.508 * Math.PI) / 180;
  const radius = 0.006 * Math.sqrt(index + 1);
  return [Math.sin(angle) * radius, Math.cos(angle) * radius];
}

export function TripMapView({
  destination,
  attractions,
  restaurants,
  activeMarkerId,
  onMarkerClick,
  onAddAttraction,
  onAddRestaurant,
}: TripMapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);
  const markersRef = useRef<Map<string, LeafletMarker>>(new Map());
  const [center, setCenter] = useState<[number, number] | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [geocoding, setGeocoding] = useState(true);
  const [popup, setPopup] = useState<PopupItem | null>(null);
  const [addingId, setAddingId] = useState<string | null>(null);

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

    import("leaflet").then((mod) => {
      if (cancelled || !mapContainerRef.current || mapInstanceRef.current) return;
      const L = mod.default ?? mod;

      const map = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
      }).setView(center, 13);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
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
      markersRef.current.clear();
      setMapReady(false);
    };
  // center changes only when destination changes — intentional single-init
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center]);

  // Build / rebuild markers whenever map or data changes
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !center) return;
    let cancelled = false;

    import("leaflet").then((mod) => {
      if (cancelled || !mapInstanceRef.current) return;
      const L = mod.default ?? mod;
      const map = mapInstanceRef.current;

      markersRef.current.forEach((m) => m.remove());
      markersRef.current.clear();

      const makeIcon = (color: string) =>
        L.divIcon({
          html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2.5px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35)"></span>`,
          className: "",
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        });

      const blueIcon = makeIcon("#2563eb");
      const orangeIcon = makeIcon("#ea580c");

      attractions.forEach((a, i) => {
        const [dLat, dLng] = goldenSpread(i);
        const lat = (a as AttractionSearchResult & { lat?: number }).lat ?? center[0] + dLat;
        const lng = (a as AttractionSearchResult & { lng?: number }).lng ?? center[1] + dLng;
        const marker = L.marker([lat, lng], { icon: blueIcon });
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
        const marker = L.marker([lat, lng], { icon: orangeIcon });
        marker.on("click", () => {
          onMarkerClick?.(r.id);
          setPopup({ type: "restaurant", item: r });
        });
        marker.addTo(map);
        markersRef.current.set(r.id, marker);
      });
    });

    return () => { cancelled = true; };
  }, [mapReady, center, attractions, restaurants, onMarkerClick]);

  // Pan to active marker when it changes
  useEffect(() => {
    if (!activeMarkerId || !mapInstanceRef.current) return;
    const marker = markersRef.current.get(activeMarkerId);
    if (marker) mapInstanceRef.current.panTo(marker.getLatLng(), { animate: true });
  }, [activeMarkerId]);

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
        <div className="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-slate-50/90">
          <Loader2 className="w-5 h-5 animate-spin text-sky-500" />
          <span className="ml-2 text-sm text-slate-400">Locating {destination}…</span>
        </div>
      )}

      {/* Map element */}
      <div
        ref={mapContainerRef}
        className="flex-1 rounded-xl overflow-hidden border border-slate-200"
        style={{ minHeight: 380 }}
      />

      {/* Marker popup card */}
      {popup && (
        <div className="absolute bottom-14 left-1 right-1 z-[900] bg-white rounded-xl shadow-xl border border-slate-200 p-3">
          <button
            onClick={() => setPopup(null)}
            className="absolute top-2 right-2 p-0.5 rounded text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          <p className="text-sm font-bold text-slate-900 pr-5 leading-tight">{popup.item.name}</p>
          <p className="text-xs text-slate-400 mt-0.5 leading-none">
            {popup.type === "attraction"
              ? (popup.item as AttractionSearchResult).category
              : (popup.item as RestaurantSearchResult).cuisine}
          </p>
          {popup.item.rating != null && (
            <div className="flex items-center gap-1 mt-1.5">
              <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
              <span className="text-xs font-semibold text-amber-600">{popup.item.rating.toFixed(1)}</span>
              {popup.item.numReviews != null && (
                <span className="text-xs text-slate-400">({popup.item.numReviews.toLocaleString()})</span>
              )}
            </div>
          )}
          {popup.item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {popup.item.tags.slice(0, 4).map((t) => (
                <span
                  key={t}
                  className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    popup.type === "attraction"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-orange-100 text-orange-700"
                  }`}
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          <button
            onClick={handleAddFromPopup}
            disabled={addingId !== null}
            className="mt-2.5 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
          >
            {addingId !== null
              ? <Loader2 className="w-3 h-3 animate-spin" />
              : <Plus className="w-3 h-3" />}
            Add to Trip
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 px-3 py-2 bg-white rounded-lg border border-slate-100 shadow-sm text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600 flex-shrink-0" />
          {attractions.length} Attractions
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-orange-600 flex-shrink-0" />
          {restaurants.length} Restaurants
        </span>
        <span className="ml-auto text-[10px] text-slate-300">Click a pin to explore</span>
      </div>
    </div>
  );
}
