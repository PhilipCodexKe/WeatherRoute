import type { GeocodeResult, TripAnalysisResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

export async function geocodeLocation(query: string): Promise<GeocodeResult[]> {
  if (!query || query.trim().length < 2) return [];
  try {
    const res = await fetch(`${API_BASE_URL}/geocode/?q=${encodeURIComponent(query.trim())}`);
    if (!res.ok) throw new Error('Geocoding request failed');
    const data = await res.json();
    return data.results || [];
  } catch (err) {
    console.error('Geocoding error:', err);
    return [];
  }
}

export interface AnalyzeTripParams {
  origin: [number, number]; // [lat, lon]
  destination: [number, number]; // [lat, lon]
  departure_time: string;
  load_weight_lbs: number;
  sampling_interval_miles: number;
}

export async function analyzeTrip(params: AnalyzeTripParams): Promise<TripAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/analyze/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    let msg = 'Failed to analyze routes and weather';
    try {
      const parsed = JSON.parse(errorBody);
      msg = parsed.error || JSON.stringify(parsed);
    } catch {
      msg = errorBody || msg;
    }
    throw new Error(msg);
  }

  return res.json();
}
