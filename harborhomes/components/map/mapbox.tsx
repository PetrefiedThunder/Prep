"use client";

import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef } from "react";
import type { Listing } from "@/lib/types";
import { listingsToGeoJSON } from "@/lib/map";

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? process.env.MAPBOX_TOKEN ?? "mock";

interface MapboxProps {
  listings: Listing[];
  selectedId?: string;
  onSelect?: (id: string) => void;
}

export function Mapbox({ listings, selectedId, onSelect }: MapboxProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [-98.5795, 39.8283],
      zoom: 3
    });

    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }));

    map.on("load", () => {
      map.addSource("listings", {
        type: "geojson",
        data: listingsToGeoJSON(listings)
      });

      map.addLayer({
        id: "listing-points",
        type: "circle",
        source: "listings",
        paint: {
          "circle-radius": ["case", ["==", ["get", "id"], selectedId ?? ""], 12, 8],
          "circle-color": "#ec6a4c",
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2
        }
      });

      map.on("mouseenter", "listing-points", () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", "listing-points", () => {
        map.getCanvas().style.cursor = "";
      });

      map.on("click", "listing-points", (event) => {
        const feature = event.features?.[0];
        const id = feature?.properties?.id as string | undefined;
        if (id) {
          onSelect?.(id);
        }
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [listings, onSelect, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("listing-points")) return;

    const source = map.getSource("listings") as mapboxgl.GeoJSONSource | undefined;
    if (source) {
      source.setData(listingsToGeoJSON(listings));
    }

    map.setPaintProperty("listing-points", "circle-radius", ["case", ["==", ["get", "id"], selectedId ?? ""], 12, 8]);

    if (listings.length) {
      const bounds = listings.reduce((acc, listing) => {
        return acc.extend([listing.coordinates.longitude, listing.coordinates.latitude]);
      }, new mapboxgl.LngLatBounds());
      map.fitBounds(bounds, { padding: 60, maxZoom: 10, duration: 800 });
    }
  }, [listings, selectedId]);

  return <div ref={mapContainer} className="h-full w-full rounded-3xl" aria-label="Map view" />;
}
