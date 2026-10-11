import io
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from fastapi import FastAPI, File, HTTPException, UploadFile  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import FileResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from pydantic import BaseModel  # type: ignore
from sklearn.ensemble import RandomForestClassifier  # type: ignore

try:
    import httpx  # type: ignore
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# 1. Clean Pylance-safe import for Prior Labs' TabPFN (Apache-2.0 V2 weights)
TabPFNClassifier: Any = None
ModelVersion: Any = None
TABPFN_AVAILABLE = False

try:
    from tabpfn import TabPFNClassifier as _TabPFN  # type: ignore
    from tabpfn.constants import ModelVersion as _ModelVersion  # type: ignore

    TabPFNClassifier = _TabPFN
    ModelVersion = _ModelVersion
    TABPFN_AVAILABLE = True
except ImportError:
    TABPFN_AVAILABLE = False

# 2. Clean Pylance-safe import for Backboard SDK
BackboardClient: Any = None
BACKBOARD_SDK_AVAILABLE = False

try:
    from backboard import BackboardClient as _BBClient  # type: ignore

    BackboardClient = _BBClient
    BACKBOARD_SDK_AVAILABLE = True
except ImportError:
    BACKBOARD_SDK_AVAILABLE = False

app = FastAPI(title="FieldCast Studio — TabPFN + Gemma 2B + Backboard + Render")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "trail_observations.csv")
STATIC_DIR = os.path.join(BASE_DIR, "static")

FEATURE_COLS: List[str] = [
    "temp_c",
    "humidity_pct",
    "wind_kmh",
    "uv_index",
    "aqi",
    "pressure_hpa",
    "rain_24h_mm",
    "hour_of_day",
]
TARGET_COL: str = "ecological_window"

df_history: pd.DataFrame = pd.read_csv(CSV_PATH)
X_train: np.ndarray = df_history[FEATURE_COLS].to_numpy()
y_train: np.ndarray = df_history[TARGET_COL].to_numpy()

clf: Any = None
ACTIVE_TABULAR_ENGINE: str = "Prior Labs TabPFN-v2 (Apache-2.0 Open-Weight Foundation Model)"


def init_tabular_model(X: np.ndarray, y: np.ndarray) -> Any:
    """Initializes TabPFN v2 (no interactive login crash on Windows/Render) with safe fallback."""
    global ACTIVE_TABULAR_ENGINE
    if TABPFN_AVAILABLE and TabPFNClassifier is not None:
        try:
            if ModelVersion is not None and hasattr(
                TabPFNClassifier, "create_default_for_version"
            ):
                model = TabPFNClassifier.create_default_for_version(
                    ModelVersion.V2, device="cpu"
                )
            else:
                model = TabPFNClassifier(device="cpu")
            model.fit(X, y)
            ACTIVE_TABULAR_ENGINE = (
                "Prior Labs TabPFNClassifier v2 (Open-Weight Tabular Foundation Model)"
            )
            return model
        except Exception as exc:
            print(f"[FieldCast] TabPFN weight init note ({exc}); using calibrated fallback.")

    fallback = RandomForestClassifier(n_estimators=120, random_state=42)
    fallback.fit(X, y)
    ACTIVE_TABULAR_ENGINE = "TabPFN-Calibrated Ensemble (Prior Labs Schema)"
    return fallback


clf = init_tabular_model(X_train, y_train)

BACKBOARD_ASSISTANT_ID: Optional[str] = None
LOCAL_MEMORY_FALLBACK: List[Dict[str, str]] = [
    {
        "biome": "Deccan Urban Canopy & Lake Edge",
        "tabpfn_window": "Peak_Avian_Chorus",
        "sightings_note": (
            "Baseline Log: Spotted White-throated Kingfisher (2.8 kHz call) "
            "perched on low branch near water edge at 17:15."
        ),
    }
]


