# Smart Weather-Aware Truck Routing 

> A full-stack decision-support tool that helps truck drivers pick the **safest route** by combining real-time weather forecasts, truck load weight, and travel-time estimation.

---

## 1. What the System Does (High-Level)

1. The driver enters **origin**, **destination**, **departure time**, and **load weight**.
2. The backend fetches **3 alternative routes** from Mapbox Directions API.
3. It walks each route, placing **checkpoints every N miles** and calculating the **exact arrival time** at each one.
4. It batches all checkpoint coordinates into a single **Open-Meteo weather request** and reads the forecast at each checkpoint's arrival hour.
5. It applies **load-specific risk rules** (wind × weight thresholds) to produce a `RiskLevel` at every checkpoint.
6. It **aggregates** mileage by risk category and **lexicographically ranks** all 3 routes — safest first.
7. It also builds a **48-hour corridor heatmap matrix** (grid of lat/lon points, each with 48 hourly risk values) — no extra API calls, reuses checkpoint forecasts.
8. The React frontend receives **one unified JSON payload** and renders:
   - Three colour-coded route polylines on a MapLibre GL map.
   - Interactive checkpoint markers with full weather pop-ups.
   - Route comparison cards with risk breakdowns.
   - A 0–48 h time-slider that animates the heatmap in real time, **entirely client-side** (no additional network calls after the first one).

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript | Type-safe, ultra-fast HMR, ESM native |
| **Map Engine** | MapLibre GL JS | WebGL/GPU rendering; heatmap layers via `setPaintProperty` |
| **Icons** | Lucide React | Lightweight SVG icon set |
| **Backend** | Django 5.1 + Django REST Framework | Clean stateless API; async support via `asyncio` |
| **Async HTTP** | httpx `AsyncClient` | Concurrent external API calls with `asyncio.gather` |
| **Routing API** | Mapbox Directions API | Alternatives, GeoJSON geometry, segment durations |
| **Geocoding API** | Mapbox Geocoding API | City/address autocomplete, debounce-friendly |
| **Weather API** | Open-Meteo | Free, no key needed, multi-location batch, mph/inch native units |
| **Caching** | Django `LocMemCache` (15 min TTL) | Avoids repeated weather calls for the same coordinates |
| **Testing** | pytest + pytest-asyncio + pytest-django | 36+ unit tests across risk engine and services |

---

## 3. Project Structure

```
Smart-weather-truck-routing/
├── PLAN.md                          # Master implementation plan
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env / .env.example          # MAPBOX_ACCESS_TOKEN goes here
│   ├── pytest.ini
│   ├── server/                      # Django project config
│   │   ├── settings.py              # Stateless: no DB, LocMemCache, CORS open
│   │   └── urls.py
│   ├── risk/                        # Pure risk engine (no Django deps)
│   │   ├── thresholds.py            # RiskLevel enum + classify_wind/rain/snow
│   │   ├── classify.py              # evaluate_checkpoint_risk (load rules)
│   │   ├── aggregate.py             # aggregate_route_risk (mileage buckets)
│   │   └── recommend.py             # rank_routes + reason generation
│   ├── routing/                     # Django app
│   │   ├── views.py                 # /api/analyze/ and /api/geocode/
│   │   ├── serializers.py           # DRF request validation
│   │   ├── urls.py
│   │   └── services/
│   │       ├── orchestrator.py      # End-to-end pipeline (8-step)
│   │       ├── routing_provider.py  # Mapbox + Mock routing providers
│   │       ├── checkpoint_sampler.py # Polyline interpolation + ETA
│   │       ├── weather_provider.py  # Open-Meteo batched client
│   │       ├── geocoding.py         # Mapbox geocoding wrapper
│   │       └── geo.py               # Haversine + linear interpolation
│   └── tests/
│       ├── test_risk_engine.py       # 36 boundary/logic tests
│       ├── test_checkpoint_sampler.py
│       ├── test_routing_provider.py
│       ├── test_weather_provider.py
│       └── test_api_integration.py
└── frontend/
    ├── index.html
    ├── vite.config.ts               # Proxy /api → localhost:8000
    ├── package.json
    └── src/
        ├── App.tsx                  # Root state machine + layout
        ├── types.ts                 # All TypeScript interfaces
        ├── services/api.ts          # fetch wrappers for backend
        └── components/
            ├── TripForm.tsx         # Input form + geocode autocomplete
            ├── RouteMap.tsx         # MapLibre map + routes + heatmap
            ├── RouteComparison.tsx  # Sidebar route cards
            └── ForecastSlider.tsx   # 0–48 h scrubbing slider
```

---

## 4. Backend Deep-Dive

