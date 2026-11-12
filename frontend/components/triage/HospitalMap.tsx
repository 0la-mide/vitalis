"use client";

import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

type Point = { id: string; name: string; lat: number; lng: number; highlight?: boolean };

const pin = (color: string) =>
  L.divIcon({
    className: "",
    html: `<div style="width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:${color};border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 22],
  });

export default function HospitalMap({ points, me }: { points: Point[]; me?: { lat: number; lng: number } | null }) {
  const center = me ?? (points[0] ? { lat: points[0].lat, lng: points[0].lng } : { lat: 7.1475, lng: 3.3619 });
  return (
    <MapContainer
      center={[center.lat, center.lng]}
      zoom={13}
      scrollWheelZoom={false}
      className="h-56 w-full rounded-2xl"
      attributionControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {me ? (
        <Marker position={[me.lat, me.lng]} icon={pin("#2563eb")}>
          <Popup>You</Popup>
        </Marker>
      ) : null}
      {points.map((p) => (
        <Marker key={p.id} position={[p.lat, p.lng]} icon={pin(p.highlight ? "#046c4e" : "#7aa596")}>
          <Popup>{p.name}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