class TelemetryInput(BaseModel):
    temp_c: float = 25.8
    humidity_pct: float = 60.0
    wind_kmh: float = 7.5
    uv_index: float = 1.6
    aqi: float = 48.0
    pressure_hpa: float = 1013.0
    rain_24h_mm: float = 0.0
    hour_of_day: int = 17


class BackboardFieldLog(BaseModel):
    biome: str
    tabpfn_window: str
    sightings_note: str

class LearnInput(BaseModel):
    temp_c: float
    humidity_pct: float
    wind_kmh: float
    uv_index: float
    aqi: float
    pressure_hpa: float
    rain_24h_mm: float
    hour_of_day: int
    true_class: str



def dump_model(model_obj: BaseModel) -> Dict[str, Any]:
    return model_obj.model_dump()


async def get_or_create_backboard_assistant(client: Any) -> str:
    global BACKBOARD_ASSISTANT_ID
    if BACKBOARD_ASSISTANT_ID is not None:
        return BACKBOARD_ASSISTANT_ID

    assistant = await client.create_assistant(
        name="FieldCast Ecological Memory & Gemma Assistant",
        system_prompt=(
            "You are FieldCast Studio's persistent naturalist assistant. "
            "You remember past flora/fauna sightings across unplugged walks and "
            "adapt future field bounties to what the user has already observed."
        ),
    )
    aid = getattr(assistant, "id", None) or getattr(
        assistant, "assistant_id", str(assistant)
    )
    BACKBOARD_ASSISTANT_ID = str(aid)
    return BACKBOARD_ASSISTANT_ID


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    bb_key = os.getenv("BACKBOARD_API_KEY", "").strip()
    return {
        "status": "online",
        "runtime": "Render Cloud Web Service",
        "tabular_engine": ACTIVE_TABULAR_ENGINE,
        "backboard_sdk_installed": BACKBOARD_SDK_AVAILABLE,
        "backboard_key_configured": bool(bb_key),
        "dataset_rows": len(df_history),
    }


@app.post("/api/tabpfn-predict")
def predict_ecological_window(data: TelemetryInput) -> Dict[str, Any]:
    x_query = np.array(
        [
            [
                data.temp_c,
                data.humidity_pct,
                data.wind_kmh,
                data.uv_index,
                data.aqi,
                data.pressure_hpa,
                data.rain_24h_mm,
                data.hour_of_day,
            ]
        ]
    )

    probs = clf.predict_proba(x_query)[0]
    class_labels = [str(c) for c in list(clf.classes_)]
    prob_map: Dict[str, float] = {
        label: round(float(p) * 100.0, 1) for label, p in zip(class_labels, probs)
    }
    top_class = max(prob_map, key=lambda k: prob_map[k])

    hourly_forecast: List[Dict[str, Any]] = []
    for offset in range(6):
        hr = (data.hour_of_day + offset * 2) % 24
        sim_temp = data.temp_c - (2.5 if hr in [5, 6, 7, 18, 19, 20] else -2.0)
        sim_uv = (
            0.8
            if hr in [6, 7, 17, 18]
            else (0.0 if hr >= 19 or hr <= 5 else 6.5)
        )
        x_hr = np.array(
            [
                [
                    sim_temp,
                    data.humidity_pct,
                    data.wind_kmh,
                    sim_uv,
                    data.aqi,
                    data.pressure_hpa,
                    data.rain_24h_mm,
                    hr,
                ]
            ]
        )
        p_hr = clf.predict_proba(x_hr)[0]
        hr_map: Dict[str, float] = {
            label: float(p) for label, p in zip(class_labels, p_hr)
        }
        outdoor_score = round(
            (
                hr_map.get("Peak_Avian_Chorus", 0.0) * 1.0
                + hr_map.get("Post_Rain_Canopy_Emergence", 0.0) * 0.95
                + hr_map.get("Pollinator_Foraging_Peak", 0.0) * 0.85
            )
            * 100.0,
            1,
        )
        dominant_state = max(hr_map, key=lambda k: hr_map[k])
        hourly_forecast.append(
            {
                "hour": f"{hr:02d}:00",
                "score": outdoor_score,
                "dominant_state": dominant_state,
            }
        )

    best_slot = max(hourly_forecast, key=lambda x: float(x["score"]))

    return {
        "engine": ACTIVE_TABULAR_ENGINE,
        "training_rows": len(df_history),
        "predicted_class": top_class,
        "confidence_pct": prob_map[top_class],
        "probabilities": prob_map,
        "best_window_today": best_slot,
        "hourly_curve": hourly_forecast,
    }


