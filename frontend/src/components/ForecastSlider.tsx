import React from 'react';
import { Play, Pause, RotateCcw, Clock } from 'lucide-react';

interface ForecastSliderProps {
  currentHour: number;
  onChangeHour: (hour: number) => void;
  departureTimeStr: string;
}

export const ForecastSlider: React.FC<ForecastSliderProps> = ({
  currentHour,
  onChangeHour,
  departureTimeStr,
}) => {
  const [isPlaying, setIsPlaying] = React.useState(false);

  React.useEffect(() => {
    let interval: any;
    if (isPlaying) {
      interval = setInterval(() => {
        onChangeHour((currentHour + 1) % 48);
      }, 700);
    }
    return () => clearInterval(interval);
  }, [isPlaying, currentHour, onChangeHour]);

  const getForecastTimeLabel = () => {
    try {
      const base = new Date(departureTimeStr);
      const target = new Date(base.getTime() + currentHour * 3600 * 1000);
      return target.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return `+${currentHour} hrs`;
    }
  };

  return (
    <div style={{
      background: 'var(--bg-glass)',
      backdropFilter: 'blur(12px)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-lg)',
      padding: '14px 20px',
      boxShadow: 'var(--shadow-lg)',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      color: 'var(--text-primary)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={16} color="var(--accent-blue)" />
          <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.02em' }}>
            Corridor Weather Timeline
          </span>
          <span style={{
            fontSize: '11px',
            background: 'rgba(59, 130, 246, 0.15)',
            color: 'var(--accent-blue)',
            padding: '2px 8px',
            borderRadius: '10px',
            fontWeight: 700
          }} className="mono">
            {currentHour === 0 ? 'Departure Time' : `+${currentHour}h Forecast`}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }} className="mono">
            {getForecastTimeLabel()}
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              type="button"
              onClick={() => setIsPlaying(!isPlaying)}
              style={iconBtnStyle}
              title={isPlaying ? 'Pause' : 'Play Timeline'}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} />}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                onChangeHour(0);
              }}
              style={iconBtnStyle}
              title="Reset to 0h"
            >
              <RotateCcw size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Scrubbing slider */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }} className="mono">0h</span>
        <input
          type="range"
          min="0"
          max="47"
          step="1"
          value={currentHour}
          onChange={(e) => onChangeHour(Number(e.target.value))}
          style={{
            flex: 1,
            cursor: 'pointer',
            accentColor: 'var(--accent-blue)',
            height: '6px',
          }}
        />
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }} className="mono">48h</span>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        fontSize: '11px',
        color: 'var(--text-muted)',
        paddingTop: '4px',
        borderTop: '1px solid rgba(255, 255, 255, 0.05)',
      }}>
        <span>Corridor Risk Heatmap:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--risk-low)' }} /> Low
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--risk-moderate)' }} /> Moderate
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--risk-high)' }} /> High
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--risk-severe)' }} /> Severe
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--risk-no-travel)' }} /> No Travel
          </span>
        </div>
      </div>
    </div>
  );
};

const iconBtnStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.06)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  color: 'var(--text-primary)',
  width: '26px',
  height: '26px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
};