### 4.1 Risk Engine (`backend/risk/`)

The risk engine is a **pure Python library** with zero Django dependencies — it can be unit-tested in isolation.

#### `thresholds.py` — Classification cutoffs

Defines `RiskLevel` as an `IntEnum` (1–5) and three classifier functions:

| Hazard | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| **Wind** | < 25 mph | 25–34.9 | 35–44.9 | 45–54.9 | ≥ 55 mph |
| **Rain** | < 0.10 in/hr | 0.10–0.249 | 0.25–0.499 | 0.50–0.999 | ≥ 1.00 in/hr |
| **Snow** | < 0.50 in/hr | 0.50–0.99 | 1.0–1.99 | 2.0–2.99 | ≥ 3.0 in/hr |

#### `classify.py` — Per-checkpoint evaluation

`evaluate_checkpoint_risk(weather, load_weight_lbs)` takes wind + rain + snow values and the truck's load, then:

1. Computes individual risk levels from the three classifiers.
2. Sets `base_risk = max(wind_risk, rain_risk, snow_risk)`.
3. Applies **load escalation rules**:
   - Wind ≥ 55 mph → **No Travel** (any load).
   - Wind 45–54 mph + load > 30,000 lb → **No Travel**.
   - Wind 35–44 mph + load > 40,000 lb → escalate to at least **Severe**.
4. Returns an `EvaluatedRisk` dataclass with `final_risk` and a human-readable `load_adjustment_applied` message.

#### `aggregate.py` — Route-level mileage buckets

`aggregate_route_risk(checkpoints, total_duration_hours)` walks every `CheckpointResult`, reads its `segment_miles`, and accumulates totals into:
- `severe_miles`, `high_miles`, `moderate_miles`, `low_miles`, `no_travel_miles`
- `avg_risk` — a **distance-weighted** average risk score (1.0–5.0)

#### `recommend.py` — Lexicographic ranking

`rank_routes(routes)` sorts the 3 routes by the following priority (strict, in order):

1. Routes with any `no_travel_count > 0` are **demoted** to the bottom.
2. Fewest `severe_miles`.
3. Fewest `high_miles`.
4. Lowest `avg_risk`.
5. Shortest `duration_hours` (tie-breaker).

It also generates a **human-readable reason** for each route's rank (e.g., *"Recommended: Avoids all severe weather (0 mi severe) with only 12.3 mi high-risk."*).

---

### 4.2 Routing Services (`backend/routing/services/`)

#### `geo.py`
Two pure math utilities:
- `haversine_distance_miles(lat1, lon1, lat2, lon2)` — great-circle distance.
- `interpolate_coordinates(lat1, lon1, lat2, lon2, t)` — linear interpolation between two points.

#### `routing_provider.py` — `MapboxRoutingProvider`

- Calls Mapbox Directions API with `alternatives=true`.
- If Mapbox returns < 3 routes, it automatically fires **perpendicular-offset waypoint requests** (in parallel with `asyncio.gather`) to generate realistic alternative corridors.
- Final fallback: `MockRoutingProvider` generates parabolic curved polylines (curvature ±0.12) — used in offline/test mode or when no Mapbox token is configured.
- Returns a list of `RouteOption` dataclasses: `route_id`, `name`, `distance_miles`, `duration_seconds`, `geometry` (list of lat/lon tuples).

#### `checkpoint_sampler.py`

`sample_route_checkpoints(coordinates, total_duration_seconds, departure_time, step_miles)`:

1. Computes cumulative distances between every polyline vertex using Haversine.
2. Places sample markers every `step_miles` (10 / 25 / 50, user-selectable).
3. For each marker: **linearly interpolates** exact lat/lon from the surrounding segment, and computes **ETA** by scaling total trip duration by the distance fraction.
4. Attributes **segment miles** to each checkpoint via midpoint partitioning (so risk weighting is fair across the route).

#### `weather_provider.py` — `OpenMeteoWeatherService`

- `fetch_weather_for_locations(locations)` — sends a **single batched GET** to Open-Meteo with comma-separated lat/lon lists. Returns hourly arrays for `wind_speed_10m`, `wind_gusts_10m`, `precipitation`, `snowfall`, `temperature_2m`.
- `extract_weather_at_eta(forecast_data, eta)` — rounds the ETA to the nearest hour and picks the matching index from the hourly arrays.
- `extract_48h_risk_series(forecast_data, start_time)` — extracts 48 consecutive hourly entries starting from `start_time`. Used for the corridor heatmap matrix.
- The service separates rain from snow: `rain_rate = max(0, precipitation - snow * 0.1)` (10:1 snow/water ratio).

#### `orchestrator.py` — `TripAnalysisOrchestrator` (the brain)

