'use client';

import mapboxgl from 'mapbox-gl';
import { useEffect, useRef } from 'react';
import type { Listing } from '@/lib/types';
import { createListingGeoJSON, flyToListing, getMarkerColor } from '@/lib/map';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? process.env.MAPBOX_TOKEN ?? '';

export interface SearchMapProps {
  listings: Listing[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  focusListing?: Listing;
}

export const SearchMap = ({ listings, selectedId, onSelect, focusListing }: SearchMapProps) => {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [-98.5795, 39.8283],
      zoom: 3
    });

    map.addControl(new mapboxgl.NavigationControl());

    map.on('load', () => {
      map.addSource('listings', {
        type: 'geojson',
        data: createListingGeoJSON(listings)
      });

      map.addLayer({
        id: 'listing-points',
        type: 'circle',
        source: 'listings',
        paint: {
          'circle-radius': 8,
          'circle-color': ['case', ['==', ['get', 'id'], selectedId], getMarkerColor(true), getMarkerColor(false)]
        }
      });

      map.on('click', 'listing-points', (event) => {
        const id = event.features?.[0]?.properties?.id as string;
        if (id) onSelect(id);
      });

      mapRef.current = map;
    });

    return () => {
      map.remove();
    };
  }, [listings, onSelect, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (map.getLayer('listing-points')) {
      map.setPaintProperty('listing-points', 'circle-color', [
        'case',
        ['==', ['get', 'id'], selectedId],
        getMarkerColor(true),
        getMarkerColor(false)
      ]);
    }
  }, [selectedId]);

  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const geojson = createListingGeoJSON(listings);
    const source = map.getSource('listings') as mapboxgl.GeoJSONSource | undefined;
    source?.setData(geojson as any);
    if (focusListing) {
      flyToListing(map, focusListing);
    }
  }, [listings, focusListing]);

  return <div ref={mapContainer} className="h-full w-full" aria-label="Map results" role="application" />;
};
