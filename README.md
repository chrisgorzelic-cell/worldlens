<div align="center">

# ◐ Worldlens

### A live, photoreal 3D globe of planet Earth — every signal, one lens.

Earthquakes, wildfires, storms, weather, air quality, live flights, **1,700+ real satellites**,
the Sun, Moon & planets, commodity trade flows, and a Global Stress Index — all streaming from
**free, keyless public feeds** onto a cinematic day/night Earth you can fly around.

[![License: MIT](https://img.shields.io/badge/License-MIT-38bdf8.svg)](LICENSE)
![No API keys](https://img.shields.io/badge/API%20keys-none-34d399)
![Read only](https://img.shields.io/badge/data-read--only-a78bfa)
![Python](https://img.shields.io/badge/collector-Python%20stdlib-fbbf24)
![WebGL](https://img.shields.io/badge/render-WebGL%20%2F%20globe.gl-fb7185)

</div>

> **Add a screenshot / GIF here** (`docs/preview.png`) — the day/night globe with the satellite shell and a trade-flow arc is the money shot.

---

## Why Worldlens

Most "world dashboards" bury you in tabs and charts. Worldlens puts the whole planet in front of
you as **one interactive globe**, then lets you **isolate exactly the signal you care about** with a
single click — a *lens*. It's built to be:

- **Keyless & private** — every feed is a free public source. No sign-up, no API keys, nothing is
  sent anywhere. A tiny Python script fetches the data; the browser just reads a JSON file.
- **Cinematic but honest** — real day/night terminator, drifting clouds, glowing atmosphere, and
  live-propagated satellites. All the numbers come from real sources and are labeled as such.
- **Correlative** — click a country and see its weather, air, quakes, hazards and flights together.
  Turn on the **Fire-risk** or **Energy** lens and watch hazards line up with supply nodes.

---

## ✨ Features

| | |
|---|---|
| 🌍 **Photoreal Earth** | Real sun-lit day/night terminator, rotating cloud veil, NASA Blue-Marble textures, 50 m country borders, glowing atmosphere, cinematic bloom. |
| 🛰️ **1,700+ live satellites** | Real Celestrak orbital elements propagated in-browser with **SGP4**. Click one to trace its live orbit and next overhead pass. |
| 🌦️ **Weather & hazards** | USGS earthquakes, NASA EONET + **GDACS** severity-scored disasters (pulsing rings), global wind / temp / precip / cloud / humidity / pressure, and air quality. |
| ✈️ **Live flights** | Thousands of real aircraft with callsign, type & altitude. |
| 🛡️ **Cyber threat watch** | Live attack sources (SANS ISC / DShield honeypots), online botnet C2 servers (abuse.ch Feodo Tracker), and vulnerabilities being **actively exploited** (CISA KEV) — as pulsing red nodes and animated attack arcs, plus a transparent 0–100 threat level. |
| 🪐 **Solar system & sky** | Sun, Moon and planets as sun-lit textured spheres (Saturn's rings, lunar phase) in their true sky directions, plus constellations and a real star field. On-device astronomy → live **zodiac & moon phase**. |
| 🔭 **Lenses** | One click isolates a *correlated* dataset: Seismic · Weather · Fire-risk · Air · Aviation · Orbital · Threats · Energy · Agri · Metals & chips · Shipping · Macro. |
| 💹 **Trade Desk** | Live commodities, rates & FX; curated commodity **supply nodes** that glow red when hazards/weather threaten them; and **animated trade-flow arcs** (oil, grain, metals, chips). |
| ◎ **Situation Brief** | One-tap synthesized intelligence report — seismic, hazards, orbital, markets, sky. |
| 🧭 **Built to run anywhere** | Static HTML + one Python file. Serve the folder, schedule the collector, done. A **Lite mode** trims effects for weak devices. |

---

## 🚀 Quick start

**Requirements:** Python 3 (standard library only — no `pip install`), and any static file server.
The globe itself loads its 3D engine from a CDN, so the browser needs internet.

```bash
git clone https://github.com/chrisgorzelic-cell/worldlens.git
cd worldlens

# 1) Fetch a data snapshot (writes public/world-status.json)
python3 collectors/worldlens_collector.py

# 2) Serve the public folder
cd public && python3 -m http.server 8080
```

Open **http://localhost:8080** 🌍

Keep the data fresh by re-running the collector on a schedule (every ~15 min):

```cron
*/15 * * * *  /usr/bin/python3 /path/to/worldlens/collectors/worldlens_collector.py
```

> Change where the snapshot is written with the `WORLDLENS_OUT` env var.

---

## 🧠 How it works

```
   free public APIs                 Python stdlib                     browser (WebGL)
 ┌───────────────────┐   fetch    ┌──────────────────────┐   reads   ┌──────────────────┐
 │ USGS · EONET ·    │──────────▶ │ worldlens_collector  │ ────────▶ │ index.html       │
 │ GDACS · Open-Meteo│            │  + sky.py (astronomy)│  JSON     │ globe.gl + three │
 │ adsb.lol · NOAA · │            │                      │           │  + satellite.js  │
 │ Celestrak · Yahoo │            │ → world-status.json  │           │  (SGP4, bloom)   │
 └───────────────────┘            └──────────────────────┘           └──────────────────┘
```

The collector is **best-effort**: any single dead feed is skipped without breaking the rest. It
writes one JSON snapshot; the page polls that snapshot and renders everything client-side. There is
no server, no database, and no account.

### Data sources (all keyless)

| Source | Provides |
|--------|----------|
| [USGS](https://earthquake.usgs.gov/) | Earthquakes (past 24 h) |
| [NASA EONET](https://eonet.gsfc.nasa.gov/) | Natural hazards (fires, storms, volcanoes, floods) |
| [GDACS](https://www.gdacs.org/) | Severity-scored global disaster alerts |
| [Open-Meteo](https://open-meteo.com/) | Global weather grid + air quality |
| [adsb.lol](https://adsb.lol/) | Live aircraft |
| [NOAA SWPC](https://www.swpc.noaa.gov/) | Space weather (Kp index) |
| [Celestrak](https://celestrak.org/) | Satellite orbital elements (TLE) |
| [SANS ISC / DShield](https://isc.sans.edu/) | Top attacking source IPs + ports under attack (honeypots) |
| [abuse.ch Feodo Tracker](https://feodotracker.abuse.ch/) | Online botnet command-and-control servers |
| [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Vulnerabilities being actively exploited in the wild |
| [ip-api.com](https://ip-api.com/) | Geolocation of attacker IPs (keyless batch) |
| [Yahoo Finance](https://finance.yahoo.com/) | Indices, commodities, rates, FX |
| [CoinGecko](https://www.coingecko.com/) | Crypto |

---

## ⚙️ Configuration

Drop your own **home beacon** and **satellite-pass location** by defining a global before the page's
module runs (e.g. in a tiny `config.js` you include first):

```html
<script>
  window.WORLDLENS = {
    observer:  { lat: 51.5, lon: -0.12, name: "London" },
    presences: [ { name: "Home", lat: 51.5, lon: -0.12, note: "my base" } ]
  };
</script>
```

Nothing is hardcoded — leave it unset and the personal beacon simply doesn't appear.

---

## 🛠️ Tech stack

- **Rendering:** [globe.gl](https://github.com/vasturiano/globe.gl) + [three.js](https://threejs.org/) + `UnrealBloomPass`
- **Orbits:** [satellite.js](https://github.com/shashwatak/satellite-js) (SGP4)
- **Sun position:** [solar-calculator](https://github.com/vasturiano/solar-calculator)
- **Astronomy:** on-device (JPL Keplerian elements + a truncated Meeus lunar series) — pure Python
- **Collector:** Python standard library only

---

## 🙏 Credits & attribution

Worldlens was **inspired by the idea** behind [`worldmonitor`](https://github.com/koala73/worldmonitor)
by **Elie Habib** — a real-time global-intelligence dashboard. Worldlens is an **independent,
from-scratch reimplementation**: a different language, a different architecture, and different data
sources. **No source code from the original project is used**, and the two share no code.

Built on the shoulders of these excellent open-source projects and datasets — thank you:

- [globe.gl](https://github.com/vasturiano/globe.gl), [solar-calculator](https://github.com/vasturiano/solar-calculator) (MIT) — Vasco Asturiano. Day/night, clouds & rendering patterns adapt globe.gl's MIT examples.
- [three.js](https://github.com/mrdoob/three.js) (MIT)
- [satellite.js](https://github.com/shashwatak/satellite-js) (MIT)
- Planet & moon textures from [threex.planets](https://github.com/jeromeetienne/threex.planets) (MIT) — Jérôme Étienne
- Country borders from [Natural Earth](https://www.naturalearthdata.com/) (public domain)
- All the public data providers listed above

See [CREDITS.md](CREDITS.md) for the full attribution list.

---

## 📄 License

[MIT](LICENSE) — do what you like, just keep the notice. Data remains subject to each provider's
terms; Worldlens only reads public endpoints.

<div align="center">
<sub>Worldlens · a live lens on planet Earth · keyless & read-only</sub>
</div>