This is the 8-step end-to-end pipeline:

```
Step 1  → get_3_routes()
Step 2  → sample_route_checkpoints() for each route
Step 3  → collect all unique checkpoint coords (deduplicated to ~0.15° cells)
Step 4  → batch-fetch Open-Meteo for all unique coords
           (max 15 coords/chunk, max 2 concurrent requests via asyncio.Semaphore)
           (3 retry attempts per chunk on failure)
Step 5  → evaluate_checkpoint_risk() at each checkpoint using ETA weather
Step 6  → aggregate_route_risk() → RouteRiskSummary per route
Step 7  → rank_routes() → ranked list with recommendation reasons
Step 8  → _build_corridor_heatmap_matrix() (ZERO extra API calls — reuses Step 4 data)
```

**Key design decision — Zero-Chatter Slider:** The heatmap corridor matrix (all unique checkpoint coords × 48 hourly risk values) is built entirely from the forecasts already fetched in Step 4. The React frontend can scrub through 48 hours of weather without ever hitting the backend again.

---

### 4.3 API Endpoints (`backend/routing/views.py`)

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/health/` | Health check |
| `GET` | `/api/geocode/?q=Denver` | Autocomplete address → lat/lon |
| `POST` | `/api/analyze/` | Full trip analysis pipeline |

**`POST /api/analyze/` request body:**
```json
{
  "origin": [39.7392, -104.9903],
  "destination": [41.8781, -87.6298],
  "departure_time": "2026-10-17T14:00:00Z",
  "load_weight_lbs": 35000,
  "sampling_interval_miles": 25
}
```

**Response shape:**
```json
{
  "origin": {...},
  "destination": {...},
  "departure_time": "...",
  "load_weight_lbs": 35000,
  "routes": [
    {
      "id": "mapbox_route_1",
      "name": "Via I-80",
      "rank": 1,
      "is_recommended": true,
      "recommendation_reason": "Safest option: 0 severe and 0 high-risk miles...",
      "distance_miles": 912.4,
      "duration_hours": 13.8,
      "summary": {
        "severe_miles": 0, "high_miles": 12.3, "avg_risk": 1.42, ...
      },
      "geometry": [{"latitude": ..., "longitude": ...}, ...],
      "checkpoints": [
        {
          "index": 0, "latitude": ..., "longitude": ...,
          "distance_miles": 0, "eta": "...", "segment_miles": 12.5,
          "weather": {"wind_mph": 18.3, "rain_in_per_hr": 0.0, ...},
          "risk": {"level": 1, "label": "Low", "load_adjustment": null}
        }, ...
      ]
    }, ...
  ],
  "corridor_heatmap": [
    {"latitude": 39.74, "longitude": -104.99, "risks": [1,1,2,2,3,...48 values]},
    ...
  ]
}
```

---

### 4.4 Django Configuration

- **No database** — `DATABASES = {}`. The entire pipeline is stateless; all data lives in request/response cycles.
- **LocMemCache** (15-minute TTL) — avoids re-fetching weather for the same coordinates within a session.
- **CORS fully open** — `CORS_ALLOW_ALL_ORIGINS = True` for local dev.
- **Windows fix** — `asyncio.WindowsSelectorEventLoopPolicy()` is set in `views.py` so `asyncio.run()` works correctly on Windows with `httpx`.

---

## 5. Frontend Deep-Dive

### 5.1 App State Machine (`App.tsx`)

The root component manages a simple state machine with 4 states:

| State | What's shown |
|---|---|
| `idle` | TripForm + map placeholder |
| `loading` | TripForm disabled + spinner on both sides |
| `results` | TripForm + RouteComparison + ForecastSlider + live map |
| `error` | TripForm + error panel |

Key state: `forecastHour` (0–47) is the single source of truth for the heatmap layer — it flows down to both `ForecastSlider` (the control) and `RouteMap` (the consumer).

### 5.2 Components

#### `TripForm.tsx`
- Origin and destination text inputs with **Mapbox geocode autocomplete** (300 ms debounce).
- Dropdown for departure date/time.
- Load weight input (lbs).
- Sampling interval selector: 10 / 25 / 50 miles.
- On submit: calls `analyzeTrip()` and passes results up via `onAnalyze`.

#### `RouteMap.tsx`
- Initialises a **MapLibre GL** map instance (dark vector tile style).
- Renders 3 route polylines as GeoJSON `LineString` layers, colour-coded by segment risk.
- The **recommended / selected** route is drawn thicker and on top.
- Checkpoint markers are rendered as coloured circles; clicking opens a pop-up showing ETA, wind, rain, snow, temperature, and risk label.
- A **GPU heatmap layer** is bound to the corridor matrix. When `forecastHour` prop changes, the component calls `map.setPaintProperty(...)` with the pre-computed risk weights for that hour — **no re-render, no API call**.

#### `RouteComparison.tsx`
- Renders one card per route, sorted by rank.
- Each card shows: route name, rank badge, distance, duration, and a 4-column breakdown (No Travel mi / Severe mi / High mi / Avg Risk).
- The recommended route gets a green "RECOMMENDED" pill badge and a green border.
- Clicking a card updates `selectedRoute` and highlights the corresponding polyline on the map.

#### `ForecastSlider.tsx`
- A styled `<input type="range">` (0–47).
- **Play/Pause** button auto-advances the hour every 700 ms using `setInterval`.
- **Reset** button returns to hour 0 and pauses.
- Displays the actual forecast timestamp (departure time + N hours) in a human-readable format.
- A colour legend at the bottom explains the heatmap risk colours.

### 5.3 TypeScript Types (`types.ts`)

All interfaces that cross the API boundary are defined here:
- `WeatherCondition`, `CheckpointRisk`, `Checkpoint`
- `RouteSummary`, `RouteOption`, `Coordinate`
- `HeatmapGridPoint`, `TripAnalysisResponse`
- `GeocodeResult`

### 5.4 API Service (`services/api.ts`)
Thin fetch wrappers:
- `analyzeTrip(params)` → `POST /api/analyze/` → `TripAnalysisResponse`
- `geocodeLocation(query)` → `GET /api/geocode/?q=...` → `GeocodeResult[]`

Vite proxies `/api/*` to `http://localhost:8000` during development (configured in `vite.config.ts`).

---

## 6. The 48-Hour Corridor Heatmap — How It Works

This is the most novel performance feature of the system.

**During the single `/api/analyze/` call:**
1. All checkpoint coordinates (deduplicated into ~0.15° grid cells) are fetched from Open-Meteo with a 72-hour forecast window.
2. For each coordinate, `extract_48h_risk_series()` reads the 48 hourly forecast slots starting from departure time and evaluates `evaluate_checkpoint_risk()` for each hour.
3. The result is stored as `{"latitude": X, "longitude": Y, "risks": [1,1,2,3,...]}` — 48 integers per point.
4. This entire matrix is included in the JSON response under `corridor_heatmap`.

**On the client:**
- MapLibre receives the matrix and sets up a heatmap layer with the risk values for `hour = 0` as initial weights.
- When the user drags the slider to hour `h`, the component extracts `point.risks[h]` for every grid point and calls `map.setPaintProperty('heatmap-weight', ...)`.
- The GPU re-renders the heatmap in milliseconds — completely offline from the backend.

---

## 7. Running the Project

### Backend
```powershell
cd backend
.\venv\Scripts\python.exe manage.py runserver
```
Runs on `http://localhost:8000`. Set `MAPBOX_ACCESS_TOKEN` in `backend/.env`.

### Frontend
```powershell
cd frontend
npm run dev
```
Runs on `http://localhost:5173`. All `/api/*` requests are proxied to the backend.

### Tests
```powershell
cd backend
.\venv\Scripts\pytest tests/ -v
```

---

## 8. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Zero-database backend** | The pipeline is fully stateless; no persistence needed. Avoids ORM overhead entirely. |
| **Single POST, all data** | One round-trip delivers geometry, checkpoints, risk scores, and 48 h heatmap. The slider animates offline. |
| **Semaphore on weather fetches** | Open-Meteo rate-limits aggressive parallel requests. Max 2 concurrent chunks prevents 429 errors on long routes. |
| **Coordinate deduplication** | Routes share corridor coordinates. Rounding to ~0.15° cells collapses duplicates before fetching, cutting API calls by 40–60 %. |
| **MockRoutingProvider** | Allows full offline testing and development without a Mapbox token. Generates realistic parabolic polylines. |
| **Midpoint segment attribution** | Each checkpoint "owns" the miles halfway to its neighbours, making the mileage totals exactly equal to the route's total distance. |
| **Load weight escalation** | Real-world regulation: heavy loads are more vulnerable to wind. High-cube trailers (> 40k lb) are treated more conservatively at 35–44 mph winds. |

---

## 9. Implementation Progress

| Phase | Status |
|---|---|
| Phase 1: Risk Engine + Django setup | ✅ Complete |
| Phase 2: Routing + Weather pipeline | ✅ Complete |
| Phase 3: Frontend + Map visualisation | ✅ Complete |
| Phase 4: 48 h Heatmap + Slider | ✅ Complete |
| Phase 5: Production packaging + README | 🔲 Pending |
