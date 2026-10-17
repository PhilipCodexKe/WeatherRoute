import React from 'react';
import type { RouteOption } from '../types';
import { ShieldCheck } from 'lucide-react';

interface RouteComparisonProps {
  routes: RouteOption[];
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
}

export const RouteComparison: React.FC<RouteComparisonProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
}) => {
  if (!routes || routes.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Route Options ({routes.length})
        </h3>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          Ranked by Weather Risk
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {routes.map((route) => {
          const isSelected = route.id === selectedRouteId;
          const isRecommended = route.is_recommended;
          const summary = route.summary;

          return (
            <div
              key={route.id}
              onClick={() => onSelectRoute(route.id)}
              style={{
                position: 'relative',
                background: isSelected
                  ? 'var(--bg-surface-elevated)'
                  : 'var(--bg-surface)',
                border: isSelected
                  ? '1.5px solid var(--accent-blue)'
                  : isRecommended
                  ? '1.5px solid rgba(16, 185, 129, 0.4)'
                  : '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isSelected ? '0 4px 20px rgba(59, 130, 246, 0.15)' : 'none',
              }}
            >
              {/* Recommended Badge */}
              {isRecommended && (
                <div style={{
                  position: 'absolute',
                  top: '-9px',
                  right: '12px',
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  color: '#ffffff',
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  boxShadow: '0 2px 6px rgba(16, 185, 129, 0.4)',
                  letterSpacing: '0.03em',
                  textTransform: 'uppercase',
                }}>
                  <ShieldCheck size={12} />
                  RECOMMENDED
                </div>
              )}

              {/* Header: Name + Rank */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: isRecommended ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                    color: isRecommended ? '#10b981' : 'var(--text-secondary)',
                    fontSize: '11px',
                    fontWeight: 700,
                  }}>
                    {route.rank}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                    {route.name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }} className="mono">
                  <span>{route.distance_miles.toFixed(0)} mi</span>
                  <span>•</span>
                  <span>{route.duration_hours.toFixed(1)} hrs</span>
                </div>
              </div>

              {/* Recommendation Reason Banner */}
              <div style={{
                fontSize: '11px',
                color: isRecommended ? '#6ee7b7' : 'var(--text-muted)',
                background: isRecommended ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                padding: '6px 8px',
                borderRadius: '6px',
                marginBottom: '10px',
                lineHeight: '1.4',
                borderLeft: isRecommended ? '3px solid #10b981' : '3px solid var(--text-muted)',
              }}>
                {route.recommendation_reason}
              </div>

              {/* Weather Risk Miles Breakdown */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', textAlign: 'center' }}>
                {/* No Travel */}
                <div style={statBoxStyle}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>No Travel</span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: summary.no_travel_miles > 0 ? 'var(--risk-no-travel)' : 'var(--text-secondary)'
                  }} className="mono">
                    {summary.no_travel_miles.toFixed(0)} mi
                  </span>
                </div>

                {/* Severe */}
                <div style={statBoxStyle}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>Severe</span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: summary.severe_miles > 0 ? 'var(--risk-severe)' : 'var(--text-secondary)'
                  }} className="mono">
                    {summary.severe_miles.toFixed(0)} mi
                  </span>
                </div>

                {/* High */}
                <div style={statBoxStyle}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>High</span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: summary.high_miles > 0 ? 'var(--risk-high)' : 'var(--text-secondary)'
                  }} className="mono">
                    {summary.high_miles.toFixed(0)} mi
                  </span>
                </div>

                {/* Avg Risk */}
                <div style={statBoxStyle}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>Avg Risk</span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: summary.avg_risk <= 1.5 ? 'var(--risk-low)' : summary.avg_risk <= 2.5 ? 'var(--risk-moderate)' : 'var(--risk-high)'
                  }} className="mono">
                    {summary.avg_risk.toFixed(2)}/5
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const statBoxStyle: React.CSSProperties = {
  background: 'rgba(0, 0, 0, 0.25)',
  padding: '6px 4px',
  borderRadius: '6px',
  display: 'flex',
  flexDirection: 'column',
  gap: '2px',
};
