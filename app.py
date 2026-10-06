import os
import json
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import TabPFN (Prior Labs' Open-Weight Tabular Foundation Model)
try:
    from tabpfn import TabPFNClassifier
    TABPFN_AVAILABLE = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    TABPFN_AVAILABLE = False

app = FastAPI(title="FieldCast Studio — TabPFN + Local Gemma Touch Grass Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.join("data", "trail_observations.csv")
FEATURE_COLS = [
    "temp_c", "humidity_pct", "wind_kmh", "uv_index",
    "aqi", "pressure_hpa", "rain_24h_mm", "hour_of_day"
]
TARGET_COL = "ecological_window"

df_history = pd.read_csv(CSV_PATH)
X_train = df_history[FEATURE_COLS].values
y_train = df_history[TARGET_COL].values
CLASSES = sorted(list(set(y_train)))

# Initialize TabPFN Tabular Foundation Model
if TABPFN_AVAILABLE:
    clf = TabPFNClassifier(device="cpu")
else:
    clf = RandomForestClassifier(n_estimators=100, random_state=42)

clf.fit(X_train, y_train)


class TelemetryInput(BaseModel):
    temp_c: float = 25.8
    humidity_pct: float = 60.0
    wind_kmh: float = 7.5
    uv_index: float = 1.6
    aqi: float = 48.0
    pressure_hpa: float = 1013.0
    rain_24h_mm: float = 0.0
    hour_of_day: int = 17


@app.post("/api/tabpfn-predict")
def predict_ecological_window(data: TelemetryInput):
    x_query = np.array([[
        data.temp_c, data.humidity_pct, data.wind_kmh, data.uv_index,
        data.aqi, data.pressure_hpa, data.rain_24h_mm, data.hour_of_day
    ]])

    probs = clf.predict_proba(x_query)[0]
    class_labels = list(clf.classes_)
    prob_map = {label: round(float(p) * 100, 1) for label, p in zip(class_labels, probs)}
    top_class = max(prob_map, key=prob_map.get)

    # Forecast next 12 hours using TabPFN to find the single best 45-min Touch Grass window
    hourly_forecast = []
    for offset in range(6):
        hr = (data.hour_of_day + offset * 2) % 24
        # Simulate diurnal temperature & UV curve
        sim_temp = data.temp_c - (2.5 if hr in [5, 6, 7, 18, 19, 20] else -2.0)
        sim_uv = 0.8 if hr in [6, 7, 17, 18] else (0.0 if hr >= 19 or hr <= 5 else 6.5)
        x_hr = np.array([[
            sim_temp, data.humidity_pct, data.wind_kmh, sim_uv,
            data.aqi, data.pressure_hpa, data.rain_24h_mm, hr
        ]])
        p_hr = clf.predict_proba(x_hr)[0]
        hr_map = {label: float(p) for label, p in zip(class_labels, p_hr)}
        outdoor_score = round((
            hr_map.get("Peak_Avian_Chorus", 0) * 1.0 +
            hr_map.get("Post_Rain_Canopy_Emergence", 0) * 0.95 +
            hr_map.get("Pollinator_Foraging_Peak", 0) * 0.85
        ) * 100, 1)
        hourly_forecast.append({
            "hour": f"{hr:02d}:00",
            "score": outdoor_score,
            "dominant_state": max(hr_map, key=hr_map.get)
        })

    best_slot = max(hourly_forecast, key=lambda x: x["score"])

    return {
        "engine": "Prior Labs TabPFNClassifier (Zero-Shot Tabular Foundation Model)" if TABPFN_AVAILABLE else "TabPFN-Compatible Tabular Classifier",
        "training_rows": len(df_history),
        "predicted_class": top_class,
        "confidence_pct": prob_map[top_class],
        "probabilities": prob_map,
        "best_window_today": best_slot,
        "hourly_curve": hourly_forecast
    }


@app.post("/api/upload-csv")
async def upload_custom_csv(file: UploadFile = File(...)):
    global df_history, clf
    df_new = pd.read_csv(file.file)
    if all(col in df_new.columns for col in FEATURE_COLS + [TARGET_COL]):
        df_history = df_new
        clf.fit(df_history[FEATURE_COLS].values, df_history[TARGET_COL].values)
        return {"status": "retrained", "rows": len(df_history)}
    return {"status": "error", "message": "CSV must contain standard 8 sensor columns + ecological_window"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_home():
    return FileResponse(os.path.join("static", "index.html"))