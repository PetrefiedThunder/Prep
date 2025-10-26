import type mapboxgl from 'mapbox-gl';
import type { Listing } from './types';

export const getMarkerColor = (selected: boolean) =>
  selected ? 'hsl(11 85% 54%)' : 'hsl(222 20% 35%)';

export const createListingGeoJSON = (items: Listing[]) => ({
  type: 'FeatureCollection' as const,
  features: items.map((listing) => ({
    type: 'Feature' as const,
    geometry: {
      type: 'Point' as const,
      coordinates: listing.coordinates
    },
    properties: {
      id: listing.id,
      title: listing.title,
      price: listing.pricePerNight,
      rating: listing.rating
    }
  }))
});

export const flyToListing = (map: mapboxgl.Map, listing: Listing) => {
  map.flyTo({ center: listing.coordinates, zoom: 12, speed: 0.8 });
};
