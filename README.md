# WeatherRoute: Smart Weather-Aware Truck Routing

A full-stack logistics decision-support platform designed to evaluate and recommend the safest commercial trucking routes. The system integrates multi-alternative routing with high-resolution weather forecasts, dynamic vehicle load physics, and travel-time projections.

---

## Overview

Long-haul freight routing requires continuous awareness of severe weather hazards, particularly crosswinds, freezing rain, and high snow accumulations. WeatherRoute analyses up to three alternative corridors between any origin and destination, evaluates risk factors along every road segment at its projected arrival time, and produces an aggregated risk classification to recommend the safest option.

### Core Capabilities

- **Multi-Route Analysis**: Generates primary and alternative transit corridors via Mapbox Directions API with automated orthogonal corridor synthesis.
- **Dynamic Checkpoint Sampling**: Samples routing polylines at configurable spatial intervals (10, 25, or 50 miles) and calculates accurate arrival timestamps based on segment-level transit speeds.
- **Batched Atmospheric Forecasting**: Queries Open-Meteo multi-location endpoints in grouped chunks, extracting hourly wind speed, wind gust, precipitation, and snowfall projections.
- **Load-Sensitive Risk Engine**: Evaluates weather severity adjusted against gross vehicle weight ratings (GVWR), enforcing strict safety thresholds for rollover-prone heavy configurations.
- **Lexicographic Route Ranking**: Demotes routes passing through critical non-traversable conditions while prioritizing paths with minimal high and severe risk exposure.
- **Client-Side Temporal Heatmap**: Pre-computes a 48-hour corridor risk grid delivered in a single payload, allowing real-time timeline inspection without redundant network roundtrips.

---

## System Architecture

```
WeatherRoute/
├── backend/                         # Django REST Framework core
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── pytest.ini
│   ├── server/                      # Project configuration (stateless, CORS-enabled)
│   ├── risk/                        # Standalone risk assessment engine
│   │   ├── thresholds.py            # RiskLevel definitions & hazard cutoffs
│   │   ├── classify.py              # Load-adjusted checkpoint evaluation
│   │   ├── aggregate.py             # Route-level mileage risk accumulation
│   │   └── recommend.py             # Lexicographic sorting & rationale generator
│   ├── routing/                     # Routing & weather orchestration app
│   │   ├── views.py                 # API controllers (/api/analyze, /api/geocode)
│   │   ├── serializers.py           # Schema definition & input validation
│   │   └── services/
│   │       ├── orchestrator.py      # Multi-stage execution pipeline
│   │       ├── routing_provider.py  # Mapbox & synthetic fallback route providers
│   │       ├── checkpoint_sampler.py# Trajectory interpolation & ETA calculation
│   │       ├── weather_provider.py  # Batched Open-Meteo async client
│   │       ├── geocoding.py         # Address query resolution
│   │       └── geo.py               # Haversine distance & spatial math
│   └── tests/                       # Unit and integration test suites
└── frontend/                        # React + TypeScript single-page application
    ├── index.html
    ├── vite.config.ts               # Development proxy configuration
    ├── package.json
    └── src/
        ├── App.tsx                  # Root controller & view state machine
        ├── types.ts                 # Domain and API type definitions
        ├── services/api.ts          # Backend API client interfaces
        └── components/
            ├── TripForm.tsx         # Route parameters & geocoding inputs
            ├── RouteMap.tsx         # MapLibre GL visualization & heatmap engine
            ├── RouteComparison.tsx  # Comparative route ranking cards
            └── ForecastSlider.tsx   # Interactive 48-hour timeline scrubber
```

---

## Technical Specifications

