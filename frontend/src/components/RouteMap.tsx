import React, { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { RouteOption, HeatmapGridPoint } from '../types';

interface RouteMapProps {
  routes: RouteOption[];
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
  corridorHeatmap: HeatmapGridPoint[];
  forecastHour: number;
}

export const RouteMap: React.FC<RouteMapProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  corridorHeatmap,
  forecastHour,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Initialize MapLibre
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'mapbox-dark': {
            type: 'raster',
            tiles: [
              `https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{z}/{x}/{y}?access_token=${import.meta.env.VITE_MAPBOX_ACCESS_TOKEN}`,
            ],
            tileSize: 512,
            attribution: '&copy; <a href="https://www.mapbox.com/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxzoom: 22,
          },
        },
        layers: [
          {
            id: 'mapbox-dark-layer',
            type: 'raster',
            source: 'mapbox-dark',
            minzoom: 0,
            maxzoom: 22,
          },
        ],
      },
      center: [-98.5795, 39.8283], // US Center
      zoom: 3.8,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Route Layers and Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !routes || routes.length === 0) return;

    const setupLayers = () => {
      // 1. Remove existing route sources and layers
      ['route-line-glow', 'route-line-main'].forEach((id) => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      if (map.getSource('routes-source')) map.removeSource('routes-source');

      ['checkpoint-circles', 'checkpoint-inner'].forEach((id) => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      if (map.getSource('checkpoints-source')) map.removeSource('checkpoints-source');

      // 2. Prepare GeoJSON FeatureCollection for Routes
      const routeFeatures: any[] = routes.map((r) => ({
        type: 'Feature',
        properties: {
          id: r.id,
          name: r.name,
          isSelected: r.id === selectedRouteId,
          isRecommended: r.is_recommended,
          rank: r.rank,
        },
        geometry: {
          type: 'LineString',
          coordinates: r.geometry.map((pt) => [pt.longitude, pt.latitude]),
        },
      }));

      map.addSource('routes-source', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: routeFeatures,
        },
      });

      // Background route line (thicker for selected)
      map.addLayer({
        id: 'route-line-glow',
        type: 'line',
        source: 'routes-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': [
            'case',
            ['get', 'isSelected'],
            '#3b82f6',
            ['get', 'isRecommended'],
            '#10b981',
            '#64748b',
          ],
          'line-width': ['case', ['get', 'isSelected'], 7, 3],
          'line-opacity': ['case', ['get', 'isSelected'], 0.9, 0.4],
        },
      });

      // Click listener for routes
      map.on('click', 'route-line-glow', (e: any) => {
        if (e.features && e.features[0]) {
          const clickedId = e.features[0].properties?.id;
          if (clickedId) onSelectRoute(clickedId);
        }
      });

      // 3. Add Checkpoints for the Selected Route
      const activeRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];
      const checkpointFeatures: any[] = (activeRoute.checkpoints || []).map((cp) => ({
        type: 'Feature',
        properties: {
          index: cp.index,
          riskLevel: cp.risk.level,
          riskLabel: cp.risk.label,
          eta: cp.eta,
          distance: cp.distance_miles,
          wind: cp.weather.wind_mph,
          rain: cp.weather.rain_in_per_hr,
          snow: cp.weather.snow_in_per_hr,
          temp: cp.weather.temperature_f ?? '--',
          loadAdjustment: cp.risk.load_adjustment || '',
        },
        geometry: {
          type: 'Point',
          coordinates: [cp.longitude, cp.latitude],
        },
      }));

      map.addSource('checkpoints-source', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: checkpointFeatures,
        },
      });

      map.addLayer({
        id: 'checkpoint-circles',
        type: 'circle',
        source: 'checkpoints-source',
        paint: {
          'circle-radius': 7,
          'circle-color': [
            'match',
            ['get', 'riskLevel'],
            1, '#10b981',
            2, '#f59e0b',
            3, '#f97316',
            4, '#ef4444',
            5, '#9333ea',
            '#ffffff',
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#0a0e17',
        },
      });

      // Interactive popup on hover/click over checkpoint
      map.on('mouseenter', 'checkpoint-circles', (e: any) => {
        map.getCanvas().style.cursor = 'pointer';
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const coords = (e.features[0].geometry as any).coordinates.slice();

        const etaFormatted = new Date(props.eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const html = `
          <div style="font-family: inherit; font-size: 12px; color: #f8fafc; padding: 2px;">
            <div style="font-weight: 700; font-size: 13px; margin-bottom: 4px; display: flex; justify-content: space-between; gap: 8px;">
              <span>Mile ${Number(props.distance).toFixed(0)}</span>
              <span style="color: #94a3b8;">ETA ${etaFormatted}</span>
            </div>
            <div style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px; margin-bottom: 6px; background: ${
              props.riskLevel === 5 ? 'rgba(147, 51, 234, 0.3)' : props.riskLevel === 4 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'
            }; color: #ffffff;">
              Risk: ${props.riskLabel}
            </div>
            ${props.loadAdjustment ? `<div style="font-size: 10px; color: #fbbf24; margin-bottom: 4px;">⚠️ ${props.loadAdjustment}</div>` : ''}
            <div style="font-size: 11px; color: #94a3b8; display: flex; flex-direction: column; gap: 2px;">
              <div>Wind: <strong>${props.wind} mph</strong></div>
              <div>Rain: <strong>${props.rain} in/hr</strong> | Snow: <strong>${props.snow} in/hr</strong></div>
              <div>Temp: <strong>${props.temp}°F</strong></div>
            </div>
          </div>
        `;

        if (popupRef.current) popupRef.current.remove();
        popupRef.current = new maplibregl.Popup({ closeButton: false, offset: 10 })
          .setLngLat(coords)
          .setHTML(html)
          .addTo(map);
      });

      map.on('mouseleave', 'checkpoint-circles', () => {
        map.getCanvas().style.cursor = '';
        if (popupRef.current) popupRef.current.remove();
      });

      // Fit map bounds to encompass active route
      const bounds = new maplibregl.LngLatBounds();
      activeRoute.geometry.forEach((pt) => bounds.extend([pt.longitude, pt.latitude]));
      map.fitBounds(bounds, { padding: 60, maxZoom: 11 });
    };

    if (map.isStyleLoaded()) {
      setupLayers();
    } else {
      map.once('load', setupLayers);
    }
  }, [routes, selectedRouteId, onSelectRoute]);

  // Update Corridor Heatmap Layer Based on Forecast Slider
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !corridorHeatmap || corridorHeatmap.length === 0) return;

    const setupHeatmap = () => {
      // Build GeoJSON with risk at the current forecast hour
      const heatmapFeatures: any[] = corridorHeatmap.map((pt) => ({
        type: 'Feature',
        properties: {
          riskScore: pt.risks[forecastHour] || 1, // 1 to 5
        },
        geometry: {
          type: 'Point',
          coordinates: [pt.longitude, pt.latitude],
        },
      }));

      const sourceData: any = {
        type: 'FeatureCollection',
        features: heatmapFeatures,
      };

      if (map.getSource('heatmap-source')) {
        (map.getSource('heatmap-source') as maplibregl.GeoJSONSource).setData(sourceData);
      } else {
        map.addSource('heatmap-source', {
          type: 'geojson',
          data: sourceData,
        });

        // Add GPU Heatmap Layer below the route line
        map.addLayer(
          {
            id: 'corridor-weather-heat',
            type: 'heatmap',
            source: 'heatmap-source',
            maxzoom: 9,
            paint: {
              'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'riskScore'],
                1, 0.1,
                2, 0.4,
                3, 0.7,
                4, 1.0,
                5, 1.5,
              ],
              'heatmap-intensity': 0.8,
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(0, 0, 0, 0)',
                0.2, '#10b981',
                0.4, '#f59e0b',
                0.6, '#f97316',
                0.8, '#ef4444',
                1.0, '#9333ea',
              ],
              'heatmap-radius': 45,
              'heatmap-opacity': 0.55,
            },
          },
          'route-line-glow'
        );
      }
    };

    if (map.isStyleLoaded()) {
      setupHeatmap();
    } else {
      map.once('load', setupHeatmap);
    }
  }, [corridorHeatmap, forecastHour]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
};
