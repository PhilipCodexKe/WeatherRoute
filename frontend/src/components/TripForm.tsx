import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Calendar, Weight, Sliders, AlertTriangle, Search } from 'lucide-react';
import { geocodeLocation } from '../services/api';
import type { GeocodeResult } from '../types';

interface TripFormProps {
  onAnalyze: (params: {
    origin: [number, number];
    destination: [number, number];
    departure_time: string;
    load_weight_lbs: number;
    sampling_interval_miles: number;
    originLabel: string;
    destLabel: string;
  }) => void;
  isLoading: boolean;
}

export const TripForm: React.FC<TripFormProps> = ({ onAnalyze, isLoading }) => {
  const [originQuery, setOriginQuery] = useState('Denver, CO');
  const [originCoords, setOriginCoords] = useState<[number, number]>([39.7392, -104.9903]);
  const [originSuggestions, setOriginSuggestions] = useState<GeocodeResult[]>([]);
  const [showOriginDropdown, setShowOriginDropdown] = useState(false);
  const [hoveredOriginIdx, setHoveredOriginIdx] = useState<number | null>(null);

  const [destQuery, setDestQuery] = useState('Chicago, IL');
  const [destCoords, setDestCoords] = useState<[number, number]>([41.8781, -87.6298]);
  const [destSuggestions, setDestSuggestions] = useState<GeocodeResult[]>([]);
  const [showDestDropdown, setShowDestDropdown] = useState(false);
  const [hoveredDestIdx, setHoveredDestIdx] = useState<number | null>(null);

  const originRef = useRef<HTMLDivElement>(null);
  const destRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (originRef.current && !originRef.current.contains(e.target as Node)) {
        setShowOriginDropdown(false);
      }
      if (destRef.current && !destRef.current.contains(e.target as Node)) {
        setShowDestDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Set default departure to next top of hour
  const getInitialDeparture = () => {
    const d = new Date();
    d.setMinutes(0, 0, 0);
    d.setHours(d.getHours() + 1);
    const tzOffset = d.getTimezoneOffset() * 60000;
    return new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);
  };

  const [departureTime, setDepartureTime] = useState(getInitialDeparture());
  const [loadWeight, setLoadWeight] = useState(38000);
  const [stepMiles, setStepMiles] = useState<number>(25);

  // Debounced geocoding search for origin
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (originQuery && originQuery.length >= 2 && showOriginDropdown) {
        const res = await geocodeLocation(originQuery);
        setOriginSuggestions(res);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [originQuery, showOriginDropdown]);

  // Debounced geocoding search for destination
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (destQuery && destQuery.length >= 2 && showDestDropdown) {
        const res = await geocodeLocation(destQuery);
        setDestSuggestions(res);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [destQuery, showDestDropdown]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAnalyze({
      origin: originCoords,
      destination: destCoords,
      departure_time: new Date(departureTime).toISOString(),
      load_weight_lbs: loadWeight,
      sampling_interval_miles: stepMiles,
      originLabel: originQuery,
      destLabel: destQuery,
    });
  };

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px',
      boxShadow: 'var(--shadow-lg)',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--accent-blue)',
            boxShadow: '0 0 10px var(--accent-blue)'
          }} />
          Trip Parameters
        </h2>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>
          Live Weather Forecast
        </span>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Origin */}
        <div ref={originRef} style={{ position: 'relative' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
            <MapPin size={14} color="#10b981" /> Origin
          </label>
          <input
            type="text"
            value={originQuery}
            onChange={(e) => {
              setOriginQuery(e.target.value);
              setShowOriginDropdown(true);
            }}
            onFocus={() => setShowOriginDropdown(true)}
            placeholder="Search city, address..."
            style={inputStyle}
            required
          />
          {showOriginDropdown && originSuggestions.length > 0 && (
            <ul style={dropdownStyle}>
              {originSuggestions.map((item, idx) => (
                <li
                  key={idx}
                  onMouseDown={() => {
                    setOriginQuery(item.place_name);
                    setOriginCoords([item.latitude, item.longitude]);
                    setShowOriginDropdown(false);
                    setHoveredOriginIdx(null);
                  }}
                  onMouseEnter={() => setHoveredOriginIdx(idx)}
                  onMouseLeave={() => setHoveredOriginIdx(null)}
                  style={dropdownItemStyle(hoveredOriginIdx === idx)}
                >
                  <MapPin size={13} color={hoveredOriginIdx === idx ? '#10b981' : '#8b949e'} style={{ marginTop: '2px', flexShrink: 0, transition: 'color 0.15s' }} />
                  <span>{item.place_name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Destination */}
        <div ref={destRef} style={{ position: 'relative' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
            <MapPin size={14} color="#ef4444" /> Destination
          </label>
          <input
            type="text"
            value={destQuery}
            onChange={(e) => {
              setDestQuery(e.target.value);
              setShowDestDropdown(true);
            }}
            onFocus={() => setShowDestDropdown(true)}
            placeholder="Search city, address..."
            style={inputStyle}
            required
          />
          {showDestDropdown && destSuggestions.length > 0 && (
            <ul style={dropdownStyle}>
              {destSuggestions.map((item, idx) => (
                <li
                  key={idx}
                  onMouseDown={() => {
                    setDestQuery(item.place_name);
                    setDestCoords([item.latitude, item.longitude]);
                    setShowDestDropdown(false);
                    setHoveredDestIdx(null);
                  }}
                  onMouseEnter={() => setHoveredDestIdx(idx)}
                  onMouseLeave={() => setHoveredDestIdx(null)}
                  style={dropdownItemStyle(hoveredDestIdx === idx)}
                >
                  <MapPin size={13} color={hoveredDestIdx === idx ? '#ef4444' : '#8b949e'} style={{ marginTop: '2px', flexShrink: 0, transition: 'color 0.15s' }} />
                  <span>{item.place_name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Departure Time & Load Weight Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <Calendar size={13} /> Departure
            </label>
            <input
              type="datetime-local"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
              style={inputStyle}
              required
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <Weight size={13} /> Load (lbs)
            </label>
            <input
              type="number"
              min="0"
              max="100000"
              step="1"
              value={loadWeight}
              onChange={(e) => setLoadWeight(Number(e.target.value))}
              style={inputStyle}
              required
            />
          </div>
        </div>

        {/* Sampling Interval Toggle */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              <Sliders size={13} /> Checkpoint Spacing
            </label>
            <span style={{ fontSize: '11px', color: 'var(--accent-blue)', fontWeight: 600 }} className="mono">
              Every {stepMiles} mi
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
            {[10, 25, 50].map((miles) => (
              <button
                type="button"
                key={miles}
                onClick={() => setStepMiles(miles)}
                style={{
                  padding: '7px 0',
                  borderRadius: '6px',
                  border: stepMiles === miles ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  background: stepMiles === miles ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  color: stepMiles === miles ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {miles} mi
              </button>
            ))}
          </div>
        </div>

        {/* Load Rules Indicator Helper */}
        <div style={{
          padding: '8px 10px',
          borderRadius: '6px',
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          fontSize: '11px',
          color: '#fbbf24',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          <span>
            {loadWeight > 40000
              ? 'Very heavy load — strong winds (35+ mph) can make this route unsafe. Expect more restricted segments.'
              : loadWeight > 30000
              ? 'Heavy load — winds above 45 mph may make some road segments too dangerous to drive through.'
              : 'Normal load — standard wind safety limits apply along the route.'}
          </span>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          style={{
            marginTop: '4px',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            background: isLoading
              ? 'var(--text-muted)'
              : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
            color: '#ffffff',
            fontWeight: 700,
            fontSize: '14px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            boxShadow: '0 4px 15px rgba(37, 99, 235, 0.35)',
            transition: 'all 0.2s ease',
          }}
        >
          {isLoading ? (
            <>Calculating 3 Routes & Weather...</>
          ) : (
            <>
              <Search size={16} /> Analyze 3 Route Options
            </>
          )}
        </button>
      </form>
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: '8px',
  background: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid rgba(255,255,255,.08)',
  color: '#e6edf3',
  fontSize: '13px',
  fontWeight: 500,
  outline: 'none',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
};

const dropdownStyle: React.CSSProperties = {
  position: 'absolute',
  top: '100%',
  left: 0,
  right: 0,
  zIndex: 9999,
  background: '#1c2230',
  border: '1px solid rgba(255,255,255,.12)',
  borderRadius: '10px',
  marginTop: '6px',
  padding: '4px',
  listStyle: 'none',
  boxShadow: '0 8px 32px rgba(0,0,0,0.6), 0 2px 8px rgba(0,0,0,0.4)',
  maxHeight: '200px',
  overflowY: 'auto',
  backdropFilter: 'blur(12px)',
};

const dropdownItemStyle = (hovered: boolean): React.CSSProperties => ({
  padding: '9px 12px',
  fontSize: '12.5px',
  lineHeight: '1.4',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'flex-start',
  gap: '9px',
  borderRadius: '6px',
  color: hovered ? '#e6edf3' : '#8b949e',
  background: hovered ? 'rgba(59,130,246,0.12)' : 'transparent',
  borderBottom: 'none',
  transition: 'background 0.12s ease, color 0.12s ease',
  userSelect: 'none',
});
