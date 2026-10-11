import requests
import json
import csv
import subprocess
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# 1. Fetch Open-Meteo with &timezone=auto
lat, lng = 17.385, 78.4867
url = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lng}"
    f"&hourly=temperature_2m,relative_humidity_2m,surface_pressure,pressure_msl,wind_speed_10m,precipitation,uv_index"
    f"&forecast_days=2"
    f"&timezone=auto"
)

res = requests.get(url)
data = res.json()

tz = data.get("timezone")
tz_abbr = data.get("timezone_abbreviation")
utc_offset = data.get("utc_offset_seconds")

print("=== OPEN-METEO TIMEZONE CONFIRMATION ===")
print(f"Request URL: {url}")
print(f"Returned Timezone: {tz}")
print(f"Timezone Abbreviation: {tz_abbr}")
print(f"UTC Offset (seconds): {utc_offset} ({utc_offset / 3600:+.1f} hours)")
assert tz == "Asia/Kolkata", f"Expected Asia/Kolkata but got {tz}"
assert utc_offset == 19800, f"Expected 19800 (+5:30) but got {utc_offset}"
print("CONFIRMED: The returned 'time' array represents Hyderabad local time (IST, UTC+5:30).\n")

hourly = data["hourly"]
times = hourly["time"]

# Current time in Hyderabad (Asia/Kolkata)
ist_tz = ZoneInfo("Asia/Kolkata")
now_local = datetime.now(timezone.utc).astimezone(ist_tz)
print(f"Current Hyderabad Local Time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

start_idx = 0
for i, t in enumerate(times):
    # times[i] format: 'YYYY-MM-DDTHH:00' in local time
    dt_local = datetime.fromisoformat(t).replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if dt_local >= now_local:
        start_idx = i
        break

print(f"Selected starting forecast slot: {times[start_idx]} (Index: {start_idx})\n")

# Prepare payloads for 24 hours
rows_payload = []
rows_meta = []

for i in range(start_idx, start_idx + 24):
    dt = datetime.fromisoformat(times[i])
    local_hour = dt.hour  # True Hyderabad local hour
    temp = float(hourly["temperature_2m"][i])
    humidity = float(hourly["relative_humidity_2m"][i])
    wind = float(hourly["wind_speed_10m"][i])
    uv = float(hourly["uv_index"][i]) if hourly["uv_index"][i] is not None else 0.0
    aqi = 40.0
    surface_p = float(hourly["surface_pressure"][i])
    msl_p = float(hourly["pressure_msl"][i])
    rain = float(hourly["precipitation"][i])

    rows_meta.append({
        "time_str": f"{local_hour:02d}:00",
        "time_iso": times[i],
        "local_hour": local_hour,
        "temp_c": temp,
        "humidity_pct": humidity,
        "wind_kmh": wind,
        "uv_index": uv,
        "aqi": aqi,
        "surface_p": surface_p,
        "msl_p": msl_p,
        "rain_24h_mm": rain,
    })

    # Payload for JS rules
    rows_payload.append({
        "temp_c": temp,
        "humidity_pct": humidity,
        "wind_kmh": wind,
        "uv_index": uv,
        "aqi": aqi,
        "pressure_hpa": surface_p,
        "rain_24h_mm": rain,
        "hour_of_day": local_hour,
    })

# 2. Run Node on the extracted rules from index.html
temp_inputs_path = "temp_inputs.json"
with open(temp_inputs_path, "w", encoding="utf-8") as f:
    json.dump(rows_payload, f)

node_exe = r"C:\Program Files\nodejs\node.exe"
node_res = subprocess.run([node_exe, "run_rules_node.js", temp_inputs_path], capture_output=True, text=True)
if node_res.returncode != 0:
    print("Node execution error:", node_res.stderr)
    raise RuntimeError("Node rule evaluation failed")

js_classifications = json.loads(node_res.stdout.strip())
print(f"Node successfully classified all {len(js_classifications)} rows using exact extracted index.html rules.")

# 3. Query TabPFN for both Run 1 (surface_pressure) and Run 2 (pressure_msl)
tabpfn_run1 = [] # surface_pressure
tabpfn_run2 = [] # pressure_msl

for idx, m in enumerate(rows_meta):
    # Run 1: surface_pressure
    p1 = {
        "temp_c": m["temp_c"],
        "humidity_pct": m["humidity_pct"],
        "wind_kmh": m["wind_kmh"],
        "uv_index": m["uv_index"],
        "aqi": m["aqi"],
        "pressure_hpa": m["surface_p"],
        "rain_24h_mm": m["rain_24h_mm"],
        "hour_of_day": m["local_hour"],
    }
    r1 = requests.post("http://127.0.0.1:8000/api/tabpfn-predict", json=p1).json()
    tabpfn_run1.append(r1)

    # Run 2: pressure_msl
    p2 = {
        "temp_c": m["temp_c"],
        "humidity_pct": m["humidity_pct"],
        "wind_kmh": m["wind_kmh"],
        "uv_index": m["uv_index"],
        "aqi": m["aqi"],
        "pressure_hpa": m["msl_p"],
        "rain_24h_mm": m["rain_24h_mm"],
        "hour_of_day": m["local_hour"],
    }
    r2 = requests.post("http://127.0.0.1:8000/api/tabpfn-predict", json=p2).json()
    tabpfn_run2.append(r2)

if os.path.exists(temp_inputs_path):
    os.remove(temp_inputs_path)

# Assemble combined rows
combined_rows = []
for idx in range(24):
    m = rows_meta[idx]
    js_top = js_classifications[idx]["predicted_class"]
    js_probs = js_classifications[idx]["probabilities"]

    r1_top = tabpfn_run1[idx]["predicted_class"]
    r1_probs = tabpfn_run1[idx]["probabilities"]
    r1_diff = (js_top != r1_top)

    r2_top = tabpfn_run2[idx]["predicted_class"]
    r2_probs = tabpfn_run2[idx]["probabilities"]
    r2_diff = (js_top != r2_top)

    combined_rows.append({
        "hour_local": m["time_str"],
        "time_iso": m["time_iso"],
        "local_hour": m["local_hour"],
        "temp_c": m["temp_c"],
        "humidity_pct": m["humidity_pct"],
        "wind_kmh": m["wind_kmh"],
        "uv_index": m["uv_index"],
        "rain_24h_mm": m["rain_24h_mm"],
        "surface_p_hpa": m["surface_p"],
        "msl_p_hpa": m["msl_p"],
        "rule_top_state": js_top,
        "run1_surface_p_top": r1_top,
        "run1_differs": r1_diff,
        "run1_confidence": tabpfn_run1[idx]["confidence_pct"],
        "run1_probs": json.dumps(r1_probs),
        "run2_msl_p_top": r2_top,
        "run2_differs": r2_diff,
        "run2_confidence": tabpfn_run2[idx]["confidence_pct"],
        "run2_probs": json.dumps(r2_probs),
        "r1_probs_map": r1_probs,
        "r2_probs_map": r2_probs,
    })

# Save outputs/comparison_local_hour.csv
fieldnames = [
    "hour_local", "time_iso", "local_hour", "temp_c", "humidity_pct",
    "wind_kmh", "uv_index", "rain_24h_mm", "surface_p_hpa", "msl_p_hpa",
    "rule_top_state", "run1_surface_p_top", "run1_differs", "run1_confidence", "run1_probs",
    "run2_msl_p_top", "run2_differs", "run2_confidence", "run2_probs"
]
with open("outputs/comparison_local_hour.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in combined_rows:
        writer.writerow({k: r[k] for k in fieldnames})

# Also update outputs/comparison.csv for consistency
with open("outputs/comparison.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in combined_rows:
        writer.writerow({k: r[k] for k in fieldnames})

# Reporting Run 1
run1_diffs = sum(1 for r in combined_rows if r["run1_differs"])
print("\n" + "="*80)
print(f"RUN 1: SURFACE PRESSURE (~956 hPa - Outside Training Range)")
print(f"Disagreements: {run1_diffs} out of 24 hours ({run1_diffs/24*100:.1f}%)")
print("="*80)
print("| Local Hour | Rule Top State | TabPFN Top State (Run 1) | Differs? | TabPFN Probabilities |")
print("|---|---|---|---|---|")
for r in combined_rows:
    print(f"| {r['hour_local']} | {r['rule_top_state']} | {r['run1_surface_p_top']} | {r['run1_differs']} | {r['run1_probs']} |")

# Reporting Run 2
run2_diffs = sum(1 for r in combined_rows if r["run2_differs"])
print("\n" + "="*80)
print(f"RUN 2: MEAN SEA LEVEL PRESSURE pressure_msl (~1011-1014 hPa - Inside Training Range)")
print(f"Disagreements: {run2_diffs} out of 24 hours ({run2_diffs/24*100:.1f}%)")
print("="*80)
print("| Local Hour | Rule Top State | TabPFN Top State (Run 2) | Differs? | TabPFN Probabilities |")
print("|---|---|---|---|---|")
for r in combined_rows:
    print(f"| {r['hour_local']} | {r['rule_top_state']} | {r['run2_msl_p_top']} | {r['run2_differs']} | {r['run2_probs']} |")

# Run 1 vs Run 2 comparison
p_shifts = sum(1 for r in combined_rows if r["run1_surface_p_top"] != r["run2_msl_p_top"])
print("\n" + "="*80)
print(f"EFFECT OF SURFACE PRESSURE VS MSL PRESSURE ON TABPFN:")
print(f"Hours where TabPFN top class changed between surface_p vs msl_p: {p_shifts} out of 24 ({p_shifts/24*100:.1f}%)")
print("="*80)
