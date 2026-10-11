# 🌿 FieldCast Studio

> **An open-source micro-climate ecological predictor + printable 1-page field zine + acoustic bird spectrogram kit.**

FieldCast Studio gets software engineers off their screens and into nature in under 20 seconds. It predicts the best time to go outside using AI, prints a physical field guide so you leave your phone behind, and remembers your nature sightings across sessions.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi&style=for-the-badge)
![TabPFN](https://img.shields.io/badge/TabPFN-v2-orange?style=for-the-badge)
![Gemma](https://img.shields.io/badge/Gemma-2B-blue?logo=google&style=for-the-badge)
![Render](https://img.shields.io/badge/Deployed-Render-purple?logo=render&style=for-the-badge)

*(Note: Add your demo GIF here! For now, this is a placeholder)*
> `![Demo](https://via.placeholder.com/800x400.png?text=Record+a+GIF+of+the+app+and+put+it+here)`

---

## 🛑 The Problem

Software engineers average **11+ hours of daily screen time**. When they need an outdoor break, they face three decision-fatigue barriers:

1. **When?** — Is now actually a good time weather-wise?
2. **What do I do?** — Aimless walks feel pointless and end quickly.
3. **How do I unplug?** — Every "nature app" requires staring at a phone screen outdoors.

## 🚀 The Solution

FieldCast Studio uses **two open-weight AI models** (one for numbers, one for language) to eliminate all three barriers:

```mermaid
graph LR
    A[🌦️ Open-Meteo<br/>24h Forecast] --> B[📊 TabPFN<br/>Tabular Foundation Model]
    B --> C{Ecological State<br/>Classification}
    C --> D[🐦 Peak Avian Chorus]
    C --> E[🦋 Pollinator Foraging]
    C --> F[🍄 Post-Rain Emergence]
    C --> G[☀️ High UV Shade]
    D & E & F & G --> H[🤖 Gemma 2B<br/>via Ollama]
    H --> I[🖨️ Printable 1-Page<br/>Field Zine]
    I --> J[🚪 Leave Phone<br/>Walk Outside]
    J --> K[📓 Post-Walk<br/>Field Notes]
    K --> L[🧠 Backboard Cloud<br/>Persistent Memory]
    A2[📍 Geolocation] --> M[🌍 iNaturalist API<br/>Real Species]
    A2 --> N[🔊 xeno-canto API<br/>Bird Audio]
    M & N --> I
```

## ✨ Core Features

| Feature | Technology | What It Does |
|---|---|---|
| **Ecological Window Predictor** | TabPFN v2 | Classifies 8 micro-climate CSV features into 4 ecological states |
| **24-Hour Timeline Forecast** | Open-Meteo API | Visualizes TabPFN predictions across the entire day |
| **Printable Field Zine** | Gemma 2B (Ollama) | Generates a `@media print` 1-page zine with species bounties |
| **Acoustic Bird Referencing** | xeno-canto API | Fetches and plays real bird audio samples for predicted species |
| **Streak Gamification** | LocalStorage | Motivates daily outdoor habits with 🔥 streaks and badges |
| **Print-to-Digital QR Codes** | QRServer API | Injects QR links into the print zine bridging physical and digital |
| **Real Nearby Species** | iNaturalist API | Shows flora/fauna spotted within 5 km in the last 14 days |
| **Persistent Memory** | Backboard.io SDK | Logs your sightings to a cloud agent brain |
| **Calendar Block Export** | .ics (RFC 5545) | Downloads a calendar invite to block off your outdoor window |
| **Social Web Sharing** | Web Share API | Shares your custom zine and predictions to social media |

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
