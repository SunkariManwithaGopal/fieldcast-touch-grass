# 🌿 FieldCast Studio

> **A weather window estimator + printable 1-page pocket field zine.**

FieldCast Studio helps developers step away from screens and into nature. It estimates an optimal outdoor window using weather heuristics and TabPFN (locally), formats a 1-page pocket field guide, and encourages leaving your phone at your desk.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi&style=for-the-badge)
![TabPFN](https://img.shields.io/badge/TabPFN-v2-orange?style=for-the-badge)
![Gemma](https://img.shields.io/badge/Gemma-2B-blue?logo=google&style=for-the-badge)
![GitHub Pages](https://img.shields.io/badge/Hosted-GitHub%20Pages-brightgreen?logo=github&style=for-the-badge)

---

## 🌐 Live Demo vs. Local Execution

- **Live Demo (GitHub Pages):** Runs client-side in your browser. It uses a JavaScript approximation of our weather threshold rules, pre-written regional zine text, and a canvas-animated spectrogram. The "Nearby Wildlife" panel queries live iNaturalist data.
- **Local Python Environment:** Runs the full FastAPI server with in-context TabPFN v2 inference on weather parameters and local Gemma 2B generation (`gemma2:2b` via Ollama).

---

## 🛑 The Problem

Many of us spend most of our workday in front of screens. When taking an outdoor break, three barriers cause decision fatigue:

1. **When?** — Uncertainty over whether current weather conditions are comfortable.
2. **What do I do?** — Aimless walks without an observational goal often end quickly.
3. **How do I unplug?** — Most nature apps require looking at a phone screen outdoors.

## 🚀 The Solution

FieldCast Studio addresses this with a simple workflow: evaluate weather data, print a physical one-page pocket guide, and step outside without your phone.

## ✨ Core Features

| Feature | Where It Runs | What It Does |
|---|---|---|
| **Weather Window Estimation** | Local (TabPFN) / Demo (JS rules) | Evaluates 7 weather features into 4 outdoor walk states |
| **24-Hour Timeline** | Browser (Open-Meteo API) | Visualizes state probabilities across the day |
| **Printable Field Zine** | Local (Gemma 2B) / Demo (Presets) | Formats a `@media print` 1-page foldable guide |
| **Animated Spectrogram** | Browser (HTML5 Canvas) | Illustrates syrinx harmonics for bird observation |
| **Nearby Species Panel** | Browser (iNaturalist API) | Shows research-grade sightings within 5 km |
| **Offline Extras** | Browser | LocalStorage streak tracking and `.ics` calendar exports |

## 🛠️ Quick Start

### Run Locally

```bash
# Clone the repo
git clone https://github.com/SunkariManwithaGopal/fieldcast-touch-grass.git
cd fieldcast-touch-grass

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Deploy to Render (1-Click)

1. Push this repo to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
3. Connect your `fieldcast-touch-grass` repository
4. Render reads `render.yaml` and auto-deploys in ~2 minutes

### Optional: Local Gemma 2B (Ollama)

For fully offline, private field zine generation:
```bash
# Install Ollama (https://ollama.com)
ollama pull gemma2:2b
ollama serve
```
The app will automatically detect Ollama and use Gemma 2B. Without Ollama, it falls back to curated biome presets.

## 🧠 How the AI Models Work Together

### TabPFN (Tabular Data → Probabilities)
Weather data is fundamentally **tabular numbers**. Asking a text LLM to guess probabilities from CSV rows leads to hallucinated math. TabPFN is a tabular foundation model purpose-built for this: it takes 8 numerical features and outputs calibrated class probabilities with zero hyperparameter tuning.

### Gemma 2B (Probabilities → Natural Language)
Once TabPFN produces the ecological classification, Gemma 2B translates it into a human-readable, printable field guide with specific species to look for, sensory exercises, and walking meditation prompts. Each model does what it's mathematically built for.

## 🔓 Why Open Innovation Matters

- **Privacy:** Your coordinates and personal reflections never touch a third-party commercial AI server.
- **Offline-Ready:** Both TabPFN and Gemma 2B run on a standard laptop CPU with zero internet needed.
- **Zero Cost:** No API keys, no token billing, no vendor lock-in.
- **Customizable:** Upload your own CSV dataset and TabPFN re-fits in-context instantly.

## License
MIT
