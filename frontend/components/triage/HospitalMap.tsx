"use client";

import L from "leaflet";
import { useEffect, useRef } from "react";

type Point = { id: string; name: string; lat: number; lng: number; highlight?: boolean };

const pin = (color: string) =>
  L.divIcon({
    className: "",
    html: `<div style="width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:${color};border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 22],
  });

/**
 * Plain Leaflet with explicit create/remove. react-leaflet's MapContainer breaks when Next 16 hides and
 * re-shows a cached route (effects reconnect on the same DOM node), so we own the lifecycle here.
 */
export default function HospitalMap({ points, me }: { points: Point[]; me?: { lat: number; lng: number } | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const key = JSON.stringify({ points, me });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const data = JSON.parse(key) as { points: Point[]; me?: { lat: number; lng: number } | null };
    const center = data.me ?? data.points[0] ?? { lat: 7.1475, lng: 3.3619 };
    const map = L.map(el, { scrollWheelZoom: false }).setView([center.lat, center.lng], 13);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    const markers = data.points.map((p) =>
      L.marker([p.lat, p.lng], { icon: pin(p.highlight ? "#046c4e" : "#7aa596") }).bindPopup(p.name).addTo(map),
    );
    if (data.me) L.marker([data.me.lat, data.me.lng], { icon: pin("#2563eb") }).bindPopup("You").addTo(map);
    if (markers.length > 1) map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
    return () => {
      map.remove();
    };
  }, [key]);

  return <div ref={ref} className="h-56 w-full rounded-2xl" />;
}
