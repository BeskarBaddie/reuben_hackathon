"use client";

import { MapContainer, TileLayer } from "react-leaflet";

const DEFAULT_CENTER: [number, number] = [-1.2921, 36.8219]; // Nairobi

export default function FarmMap() {
  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={13}
      style={{ height: "70vh", width: "100%", borderRadius: 8 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
    </MapContainer>
  );
}
