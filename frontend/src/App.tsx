import { useState, useCallback } from "react";
import { TripForm } from "./components/TripForm";
import { RouteComparison } from "./components/RouteComparison";
import { RouteMap } from "./components/RouteMap";
import { ForecastSlider } from "./components/ForecastSlider";
import { analyzeTrip } from "./services/api";
import type { TripAnalysisResponse, RouteOption } from "./types";
import "./App.css";

type AppState = "idle" | "loading" | "results" | "error";

function App() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<TripAnalysisResponse | null>(
    null,
  );
  const [selectedRoute, setSelectedRoute] = useState<RouteOption | null>(null);
  const [forecastHour, setForecastHour] = useState(0);
  const [tripLabels, setTripLabels] = useState({ origin: "", destination: "" });

  const handleAnalyze = useCallback(
    async (params: {
      origin: [number, number];
      destination: [number, number];
      departure_time: string;
      load_weight_lbs: number;
      sampling_interval_miles: number;
      originLabel: string;
      destLabel: string;
    }) => {
      setAppState("loading");
      setErrorMsg(null);
      setAnalysisData(null);
      setSelectedRoute(null);
      setForecastHour(0);
      setTripLabels({
        origin: params.originLabel,
        destination: params.destLabel,
      });

      try {
        const data = await analyzeTrip({
          origin: params.origin,
          destination: params.destination,
          departure_time: params.departure_time,
          load_weight_lbs: params.load_weight_lbs,
          sampling_interval_miles: params.sampling_interval_miles,
        });
        setAnalysisData(data);
        const recommended =
          data.routes.find((r) => r.is_recommended) ?? data.routes[0] ?? null;
        setSelectedRoute(recommended);
        setAppState("results");
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Unknown error occurred";
        setErrorMsg(msg);
        setAppState("error");
      }
    },
    [],
  );

  const handleSelectRoute = useCallback(
    (routeId: string) => {
      if (!analysisData) return;
      const r = analysisData.routes.find((x) => x.id === routeId) ?? null;
      setSelectedRoute(r);
    },
    [analysisData],
  );

  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-inner">
          <div className="logo-group">
            <span className="logo-icon"></span>
            <div>
              <h1 className="logo-title">WeatherRoute</h1>
              <p className="logo-sub">Smart Weather-Aware Truck Routing</p>
            </div>
          </div>
          {appState === "results" && analysisData && (
            <div className="header-trip-info">
              <span className="trip-badge">
                📍 {tripLabels.origin} → {tripLabels.destination}
              </span>
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <TripForm
            onAnalyze={handleAnalyze}
            isLoading={appState === "loading"}
          />

          {appState === "loading" && (
            <div className="loading-panel">
              <div className="spinner" />
              <p className="loading-text">Analyzing routes &amp; weather…</p>
              <p className="loading-sub">
                Fetching 3 route alternatives and weather forecasts for each
                checkpoint
              </p>
            </div>
          )}

          {appState === "error" && errorMsg && (
            <div className="error-panel">
              <span className="error-icon">⚠️</span>
              <p className="error-title">Analysis Failed</p>
              <p className="error-msg">{errorMsg}</p>
            </div>
          )}

          {appState === "results" && analysisData && selectedRoute && (
            <>
              <RouteComparison
                routes={analysisData.routes}
                selectedRouteId={selectedRoute.id}
                onSelectRoute={handleSelectRoute}
              />
              <ForecastSlider
                currentHour={forecastHour}
                onChangeHour={setForecastHour}
                departureTimeStr={analysisData.departure_time}
              />
            </>
          )}
        </aside>

        {/* ── Map ── */}
        <section className="map-section">
          {appState === "idle" && (
            <div className="map-placeholder">
              <div className="placeholder-content">
                <span className="placeholder-icon">🗺️</span>
                <h2>Plan Your Route</h2>
                <p>
                  Enter origin, destination, departure time and load weight to
                  generate weather-safe route options.
                </p>
              </div>
            </div>
          )}

          {appState === "loading" && (
            <div className="map-placeholder">
              <div className="placeholder-content">
                <div className="spinner large" />
                <h2>Calculating Routes…</h2>
                <p>
                  Fetching alternatives and checking weather at each checkpoint
                </p>
              </div>
            </div>
          )}

          {appState === "error" && (
            <div className="map-placeholder error-bg">
              <div className="placeholder-content">
                <span className="placeholder-icon">❌</span>
                <h2>Could not complete analysis</h2>
                <p>{errorMsg}</p>
              </div>
            </div>
          )}

          {appState === "results" && analysisData && selectedRoute && (
            <RouteMap
              routes={analysisData.routes}
              selectedRouteId={selectedRoute.id}
              onSelectRoute={handleSelectRoute}
              corridorHeatmap={analysisData.corridor_heatmap}
              forecastHour={forecastHour}
            />
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