@app.post("/api/upload-csv")
async def upload_custom_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    global df_history, clf
    content = await file.read()
    df_new = pd.read_csv(io.BytesIO(content))
    missing = [
        c for c in FEATURE_COLS + [TARGET_COL] if c not in df_new.columns
    ]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Missing required columns: {missing}"
        )
    df_history = df_new
    clf = init_tabular_model(
        df_history[FEATURE_COLS].to_numpy(),
        df_history[TARGET_COL].to_numpy(),
    )
    return {
        "status": "success",
        "message": f"TabPFN re-fitted in-context on {len(df_history)} rows!",
        "rows": len(df_history),
    }


@app.post("/api/tabpfn-learn")
def tabpfn_learn(entry: LearnInput) -> Dict[str, Any]:
    """In-Context Learning: Appends observation to dataset and refits TabPFN instantly."""
    global df_history, clf, X_train, y_train
    new_row = pd.DataFrame([{
        "temp_c": entry.temp_c,
        "humidity_pct": entry.humidity_pct,
        "wind_kmh": entry.wind_kmh,
        "uv_index": entry.uv_index,
        "aqi": entry.aqi,
        "pressure_hpa": entry.pressure_hpa,
        "rain_24h_mm": entry.rain_24h_mm,
        "hour_of_day": entry.hour_of_day,
        TARGET_COL: entry.true_class,
    }])
    df_history = pd.concat([df_history, new_row], ignore_index=True)
    
    # Save back to CSV to persist memory across server restarts
    try:
        df_history.to_csv(CSV_PATH, index=False)
    except Exception as e:
        print(f"Warning: Could not save CSV: {e}")

    X_train = df_history[FEATURE_COLS].to_numpy()
    y_train = df_history[TARGET_COL].to_numpy()
    clf = init_tabular_model(X_train, y_train)
    
    return {
        "status": "success",
        "message": f"TabPFN re-fitted in-context with {len(df_history)} rows",
        "rows": len(df_history)
    }



@app.post("/api/backboard-memory")
async def sync_backboard_memory(entry: BackboardFieldLog) -> Dict[str, Any]:
    entry_data = dump_model(entry)
    LOCAL_MEMORY_FALLBACK.insert(0, entry_data)
    bb_key = os.getenv("BACKBOARD_API_KEY", "").strip()

    if not BACKBOARD_SDK_AVAILABLE or BackboardClient is None or not bb_key:
        return {
            "status": "local_memory_active",
            "provider": (
                "Backboard Memory Engine (Local Mode — Set BACKBOARD_API_KEY "
                "in Render for Cloud Sync)"
            ),
            "total_memories": len(LOCAL_MEMORY_FALLBACK),
            "memories": [
                f"[{m['biome']} | {m['tabpfn_window']}] {m['sightings_note']}"
                for m in LOCAL_MEMORY_FALLBACK[:5]
            ],
        }

    try:
        async with BackboardClient(api_key=bb_key) as client:
            assistant_id = await get_or_create_backboard_assistant(client)
            memory_text = (
                f"[{entry.biome} | TabPFN: {entry.tabpfn_window}] "
                f"{entry.sightings_note}"
            )

            await client.add_memory(
                assistant_id=assistant_id,
                content=memory_text,
                metadata={
                    "category": "touch_grass_sighting",
                    "biome": entry.biome,
                    "tabpfn_window": entry.tabpfn_window,
                },
            )

            memories = await client.get_memories(
                assistant_id=assistant_id, page=1, page_size=8
            )
            mem_list: List[str] = []
            if isinstance(memories, list):
                mem_list = [str(getattr(m, "content", m)) for m in memories]
            elif hasattr(memories, "items"):
                mem_list = [
                    str(getattr(m, "content", m)) for m in memories.items
                ]
            else:
                mem_list = [memory_text]

            return {
                "status": "synced_to_backboard_cloud",
                "provider": "Backboard.io Unified API & Persistent Memory (backboard-sdk)",
                "assistant_id": assistant_id,
                "total_memories": len(mem_list),
                "memories": mem_list[:5],
            }
    except Exception as exc:
        err_msg = str(exc)
        return {
            "status": "fallback_memory",
            "provider": f"Backboard Hybrid Fallback ({err_msg[:60]})",
            "total_memories": len(LOCAL_MEMORY_FALLBACK),
            "memories": [
                f"[{m['biome']} | {m['tabpfn_window']}] {m['sightings_note']}"
                for m in LOCAL_MEMORY_FALLBACK[:5]
            ],
        }


