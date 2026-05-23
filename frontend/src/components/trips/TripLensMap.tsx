"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet";

// Journey Desk v2C — real Trip Lens pin map.
//
// Plots ONLY pins handed in by MapFoldOut, each built from coordinates that
// already passed the shared coordinate normalizer (real lat/lng in source data).
// Positions are taken verbatim from each pin — never network-resolved, never
// spread by position, never inferred, never fabricated. The map view is derived
// purely from the real pin coordinates: one pin → center on it; many pins → fit
// their bounds. No heatmap, no connecting line, no proximity claim.

export interface TripLensPin {
  id: string;
  lat: number;
  lng: number;
  title: string;
  kind: string;
  dayNumber: number;
  time: string | null;
  order: number;
  mapsUrl: string;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function popupHtml(pin: TripLensPin): string {
  const meta = [`Day ${pin.dayNumber}`, pin.time ? pin.time : null, pin.kind]
    .filter(Boolean)
    .map((part) => escapeHtml(String(part)))
    .join(" · ");
  return (
    `<div class="jd-trip-pin-popup">` +
    `<span class="jd-trip-pin-popup-title">${escapeHtml(pin.title)}</span>` +
    `<span class="jd-trip-pin-popup-meta">${meta}</span>` +
    `<a class="jd-trip-pin-popup-link" href="${escapeHtml(pin.mapsUrl)}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>` +
    `</div>`
  );
}

export interface TripLensMapProps {
  pins: TripLensPin[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

export function TripLensMap({ pins, selectedId, onSelect }: TripLensMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markersRef = useRef<Map<string, LeafletMarker>>(new Map());
  const [ready, setReady] = useState(false);

  // Inject Leaflet CSS once (same CDN stylesheet the discovery map uses).
  useEffect(() => {
    const CSS_ID = "leaflet-css";
    if (document.getElementById(CSS_ID)) return;
    const link = document.createElement("link");
    link.id = CSS_ID;
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);
  }, []);

  // Initialize the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;
    const markers = markersRef.current;

    import("leaflet").then((mod) => {
      if (cancelled || !containerRef.current || mapRef.current) return;
      const L = mod.default ?? mod;
      const map = L.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
      });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);
      mapRef.current = map;
      // Drawer animates in; recompute size on the next frame so tiles render.
      requestAnimationFrame(() => {
        if (!cancelled && mapRef.current) mapRef.current.invalidateSize();
      });
      if (!cancelled) setReady(true);
    });

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
      markers.clear();
      setReady(false);
    };
  }, []);

  // Build markers and fit the view from the real pin coordinates only.
  useEffect(() => {
    if (!ready || !mapRef.current) return;
    let cancelled = false;

    import("leaflet").then((mod) => {
      if (cancelled || !mapRef.current) return;
      const L = mod.default ?? mod;
      const map = mapRef.current;

      markersRef.current.forEach((m) => m.remove());
      markersRef.current.clear();

      const latlngs: [number, number][] = [];
      pins.forEach((pin) => {
        const icon = L.divIcon({
          html: `<span class="jd-trip-pin">${escapeHtml(String(pin.order))}</span>`,
          className: "jd-trip-pin-wrap",
          iconSize: [26, 26],
          iconAnchor: [13, 13],
          popupAnchor: [0, -13],
        });
        const marker = L.marker([pin.lat, pin.lng], { icon, title: pin.title });
        marker.bindPopup(popupHtml(pin), { closeButton: true, className: "jd-trip-pin-popup-shell" });
        marker.on("click", () => onSelect?.(pin.id));
        marker.addTo(map);
        markersRef.current.set(pin.id, marker);
        latlngs.push([pin.lat, pin.lng]);
      });

      // Center / bounds derived ONLY from real pins.
      if (latlngs.length === 1) {
        map.setView(latlngs[0], 14);
      } else if (latlngs.length > 1) {
        map.fitBounds(latlngs, { padding: [36, 36], maxZoom: 15 });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [ready, pins, onSelect]);

  // Open the popup for the externally selected pin.
  useEffect(() => {
    if (!ready || !selectedId) return;
    const marker = markersRef.current.get(selectedId);
    if (marker) marker.openPopup();
  }, [ready, selectedId]);

  return (
    <div
      ref={containerRef}
      data-testid="journey-desk-trip-map-canvas"
      className="jd-trip-map w-full"
      aria-label="Map of placed trip stops with real coordinates"
      role="application"
    />
  );
}
