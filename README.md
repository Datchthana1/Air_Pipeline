# Air Quality Pipeline

A personal data engineering project built to collect hourly weather and air quality data for Bangkok, with the goal of training ML models (Random Forest, Decision Tree, Gradient Boosting) to predict next-day PM2.5.

## Tools

- Apache Airflow (Dockerized, Standalone)
- Pendulum
- Supabase (PostgreSQL Cloud)
- Pandas
- Dotenv

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          External APIs                               │
│                                                                      │
│  ┌───────────────────────────┐    ┌─────────────────────────────┐   │
│  │    OpenWeatherMap API     │    │     AIR4Thai API (PCD)      │   │
│  │  api.openweathermap.org   │    │   air4thai.pcd.go.th        │   │
│  │                           │    │   Station ID: o10           │   │
│  │  - Temperature            │    │                             │   │
│  │  - Humidity               │    │   - PM2.5                   │   │
│  │  - Wind Speed / Direction │    │   - AQI                     │   │
│  │  - Pressure               │    │   - Area / Station Name     │   │
│  │  - Visibility             │    │                             │   │
│  │  - Cloud Description      │    └──────────────┬──────────────┘   │
│  │  - Sea Level              │                   │                  │
│  │  - Temp Min / Max         │                   │                  │
│  └──────────────┬────────────┘                   │                  │
│                 │                                │                  │
└─────────────────┼────────────────────────────────┼──────────────────┘
                  │  HTTP GET                      │  HTTP GET
                  └───────────────┬────────────────┘
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Docker Container (Airflow Standalone)             │
│                                                                      │
│  Volumes:  ./dags        → /opt/airflow/dags                        │
│            ./logs        → /opt/airflow/logs                        │
│            ./assets/.env → /opt/airflow/assets/.env                 │
│  Port: 8080                                                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  DAG: air_pipeline_hourly  (cron: 0 * * * * | Asia/Bangkok)   │ │
│  │                                                                │ │
│  │  ┌──────────────────────┐  XCom  ┌───────────────────────┐   │ │
│  │  │  Task 1              │ ──────▶│  Task 2               │   │ │
│  │  │  fetch_weather_data  │        │  insert_weather_data  │   │ │
│  │  │                      │        │                       │   │ │
│  │  │  combine_data()      │        │  insert_data()        │   │ │
│  │  │  - Call OW API       │        │  - Connect Supabase   │   │ │
│  │  │  - Call AIR4Thai     │        │  - INSERT 1 row →     │   │ │
│  │  │  - Merge fields      │        │    weather_data       │   │ │
│  │  │  retries: 3 (2 min)  │        │                       │   │ │
│  │  └──────────────────────┘        └───────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  DAG: air_pipeline_daily   (cron: 0 0 * * * | Asia/Bangkok)   │ │
│  │                                                                │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │  Task 1                                                 │  │ │
│  │  │  process_data_daily                                     │  │ │
│  │  │                                                         │  │ │
│  │  │  process_daily_data()   → Query yesterday's rows from   │  │ │
│  │  │                            weather_data (~24 rows)      │  │ │
│  │  │                         → Aggregate via pandas resample │  │ │
│  │  │                           (mean / min / max / mode)     │  │ │
│  │  │                         → Calculate AQI from PM2.5      │  │ │
│  │  │                           using Thailand breakpoints    │  │ │
│  │  │  insert_daily_data()    → UPSERT 1 row →                │  │ │
│  │  │                            weather_data_daily           │  │ │
│  │  │  retries: 3 (2 min)                                     │  │ │
│  │  │  supports: manual trigger with target_date param        │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  Supabase Client (REST / HTTPS)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL Cloud)                       │
│                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Table: weather_data        │  │  Table: weather_data_daily   │  │
│  │  (raw · 1 row/hour)         │  │  (aggregated · 1 row/day)    │  │
│  │                             │  │                              │  │
│  │  - datetime                 │  │  - datetime                  │  │
│  │  - temperature              │  │  - temperature (mean)        │  │
│  │  - humidity                 │  │  - humidity (mean)           │  │
│  │  - wind_speed               │  │  - wind_speed (mean)         │  │
│  │  - wind_direction           │  │  - wind_direction (mode)     │  │
│  │  - pressure                 │  │  - pressure (mean)           │  │
│  │  - visibility               │  │  - visibility (mean)         │  │
│  │  - cloud                    │  │  - cloud (mode)              │  │
│  │  - sea_level                │  │  - sea_level (mean)          │  │
│  │  - temp_min                 │  │  - temp_min (min)            │  │
│  │  - temp_max                 │  │  - temp_max (max)            │  │
│  │  - pm25                     │  │  - pm25 (mean)               │  │
│  │  - AQI                      │  │  - AQI (calculated)          │  │
│  │  - area                     │  │  - area (mode)               │  │
│  │  - station_name             │  │  - station_name (mode)       │  │
│  │  - created_at               │  │  - day_of_week               │  │
│  └─────────────────────────────┘  │  - created_at                │  │
│                                   └──────────────────────────────┘  │
│                    ▲                            ▲                    │
│                    │  write (hourly)            │  write (midnight)  │
│         air_pipeline_hourly          air_pipeline_daily              │
│                                      reads FROM weather_data         │
└──────────────────────────────────────────────────────────────────────┘
```

## AQI Calculation

AQI is derived from PM2.5 using Thailand's breakpoints (reference: [aqihub.info](https://aqihub.info/indices/thailand)):

| PM2.5 (µg/m³) | AQI Range |
| ------------- | --------- |
| 0.0 – 15.0    | 0 – 25    |
| 15.1 – 25.0   | 26 – 50   |
| 25.1 – 37.5   | 51 – 100  |
| 37.6 – 75.0   | 101 – 200 |
| 75.1 – 150.0  | 201 – 300 |

## Getting Started

1. Clone the repository
2. Copy `assets/.env.example` to `assets/.env` and fill in your credentials:

```env
OPENWEATHER_API_KEY=
LATITUDE=
LONGITUDE=
AIR4THAI_STATIONID=
SUPABASE_URL=
SUPABASE_KEY=
```

3. Run with Docker:

```bash
docker compose up
```

4. Open Airflow UI at `http://localhost:8080`

## Manual Trigger

The daily DAG supports manual backfill via the `target_date` param (format: `YYYY-MM-DD`).
Trigger from the Airflow UI or CLI:

```bash
airflow dags trigger air_pipeline_daily --conf '{"target_date": "2026-03-14"}'
```

## AI Prediction

After collecting sufficient data (~3 months), ML models will be trained to predict next-day PM2.5.
Planned models: Random Forest, Decision Tree, Gradient Boosting.
Results and visualizations will be published in this repository.
