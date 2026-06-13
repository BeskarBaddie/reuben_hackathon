"use client";

import MapboxDraw from "@mapbox/mapbox-gl-draw";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import { FormEvent, useEffect, useRef, useState } from "react";
import type { BoundaryGeometry } from "@/lib/types";

type Props = {
  boundary: BoundaryGeometry | null;
  onBoundaryChange: (boundary: BoundaryGeometry | null) => void;
};

type GeocodingFeature = {
  id: string;
  place_name: string;
  center: [number, number];
  bbox?: [number, number, number, number];
};

const boundaryStyles: MapboxDraw.MapboxDrawOptions["styles"] = [
  {
    id: "gl-draw-polygon-fill-inactive",
    type: "fill",
    filter: ["all", ["==", "active", "false"], ["==", "$type", "Polygon"], ["!=", "mode", "static"]],
    paint: {
      "fill-color": "#1f7a4d",
      "fill-outline-color": "#0b4f2c",
      "fill-opacity": 0.28
    }
  },
  {
    id: "gl-draw-polygon-stroke-inactive",
    type: "line",
    filter: ["all", ["==", "active", "false"], ["==", "$type", "Polygon"], ["!=", "mode", "static"]],
    layout: {
      "line-cap": "round",
      "line-join": "round"
    },
    paint: {
      "line-color": "#062f1b",
      "line-width": 4
    }
  },
  {
    id: "gl-draw-polygon-fill-active",
    type: "fill",
    filter: ["all", ["==", "active", "true"], ["==", "$type", "Polygon"]],
    paint: {
      "fill-color": "#1f7a4d",
      "fill-outline-color": "#0b4f2c",
      "fill-opacity": 0.22
    }
  },
  {
    id: "gl-draw-polygon-stroke-active",
    type: "line",
    filter: ["all", ["==", "active", "true"], ["==", "$type", "Polygon"]],
    layout: {
      "line-cap": "round",
      "line-join": "round"
    },
    paint: {
      "line-color": "#062f1b",
      "line-dasharray": [0.2, 2],
      "line-width": 4
    }
  },
  {
    id: "gl-draw-polygon-and-line-vertex-active",
    type: "circle",
    filter: ["all", ["==", "meta", "vertex"], ["==", "$type", "Point"]],
    paint: {
      "circle-color": "#ffffff",
      "circle-radius": 5,
      "circle-stroke-color": "#062f1b",
      "circle-stroke-width": 2
    }
  }
];

export default function BoundaryMap({ boundary, onBoundaryChange }: Props) {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodingFeature[]>([]);
  const [message, setMessage] = useState(token ? "" : "Set NEXT_PUBLIC_MAPBOX_TOKEN to enable Mapbox.");

  useEffect(() => {
    if (!token || !mapContainerRef.current || mapRef.current) {
      return;
    }

    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [32.5825, 0.3476],
      zoom: 13,
      preserveDrawingBuffer: false
    });
    mapRef.current = map;

    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-left");
    map.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: "metric" }), "bottom-left");

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: { polygon: true, trash: true },
      defaultMode: "draw_polygon",
      styles: boundaryStyles
    });
    drawRef.current = draw;
    map.addControl(draw, "top-left");

    function updateBoundary() {
      const collection = draw.getAll();
      const polygon = collection.features.find((feature) => feature.geometry.type === "Polygon");
      if (!polygon || polygon.geometry.type !== "Polygon") {
        onBoundaryChange(null);
        return;
      }
      onBoundaryChange({
        type: "Polygon",
        coordinates: polygon.geometry.coordinates as BoundaryGeometry["coordinates"]
      });
    }

    map.on("draw.create", () => {
      const features = draw.getAll().features;
      if (features.length > 1) {
        features.slice(0, -1).forEach((feature) => {
          if (feature.id) draw.delete(String(feature.id));
        });
      }
      updateBoundary();
    });
    map.on("draw.update", updateBoundary);
    map.on("draw.delete", updateBoundary);

    return () => {
      map.remove();
      mapRef.current = null;
      drawRef.current = null;
    };
  }, [onBoundaryChange, token]);

  function fitBoundary() {
    if (!boundary || !mapRef.current) return;
    const bounds = new mapboxgl.LngLatBounds();
    boundary.coordinates[0].forEach((coordinate) => bounds.extend(coordinate as [number, number]));
    mapRef.current.fitBounds(bounds, { padding: 48, maxZoom: 17 });
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !query.trim()) return;

    const params = new URLSearchParams({
      access_token: token,
      autocomplete: "true",
      limit: "5",
      proximity: "32.5825,0.3476"
    });

    const response = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?${params}`
    );
    const payload = await response.json();
    setResults(payload.features ?? []);
  }

  function chooseResult(result: GeocodingFeature) {
    if (!mapRef.current) return;
    if (result.bbox) {
      mapRef.current.fitBounds(
        [
          [result.bbox[0], result.bbox[1]],
          [result.bbox[2], result.bbox[3]]
        ],
        { padding: 48, maxZoom: 15 }
      );
    } else {
      mapRef.current.flyTo({ center: result.center, zoom: 14 });
    }
    setResults([]);
    setQuery(result.place_name);
  }

  return (
    <div className="mapbox-shell">
      <form className="mapbox-search" onSubmit={search}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search region, town, village, or coordinates"
        />
        <button type="submit" disabled={!token}>
          Search
        </button>
      </form>

      {results.length ? (
        <div className="mapbox-results">
          {results.map((result) => (
            <button key={result.id} type="button" onClick={() => chooseResult(result)}>
              {result.place_name}
            </button>
          ))}
        </div>
      ) : null}

      {message ? <p className="mapbox-warning">{message}</p> : null}
      <div ref={mapContainerRef} className="boundary-map" />
      <div className="mapbox-actions">
        <button type="button" disabled={!boundary} onClick={fitBoundary}>
          Fit boundary
        </button>
      </div>
    </div>
  );
}
