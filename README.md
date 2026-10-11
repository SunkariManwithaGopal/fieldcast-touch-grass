# 🌿 FieldCast Studio

> **A weather window estimator + printable 1-page pocket field zine.**

FieldCast Studio helps developers step away from screens and into nature. It evaluates weather conditions to estimate optimal outdoor observation windows, formats a printable 1-page pocket field guide, and encourages leaving your phone at your desk.

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi&style=for-the-badge)
![TabPFN](https://img.shields.io/badge/TabPFN-v2-orange?style=for-the-badge)
![Gemma](https://img.shields.io/badge/Gemma-2B-blue?logo=google&style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge)

---

## What Runs Where

FieldCast Studio has two distinct execution tiers:

| Component | Live Web Demo (GitHub Pages) | Local Python Environment (`app.py`) | Proof / Evidence |
|---|---|---|---|
| **Tabular Ecological State Prediction** | **JavaScript Threshold Rules:** Deterministic `if/else` ladder based on hard thresholds (rain ≥ 10mm, humidity ≥ 82%, temp ≥ 34°C, hour ≤ 8 or ≥ 17). | **Prior Labs TabPFN v2:** TabPFNClassifier V2 tabular foundation model fitted in-context on 8 meteorological features. | Saved raw response: [`outputs/tabpfn_raw.json`](outputs/tabpfn_raw.json) |
| **Field Zine Generation** | **Client-Side Curated Presets:** Hardcoded regional species, sensory prompts, and observation anchors rendered in browser. | **Local Gemma 2B via Ollama:** Calls `gemma2:2b` at `http://127.0.0.1:11434` to dynamically compose structured JSON field guides. | Saved raw response: [`outputs/gemma_raw.json`](outputs/gemma_raw.json) |
| **24-Hour Forecast** | **Not computed in live demo** (browser fetches current weather only). | Backend proxies Open-Meteo and predicts each hour with TabPFN. | 24-hour evaluation: [`outputs/comparison_local_hour.csv`](outputs/comparison_local_hour.csv) |
| **Nearby Species** | Direct client fetch from iNaturalist Open API (last 14 days research-grade observations within 5 km). | FastAPI endpoint `/api/nearby-species` queries iNaturalist via `httpx`. | iNaturalist API |
| **Audio Spectrogram** | HTML5 Canvas decorative animation or live mic frequency view (no species ID). | Same frontend canvas widget. | Client-side Canvas |
| **Field Bounties & QR Code** | Prints QR code encoding an iNaturalist search URL (`https://www.inaturalist.org/search?q={species}`). | Same frontend print template. | Formatted in `index.html` |

---

## TabPFN vs. JavaScript Rules: Empirical Benchmark

We benchmarked TabPFN v2 against the client-side JavaScript threshold rules extracted from `index.html` across an identical 24-hour Open-Meteo forecast in Hyderabad (`17.385°N, 78.4867°E`, `&timezone=auto` in Asia/Kolkata local time).

The full dataset is saved in [`outputs/comparison_local_hour.csv`](outputs/comparison_local_hour.csv).

### Summary Statistics
- **Total Hours Evaluated:** 24 consecutive local hours
- **Top State Disagreement:** **5 out of 24 hours (20.8%)**
- **Top State Agreement:** **19 out of 24 hours (79.2%)**
- In-range hours (6 to 18): 5 of 13 differ. Evening/night hours are outside the training hour range.
- **Impact of Pressure Feature (Surface Pressure vs. MSL Pressure):**
  - Raw surface pressure in Hyderabad (~956 hPa) is outside the training dataset range (`[1002, 1016]` hPa).
  - When comparing Run 1 (`surface_pressure` ~956 hPa) vs Run 2 (`pressure_msl` ~1012 hPa), the top predicted class changed in **0 out of 24 hours (0.0%)**, though probabilities became sharper with in-distribution MSL pressure.

### Top Divergent Hours (Real Local Telemetry)

1. **Hour 08:00 Local IST (Morning Sun vs Rigid Cutoff)**
   - **Weather Inputs:** Temp = 27.6°C, Humidity = 49.0%, Wind = 5.8 km/h, UV Index = 2.45, Rain = 0.0 mm
   - **JS Rule Prediction:** `Peak_Avian_Chorus` (rule allocates 92.4% because `hour <= 8`)
   - **TabPFN v2 Prediction:** `Pollinator_Foraging_Peak` (68.7% confidence in Run 2; gives 23.4% to Avian Chorus)
   - **Why they differ:** The hardcoded JS rule uses a rigid `hour <= 8` boundary. TabPFN observes warming ambient conditions and rising solar angle, anticipating the pollinator activity phase.

2. **Hour 11:00 & 13:00 Local IST (Midday Solar Stress)**
   - **Weather Inputs (13:00):** Temp = 33.4°C, Humidity = 30.0%, Wind = 10.9 km/h, UV Index = 7.7, Rain = 0.0 mm
   - **JS Rule Prediction:** `Pollinator_Foraging_Peak` (rule threshold for High UV requires UV ≥ 8 or Temp ≥ 34)
   - **TabPFN v2 Prediction:** `High_UV_AQI_Short_Shade_Walk` (58.0% confidence; gives 24.2% to Pollinator)
   - **Why they differ:** With UV index 7.7 and 33.4°C, conditions are near the threshold. TabPFN smooths the boundary and flags high solar stress, whereas JS rules fall into midday pollinator foraging.

---

## ⏱️ Measured Inference Latency

Measured across cold start (model load + first inference) and warm server (subsequent inference):

| Endpoint | Engine / Model | Cold Start (Call 1) | Warm Server (Call 2) | Notes / Timeouts |
|---|---|---|---|---|
| `/api/tabpfn-predict` | Prior Labs TabPFN v2 (CPU/torch) | **68.2 seconds** | **4.83 seconds** | Loads TabPFN v2 weights into torch memory and fits on 32-row trail context. Client `fetch()` uses default browser timeout. |
| `/api/generate-zine` | Google Gemma 2B (`gemma2:2b` via Ollama) | **34.1 seconds** | **9.97 seconds** | Local LLM structured JSON generation. Server timeout: 45.0s (`httpx.Timeout(45.0)`). |

---

## 🛠️ Local Setup & Reproduction

### Prerequisites
- Python 3.11 or Python 3.12 (tested on Python 3.12.7)
- Ollama with `gemma2:2b`

### 1. Install Dependencies
```bash
git clone https://github.com/SunkariManwithaGopal/fieldcast-touch-grass.git
cd fieldcast-touch-grass

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt requests
```

### 2. Pull Local Language Model
```bash
ollama pull gemma2:2b
```

### 3. Start Backend Server
```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```
Open `http://localhost:8000` in your browser.

---

## Verified Output Artifacts

Every claim and metric in this repository is backed by locally generated artifacts:

| Output File | Description |
|---|---|
| [`outputs/tabpfn_raw.json`](outputs/tabpfn_raw.json) | Live response from `/api/tabpfn-predict` running Prior Labs TabPFN v2. |
| [`outputs/gemma_raw.json`](outputs/gemma_raw.json) | Live response from `/api/generate-zine` invoking local `gemma2:2b`. |
| [`outputs/comparison.csv`](outputs/comparison.csv) | Full 24-hour table comparing JS rules vs TabPFN probabilities. |
| [`outputs/comparison_local_hour.csv`](outputs/comparison_local_hour.csv) | Dual 24-hour comparison using true local hours (surface pressure vs MSL pressure). |
| [`outputs/facts_search.txt`](outputs/facts_search.txt) | Exact file and line occurrences for all audit keywords. |

---

## License

MIT