| Component | Technology | Rationale |
|---|---|---|
| Frontend Framework | React 19, TypeScript, Vite | Fast client execution, strict type validation, and rapid hot-module replacement |
| Geospatial Rendering | MapLibre GL JS | Hardware-accelerated WebGL vector map rendering and dynamic GPU heatmaps |
| User Interface Styling | Modern CSS & Lucide Icons | Responsive layout design, streamlined iconography, zero external CSS runtime overhead |
| Application Server | Django 5.1, Django REST Framework | Mature API structure with native asynchronous execution support |
| HTTP Transport | httpx AsyncClient | Non-blocking concurrent requests orchestrated via asyncio primitives |
| Routing Services | Mapbox Directions API | Accurate real-world highway geometries, durations, and alternative corridors |
| Weather Forecasts | Open-Meteo API | High-resolution global atmospheric forecasts with multi-coordinate batch queries |
| Caching Layer | Django LocMemCache | In-memory session cache to avoid repeated queries for duplicate spatial coordinates |
| Test Suite | pytest, pytest-asyncio, pytest-django | Deterministic unit coverage across risk algorithms and async network clients |

---

## Risk Assessment Methodology

### 1. Hazard Classification Thresholds

Each checkpoint evaluates three independent weather variables into an integer risk rank (Level 1 to 5):

| Risk Level | Designation | Sustained Wind | Hourly Rainfall | Hourly Snowfall |
|---|---|---|---|---|
| Level 1 | Low | Below 25 mph | Below 0.10 in/hr | Below 0.50 in/hr |
| Level 2 | Moderate | 25.0 - 34.9 mph | 0.10 - 0.249 in/hr | 0.50 - 0.99 in/hr |
| Level 3 | High | 35.0 - 44.9 mph | 0.25 - 0.499 in/hr | 1.00 - 1.99 in/hr |
| Level 4 | Severe | 45.0 - 54.9 mph | 0.50 - 0.999 in/hr | 2.00 - 2.99 in/hr |
| Level 5 | No Travel | 55.0 mph or higher | 1.00 in/hr or higher | 3.00 in/hr or higher |

### 2. Vehicle Weight Escalation Rules

Because elevated profile trailers are vulnerable to dynamic wind shear at higher gross weights, base weather risk is modified using operational escalation rules:

- **Universal No Travel**: Wind speeds reaching 55.0 mph trigger a mandatory No Travel classification regardless of configuration.
- **Heavy Load Wind Exposure**: Wind speeds between 45.0 and 54.9 mph combined with load weights above 30,000 lbs trigger a No Travel classification.
- **Moderate Gale Threshold**: Wind speeds between 35.0 and 44.9 mph combined with load weights exceeding 40,000 lbs escalate the risk level to Severe.

### 3. Lexicographic Route Ranking

Routes are sorted deterministically using prioritized safety criteria:

1. Demote any route with one or more checkpoints classified as No Travel.
2. Minimize cumulative mileage traversing Severe conditions.
3. Minimize cumulative mileage traversing High-risk conditions.
4. Minimize overall distance-weighted average risk score.
5. Minimize total travel duration (applied as a final tie-breaker).

---

## Pipeline Execution Flow

```
1. Route Retrieval    --> Query 3 independent corridors via Mapbox Directions API
2. Spatial Sampling   --> Divide each trajectory into discrete checkpoints with ETAs
3. Deduplication      --> Cluster nearby coordinates into ~0.15 degree spatial buckets
4. Batch Weather      --> Fetch Open-Meteo hourly projections in concurrent chunks
5. Risk Evaluation    --> Match forecast hour to ETA and execute weight-adjusted rules
6. Route Aggregation  --> Compute distance-weighted risk and categorize mileage bands
7. Recommendation     --> Apply lexicographic ranking and construct explanation rationale
8. Corridor Matrix    --> Build 48-hour temporal risk grid for client-side timeline scrubbing
```

---

## API Reference

### Health Check

```http
GET /api/health/
```

Returns operational status confirmation of the service.

---

### Geocoding Autocomplete

```http
GET /api/geocode/?q={search_term}
```

Resolves partial strings to coordinates with city, state, and geographic metadata.

---

### Trip Analysis

```http
POST /api/analyze/
Content-Type: application/json
```