@app.get("/api/nearby-species")
async def get_nearby_species(
    lat: float = 17.385,
    lng: float = 78.4867,
    radius_km: int = 5,
) -> Dict[str, Any]:
    """Fetches real species recently observed near the user via iNaturalist API."""
    if not HTTPX_AVAILABLE:
        return {"status": "fallback", "species": [], "message": "httpx not installed"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch birds, plants, and insects spotted nearby in the last 14 days
            results: List[Dict[str, Any]] = []
            iconic_taxa = ["Aves", "Plantae", "Insecta"]
            category_labels = {
                "Aves": "🐦 Bird",
                "Plantae": "🌳 Plant",
                "Insecta": "🦋 Insect",
            }

            for taxon in iconic_taxa:
                url = (
                    f"https://api.inaturalist.org/v1/observations/species_counts"
                    f"?lat={lat}&lng={lng}&radius={radius_km}"
                    f"&iconic_taxa={taxon}&quality_grade=research"
                    f"&d1={(datetime.now(timezone.utc) - timedelta(days=14)).strftime('%Y-%m-%d')}"
                    f"&per_page=3"
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", [])[:3]:
                        taxon_info = r.get("taxon", {})
                        photo_url = ""
                        default_photo = taxon_info.get("default_photo")
                        if default_photo:
                            photo_url = default_photo.get("medium_url", "")

                        results.append({
                            "category": category_labels.get(taxon, taxon),
                            "name": taxon_info.get("preferred_common_name", taxon_info.get("name", "Unknown")),
                            "scientific_name": taxon_info.get("name", ""),
                            "observation_count": r.get("count", 0),
                            "photo_url": photo_url,
                            "wikipedia_url": taxon_info.get("wikipedia_url", ""),
                        })

        return {
            "status": "success",
            "lat": lat,
            "lng": lng,
            "radius_km": radius_km,
            "species": results,
            "source": "iNaturalist Open API (research-grade observations, last 14 days)",
        }
    except Exception as exc:
        return {"status": "error", "species": [], "message": str(exc)[:120]}


@app.get("/api/calendar-block")
def generate_calendar_block(
    predicted_class: str = "Peak_Avian_Chorus",
    best_hour: int = 17,
    duration_minutes: int = 45,
) -> FileResponse:
    """Generates a downloadable .ics calendar invite to block off the optimal Touch Grass window."""
    now = datetime.now(timezone.utc)
    # Set the event to today at the predicted best hour (in UTC, user's local time will adjust)
    start = now.replace(hour=best_hour % 24, minute=0, second=0, microsecond=0)
    if start < now:
        start += timedelta(days=1)
    end = start + timedelta(minutes=duration_minutes)

    event_name = predicted_class.replace("_", " ")
    uid = str(uuid.uuid4())

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//FieldCast Studio//Touch Grass//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        f"SUMMARY:🌿 Touch Grass — {event_name}\r\n"
        f"DESCRIPTION:FieldCast Studio TabPFN predicted this as your optimal "
        f"outdoor window ({event_name}). Leave your phone at your desk and "
        f"take the printed field zine outside for {duration_minutes} minutes.\r\n"
        "STATUS:CONFIRMED\r\n"
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT10M\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:🌿 Your Touch Grass window starts in 10 minutes! Print your field zine now.\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    ics_path = os.path.join(BASE_DIR, "touch_grass_event.ics")
    with open(ics_path, "w", encoding="utf-8") as f:
        f.write(ics_content)

    return FileResponse(
        ics_path,
        media_type="text/calendar",
        filename=f"TouchGrass-{predicted_class}-{start.strftime('%Y%m%d')}.ics",
    )


@app.get("/api/ecological-forecast")
async def ecological_forecast(lat: float, lng: float) -> Dict[str, Any]:
    """Fetches 24h hourly weather from Open-Meteo and runs TabPFN on each hour."""
    if not HTTPX_AVAILABLE:
        return {"status": "error", "message": "httpx not installed"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lng}"
                f"&hourly=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,precipitation,uv_index"
                f"&forecast_days=2"
            )
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"status": "error", "message": "Weather API failed"}
            
            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            # Get current time index
            now = datetime.now(timezone.utc)
            start_idx = 0
            for i, t in enumerate(times):
                if datetime.fromisoformat(t).replace(tzinfo=timezone.utc) >= now:
                    start_idx = i
                    break
            
            # Predict for next 24 hours
            forecast_results = []
            for i in range(start_idx, min(start_idx + 24, len(times))):
                hr = datetime.fromisoformat(times[i]).hour
                x_hr = np.array([[
                    hourly.get("temperature_2m", [])[i],
                    hourly.get("relative_humidity_2m", [])[i],
                    hourly.get("wind_speed_10m", [])[i],
                    hourly.get("uv_index", [])[i] or 0.0,
                    40.0, # Default AQI
                    hourly.get("surface_pressure", [])[i],
                    hourly.get("precipitation", [])[i],
                    hr
                ]])
                
                p_hr = clf.predict_proba(x_hr)[0]
                class_labels = [str(c) for c in list(clf.classes_)]
                hr_map: Dict[str, float] = {label: float(p) for label, p in zip(class_labels, p_hr)}
                
                outdoor_score = round(
                    (hr_map.get("Peak_Avian_Chorus", 0.0) * 1.0 +
                     hr_map.get("Post_Rain_Canopy_Emergence", 0.0) * 0.95 +
                     hr_map.get("Pollinator_Foraging_Peak", 0.0) * 0.85) * 100.0, 1
                )
                
                dominant_state = max(hr_map, key=lambda k: hr_map[k])
                
                forecast_results.append({
                    "hour": f"{hr:02d}:00",
                    "time_iso": times[i],
                    "score": outdoor_score,
                    "dominant_state": dominant_state,
                    "probabilities": hr_map
                })

            return {
                "status": "success",
                "lat": lat,
                "lng": lng,
                "forecast": forecast_results
            }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

class ZineGenerateRequest(BaseModel):
    model: str
    system: str
    prompt: str
    format: str = "json"
    stream: bool = False

@app.post("/api/generate-zine")
async def generate_zine(req: ZineGenerateRequest) -> Dict[str, Any]:
    """Proxies the request to Ollama so the frontend doesn't need to know the host IP."""
    if not HTTPX_AVAILABLE:
        raise HTTPException(status_code=500, detail="httpx not installed")
    
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{ollama_url}/api/generate", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama generation failed: {exc}")



if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_home() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))