#### Request Payload

```json
{
  "origin": [39.7392, -104.9903],
  "destination": [41.8781, -87.6298],
  "departure_time": "2026-10-17T14:00:00Z",
  "load_weight_lbs": 35000,
  "sampling_interval_miles": 25
}
```

#### Response Structure

```json
{
  "origin": { "latitude": 39.7392, "longitude": -104.9903 },
  "destination": { "latitude": 41.8781, "longitude": -87.6298 },
  "departure_time": "2026-10-17T14:00:00Z",
  "load_weight_lbs": 35000,
  "routes": [
    {
      "id": "mapbox_route_1",
      "name": "Via I-80 E",
      "rank": 1,
      "is_recommended": true,
      "recommendation_reason": "Safest route: 0.0 severe miles and lowest weighted risk index.",
      "distance_miles": 1005.2,
      "duration_hours": 15.3,
      "summary": {
        "no_travel_miles": 0.0,
        "severe_miles": 0.0,
        "high_miles": 18.5,
        "moderate_miles": 142.0,
        "low_miles": 844.7,
        "avg_risk": 1.28
      },
      "geometry": [
        { "latitude": 39.7392, "longitude": -104.9903 },
        { "latitude": 41.8781, "longitude": -87.6298 }
      ],
      "checkpoints": [
        {
          "index": 0,
          "latitude": 39.7392,
          "longitude": -104.9903,
          "distance_miles": 0.0,
          "eta": "2026-10-17T14:00:00Z",
          "segment_miles": 12.5,
          "weather": {
            "wind_mph": 14.2,
            "wind_gusts_mph": 19.5,
            "rain_in_per_hr": 0.0,
            "snow_in_per_hr": 0.0,
            "temperature_f": 52.0
          },
          "risk": {
            "level": 1,
            "label": "Low",
            "load_adjustment": null
          }
        }
      ]
    }
  ],
  "corridor_heatmap": [
    {
      "latitude": 39.74,
      "longitude": -104.99,
      "risks": [1, 1, 1, 2, 2, 3]
    }
  ]
}
```

---

## Local Setup and Development

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Mapbox access token (required for production routing and geocoding services)

---

### Backend Configuration

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Initialize a Python virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the environment:
   - Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - macOS / Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables by copying the example template:
   ```bash
   cp .env.example .env
   ```
   Set `MAPBOX_ACCESS_TOKEN` in `backend/.env`.

6. Start the development server:
   ```bash
   python manage.py runserver
   ```
   The backend service will listen at `http://localhost:8000`.

---

### Frontend Configuration

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   The user interface will be accessible at `http://localhost:5173`. API calls to `/api/*` are automatically forwarded to the backend service.

---

### Running the Test Suite

Execute the unit and integration tests from the backend directory:

```bash
cd backend
pytest tests/ -v
```

---

## Engineering Design Decisions

- **Stateless Architecture**: The backend requires no relational database (`DATABASES = {}`). All operations are computed in-flight, eliminating persistence bottlenecks and migration overhead.
- **Single-Roundtrip Data Delivery**: Complete geometries, checkpoint metrics, and 48-hour temporal matrices are packaged into a single JSON response, enabling instantaneous offline animation on the client.
- **Controlled Concurrency**: Weather requests are grouped into chunks of at most 15 coordinates and throttled via an asynchronous semaphore (maximum 2 concurrent connections) to remain within provider rate limits.
- **Spatial Deduplication**: Overlapping segments among alternative corridors are merged using a ~0.15 degree coordinate grid, cutting downstream weather request volumes by up to 60%.
- **Resilient Fallback Mode**: In the absence of external Mapbox tokens or during network degradation, the system transparently engages a synthetic route provider to ensure uninterrupted testing and local evaluation.
- **Equitable Distance Attribution**: Checkpoints partition distance along polyline segments using midpoint attribution, ensuring aggregate risk mileage strictly reconciles with total route length.

---

## License

This project is licensed under the MIT License.
