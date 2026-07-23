#!/usr/bin/env python3
"""Worldlens collector — gathers free, keyless global-intelligence feeds and writes a single
read-only JSON snapshot the Worldlens globe reads. No API keys, no accounts, nothing is sent
anywhere. Every source is best-effort: one dead feed never breaks the rest.

Sources (all public, no key): USGS earthquakes | NASA EONET hazards | GDACS disaster alerts |
NOAA SWPC space weather | Open-Meteo weather + air-quality grids | adsb.lol live flights |
Celestrak satellite TLEs | Yahoo indices/commodities | CoinGecko crypto | on-device astronomy.

Writes: public/world-status.json  (override with the WORLDLENS_OUT env var)
Run: python3 collectors/worldlens_collector.py    (schedule every ~15 min via cron/launchd)
"""
import os, sys, json, datetime, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky

OUT = os.environ.get("WORLDLENS_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "world-status.json")
UA = "Worldlens/1.0 (+https://github.com/chrisgorzelic-cell/worldlens)"
TIMEOUT = 12


def fetch(url, parse="json", timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    if parse == "json":
        return json.loads(raw)
    return raw


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------- collectors
def get_quakes():
    """USGS all-day feed. Returns list of {lat,lon,mag,place,time,depth,url}."""
    j = fetch("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson")
    out = []
    for f in j.get("features", []):
        try:
            c = f["geometry"]["coordinates"]  # [lon, lat, depth]
            p = f["properties"]
            mag = p.get("mag")
            if mag is None:
                continue
            out.append({
                "lat": round(c[1], 3), "lon": round(c[0], 3),
                "depth": round(c[2], 1) if len(c) > 2 else None,
                "mag": round(float(mag), 1), "place": p.get("place") or "—",
                "time": p.get("time"), "url": p.get("url"),
            })
        except Exception:
            continue
    out.sort(key=lambda q: q["mag"], reverse=True)
    return out


EONET_CAT = {
    "wildfires": ("fire", "🔥"), "severeStorms": ("storm", "🌀"),
    "volcanoes": ("volcano", "🌋"), "floods": ("flood", "🌊"),
    "seaLakeIce": ("ice", "🧊"), "drought": ("drought", "🏜️"),
    "earthquakes": ("quake", "⚡"), "landslides": ("landslide", "⛰️"),
    "dustHaze": ("dust", "🌫️"), "manmade": ("manmade", "🏭"),
}


def get_hazards():
    """NASA EONET open natural events with a point geometry."""
    j = fetch("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=250")
    out = []
    for e in j.get("events", []):
        try:
            cats = e.get("categories", [])
            cid = cats[0]["id"] if cats else "manmade"
            kind, icon = EONET_CAT.get(cid, ("event", "📍"))
            geos = e.get("geometry", [])
            if not geos:
                continue
            g = geos[-1]  # most recent position
            if g.get("type") != "Point":
                continue
            lon, lat = g["coordinates"][0], g["coordinates"][1]
            out.append({
                "lat": round(lat, 3), "lon": round(lon, 3),
                "kind": kind, "icon": icon,
                "title": e.get("title") or kind,
                "date": g.get("date"), "url": (e.get("sources") or [{}])[0].get("url"),
            })
        except Exception:
            continue
    return out


GDACS_TYPE = {"EQ": ("quake", "⚡"), "TC": ("cyclone", "🌀"), "FL": ("flood", "🌊"),
              "VO": ("volcano", "🌋"), "DR": ("drought", "🏜️"), "WF": ("fire", "🔥"),
              "TS": ("tsunami", "🌊")}


def get_gdacs():
    """GDACS — Global Disaster Alert & Coordination System. Severity-scored (Green/Orange/Red)
    geolocated disasters: quakes, cyclones, floods, volcanoes, droughts. Keyless."""
    j = fetch("https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP", timeout=15)
    sev = {"Red": 3, "Orange": 2, "Green": 1}
    out = []
    for f in j.get("features", []):
        try:
            p = f.get("properties", {})
            g = f.get("geometry") or {}
            c = g.get("coordinates")
            lat = c[1] if c else p.get("latitude")
            lon = c[0] if c else p.get("longitude")
            if lat is None or lon is None:
                continue
            kind, icon = GDACS_TYPE.get(p.get("eventtype"), ("event", "📍"))
            out.append({"lat": round(float(lat), 3), "lon": round(float(lon), 3),
                        "kind": kind, "icon": icon, "alert": p.get("alertlevel"),
                        "sev": sev.get(p.get("alertlevel"), 1),
                        "name": (p.get("name") or p.get("htmldescription") or kind)[:90]})
        except Exception:
            continue
    out.sort(key=lambda e: e["sev"], reverse=True)
    return out


def get_space_weather():
    """NOAA SWPC planetary K-index (geomagnetic storm level 0-9).
    Feed is a list of dicts: {time_tag, Kp, a_running, station_count}."""
    j = fetch("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
    latest = j[-1]
    kp = float(latest["Kp"])
    levels = ["Quiet", "Quiet", "Quiet", "Unsettled", "Active",
              "Minor storm", "Moderate storm", "Strong storm", "Severe storm", "Extreme storm"]
    return {"kp": round(kp, 1), "level": levels[clamp(int(round(kp)), 0, 9)],
            "time": latest.get("time_tag")}


# Yahoo keyless chart API — reliable, gives true prior-close % change.
YAHOO = [("^GSPC", "spx", "S&P 500"), ("^IXIC", "ndq", "Nasdaq"),
         ("^DJI", "dji", "Dow"), ("^VIX", "vix", "VIX")]


def get_indices():
    out = []
    for ysym, tick, name in YAHOO:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
                   f"{urllib.parse.quote(ysym)}?interval=1d&range=1d")
            j = fetch(url)
            meta = j["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price is None or not prev:
                continue
            chg = (price - prev) / prev * 100
            out.append({"symbol": tick, "name": name,
                        "price": round(float(price), 2), "chg_pct": round(chg, 2)})
        except Exception:
            continue
    return out


# Trading dashboard: commodities, rates, dollar (Yahoo). Fed to the Macro/Trade lens + panels.
COMMODITIES = [("CL=F", "WTI Crude", "energy"), ("BZ=F", "Brent", "energy"),
               ("NG=F", "Nat Gas", "energy"), ("GC=F", "Gold", "metals"),
               ("SI=F", "Silver", "metals"), ("HG=F", "Copper", "metals"),
               ("ZW=F", "Wheat", "agri"), ("ZC=F", "Corn", "agri"),
               ("ZS=F", "Soybean", "agri"), ("^TNX", "US 10Y", "rates"),
               ("DX-Y.NYB", "Dollar", "rates")]


def get_commodities():
    out = []
    for ysym, name, grp in COMMODITIES:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
                   f"{urllib.parse.quote(ysym)}?interval=1d&range=1d")
            j = fetch(url)
            meta = j["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price is None or not prev:
                continue
            out.append({"name": name, "group": grp, "price": round(float(price), 2),
                        "chg_pct": round((price - prev) / prev * 100, 2)})
        except Exception:
            continue
    return out


def get_crypto():
    try:
        url = ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana"
               "&vs_currencies=usd&include_24hr_change=true")
        j = fetch(url)
        m = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
        out = []
        for cid, tick in m.items():
            d = j.get(cid, {})
            if "usd" in d:
                out.append({"symbol": tick, "name": cid.capitalize(),
                            "price": round(d["usd"], 2),
                            "chg_pct": round(d.get("usd_24h_change", 0.0), 2)})
        return out
    except Exception:
        return []


def get_iss():
    try:
        j = fetch("http://api.open-notify.org/iss-now.json")
        p = j["iss_position"]
        return {"lat": round(float(p["latitude"]), 2), "lon": round(float(p["longitude"]), 2)}
    except Exception:
        return None


def get_news_hotspots():
    """DISABLED: GDELT's geo API (/api/v2/geo/geo) was retired — returns 404. Kept as a no-op so the
    snapshot schema stays stable; wire a keyed news source here later if a geolocated feed is wanted."""
    return []


# ---------------------------------------------------------------- weather grid
def _grid(lon_step, lat_step, lat_span=78):
    pts = []
    lon = -180
    while lon < 180:
        lat = -lat_span
        while lat <= lat_span:
            pts.append((round(lat, 2), round(lon, 2)))
            lat += lat_step
        lon += lon_step
    return pts


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def get_weather_grid():
    """Open-Meteo global grid: current temperature + wind (speed/direction) + WMO code.
    Batched, threaded — one dead chunk never breaks the rest."""
    pts = _grid(12, 12)  # ~30 lon x 14 lat ≈ 420 points
    out = []

    def pull(chunk):
        lats = ",".join(str(a) for a, _ in chunk)
        lons = ",".join(str(b) for _, b in chunk)
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}"
               f"&current=temperature_2m,wind_speed_10m,wind_direction_10m,weather_code,"
               f"precipitation,cloud_cover,relative_humidity_2m,surface_pressure")
        j = fetch(url, timeout=20)
        rows = j if isinstance(j, list) else [j]
        res = []
        for r in rows:
            c = r.get("current", {})
            if c.get("temperature_2m") is None:
                continue
            res.append({"lat": round(r["latitude"], 2), "lon": round(r["longitude"], 2),
                        "temp": round(c["temperature_2m"], 1),
                        "wind": round(c.get("wind_speed_10m", 0), 1),
                        "dir": round(c.get("wind_direction_10m", 0), 1),
                        "code": c.get("weather_code"),
                        "precip": round(c.get("precipitation") or 0, 2),
                        "cloud": int(c.get("cloud_cover") or 0),
                        "humidity": int(c.get("relative_humidity_2m") or 0),
                        "pressure": round(c.get("surface_pressure") or 0)})
        return res

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(pull, ch) for ch in _chunks(pts, 90)]
        for f in as_completed(futs):
            try:
                out.extend(f.result())
            except Exception:
                continue
    return out


def get_air_grid():
    """Open-Meteo air-quality grid: PM2.5 + US AQI (coarser than weather)."""
    pts = _grid(20, 18, lat_span=72)  # ~18 lon x 9 lat
    out = []

    def pull(chunk):
        lats = ",".join(str(a) for a, _ in chunk)
        lons = ",".join(str(b) for _, b in chunk)
        url = (f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lats}"
               f"&longitude={lons}&current=pm2_5,us_aqi")
        j = fetch(url, timeout=20)
        rows = j if isinstance(j, list) else [j]
        res = []
        for r in rows:
            c = r.get("current", {})
            if c.get("us_aqi") is None:
                continue
            res.append({"lat": round(r["latitude"], 2), "lon": round(r["longitude"], 2),
                        "aqi": int(c["us_aqi"]), "pm25": round(c.get("pm2_5") or 0, 1)})
        return res

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(pull, ch) for ch in _chunks(pts, 80)]
        for f in as_completed(futs):
            try:
                out.extend(f.result())
            except Exception:
                continue
    return out


# Major aviation hubs — regional adsb.lol pulls stitched into a global flight picture.
FLIGHT_HUBS = [
    (40.7, -74.0), (34.0, -118.2), (41.9, -87.6), (51.5, -0.1), (50.0, 8.6),
    (48.8, 2.4), (40.4, -3.7), (25.2, 55.3), (35.7, 139.7), (1.35, 103.8),
    (28.6, 77.2), (22.3, 114.2), (39.9, 116.4), (-23.5, -46.6), (-33.9, 151.2),
    (-26.2, 28.0), (55.7, 37.6), (41.0, 28.9), (19.4, -99.1), (6.5, 3.4),
    (33.6, -84.4), (32.9, -97.0), (13.7, 100.5), (-1.3, 36.8),
]


def _flight_row(a, mil=False):
    lat, lon = a.get("lat"), a.get("lon")
    if lat is None or lon is None:
        return None
    alt = a.get("alt_baro")
    if alt == "ground":
        alt = 0
    return {"lat": round(lat, 3), "lon": round(lon, 3),
            "alt": alt if isinstance(alt, (int, float)) else None,
            "flight": (a.get("flight") or "").strip() or None,
            "type": a.get("t"), "track": a.get("track"),
            "speed": a.get("gs"), "mil": mil}


def get_flights():
    """Live aircraft from adsb.lol: regional hub pulls + the global military feed, deduped.
    adsb.lol rate-limits heavy parallelism, so use a small pool with a short timeout — full
    counts come back reliably, and any slow/limited hub is simply skipped."""
    seen = {}

    def ingest(aircraft, mil=False):
        for a in aircraft or []:
            hexid = a.get("hex")
            if not hexid:
                continue
            row = _flight_row(a, mil=mil)
            if row and (mil or hexid not in seen):
                seen[hexid] = row  # military flag always wins

    def pull(hub):
        lat, lon = hub
        return fetch(f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250", timeout=8).get("ac")

    # Global military feed first (its own request)
    try:
        ingest(fetch("https://api.adsb.lol/v2/mil", timeout=10).get("ac"), mil=True)
    except Exception:
        pass
    # Regional civil pulls — 3 at a time keeps under the rate limiter
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(pull, h): h for h in FLIGHT_HUBS}
        for f in as_completed(futs):
            try:
                ingest(f.result(), mil=False)
            except Exception:
                continue

    flights = list(seen.values())
    if len(flights) > 1100:  # keep the payload sane; sample evenly, keep all military
        mil = [f for f in flights if f["mil"]]
        civ = [f for f in flights if not f["mil"]]
        step = max(1, len(civ) // (1100 - len(mil)))
        flights = mil + civ[::step]
    return flights


# ---------------------------------------------------------------- satellites (TLE)
SAT_GROUPS = [("stations", 30), ("visual", 160), ("science", 50), ("weather", 80), ("gps-ops", 32)]


def _parse_tle(raw, group, cap):
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
        if not (l1.startswith("1 ") and l2.startswith("2 ")):
            continue
        sats.append({"name": name.strip(), "l1": l1, "l2": l2, "group": group})
    return sats[:cap] if cap else sats


def get_satellites():
    """Fetch classic 3-line TLEs from Celestrak for a curated set of groups. The globe page
    propagates these live with satellite.js (SGP4). Starlink is big, so it gets its own longer
    fetch and is sampled evenly to a few hundred."""
    out, seen = [], set()

    def pull(group, cap):
        raw = fetch(f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle",
                    parse="csv", timeout=20)
        return _parse_tle(raw, group, cap)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(pull, g, cap): g for g, cap in SAT_GROUPS}
        for f in as_completed(futs):
            try:
                for s in f.result():
                    if s["name"] not in seen:
                        seen.add(s["name"])
                        out.append(s)
            except Exception:
                continue

    # Starlink — dedicated fetch (big file; the GROUP endpoint 403s, supplemental works), sampled ~280
    try:
        raw = fetch("https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink"
                    "&FORMAT=tle", parse="csv", timeout=45)
        sl = _parse_tle(raw, "starlink", None)
        step = max(1, len(sl) // 1500)
        for s in sl[::step][:1500]:
            if s["name"] not in seen:
                seen.add(s["name"])
                out.append(s)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- stress index
def compute_stress(quakes, hazards, space, indices, crypto):
    """Transparent 0-100 Global Stress Index with visible components."""
    comp = {}
    # Seismic: significant quakes in the last day (mag>=4.5), log-weighted by magnitude
    sig = [q for q in quakes if q["mag"] >= 4.5]
    seismic = sum((q["mag"] - 4.0) ** 1.6 for q in sig)
    comp["seismic"] = round(clamp(seismic / 40 * 100, 0, 100), 1)
    # Hazards: count of open natural events, saturating ~120
    comp["hazards"] = round(clamp(len(hazards) / 120 * 100, 0, 100), 1)
    # Space weather: Kp 0-9 → 0-100
    kp = space.get("kp", 0) if space else 0
    comp["space"] = round(clamp(kp / 9 * 100, 0, 100), 1)
    # Market stress: VIX level + average absolute move across indices & crypto
    vix = next((i["price"] for i in indices if i["symbol"] == "vix"), None)
    moves = [abs(i["chg_pct"]) for i in indices] + [abs(c["chg_pct"]) for c in crypto]
    avg_move = sum(moves) / len(moves) if moves else 0
    vix_score = clamp(((vix or 15) - 12) / 30 * 100, 0, 100)
    market = 0.6 * vix_score + 0.4 * clamp(avg_move / 6 * 100, 0, 100)
    comp["market"] = round(market, 1)
    # Weighted blend
    w = {"seismic": 0.25, "hazards": 0.2, "space": 0.15, "market": 0.4}
    score = sum(comp[k] * w[k] for k in w)
    score = round(clamp(score, 0, 100), 1)
    if score < 25:
        band = "Calm"
    elif score < 45:
        band = "Elevated"
    elif score < 65:
        band = "Tense"
    else:
        band = "Critical"
    return {"score": score, "band": band, "components": comp, "weights": w}


def build_feed(quakes, hazards, space, news):
    """Unified reverse-chronological event ticker."""
    feed = []
    for q in quakes[:12]:
        feed.append({"t": q.get("time"), "icon": "⚡", "kind": "quake",
                     "text": f"M{q['mag']} earthquake — {q['place']}"})
    for h in hazards[:12]:
        ts = None
        try:
            ts = int(datetime.datetime.fromisoformat(
                h["date"].replace("Z", "+00:00")).timestamp() * 1000) if h.get("date") else None
        except Exception:
            ts = None
        feed.append({"t": ts, "icon": h["icon"], "kind": h["kind"], "text": h["title"]})
    if space and space.get("kp", 0) >= 5:
        feed.append({"t": None, "icon": "☀️", "kind": "space",
                     "text": f"Geomagnetic {space['level']} (Kp {space['kp']})"})
    for n in news[:8]:
        feed.append({"t": None, "icon": "📰", "kind": "news",
                     "text": f"News cluster — {n['name']} ({n['count']})"})
    feed.sort(key=lambda x: (x["t"] or 0), reverse=True)
    return feed[:40]


RATES = [("^IRX", "3mo"), ("^FVX", "5y"), ("^TNX", "10y"), ("^TYX", "30y")]


def get_rates():
    """US Treasury yield LEVELS (Yahoo) + 10y-3mo curve spread + DXY — macro/risk signals."""
    def yprice(sym):
        j = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=1d")
        return j["chart"]["result"][0]["meta"].get("regularMarketPrice")
    out = {}
    for ysym, tick in RATES:
        try:
            p = yprice(ysym)
            if p is not None:
                out[tick] = round(float(p), 3)
        except Exception:
            continue
    try:
        p = yprice("DX-Y.NYB")
        if p is not None:
            out["dxy"] = round(float(p), 2)
    except Exception:
        pass
    if "10y" in out and "3mo" in out:
        out["curve_10y_3mo"] = round(out["10y"] - out["3mo"], 3)
    if not out:
        raise RuntimeError("no rate data")
    return out


def get_fear_greed():
    """Crypto Fear & Greed index (0-100), keyless (alternative.me)."""
    d = fetch("https://api.alternative.me/fng/?limit=1")["data"][0]
    return {"value": int(d["value"]), "label": d.get("value_classification")}


def get_solar_wind():
    """NOAA SWPC real-time solar wind (DSCOVR): bulk speed + IMF Bz/Bt (last valid sample)."""
    out = {}
    try:
        p = fetch("https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json")
        for row in reversed(p[1:]):
            try:
                out["speed_kms"] = round(float(row[2])); break
            except (TypeError, ValueError, IndexError):
                continue
    except Exception:
        pass
    try:
        m = fetch("https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json")
        for row in reversed(m[1:]):
            try:
                out["bz_nt"] = round(float(row[3]), 1); out["bt_nt"] = round(float(row[6]), 1); break
            except (TypeError, ValueError, IndexError):
                continue
    except Exception:
        pass
    if not out:
        raise RuntimeError("no solar-wind data")
    return out


def get_hamqsl():
    """HamQSL solar/propagation XML — SFI, sunspots, A/K, aurora, HF band conditions (ham radio)."""
    import xml.etree.ElementTree as ET
    sd = ET.fromstring(fetch("https://www.hamqsl.com/solarxml.php", parse="text")).find("solardata")
    if sd is None:
        raise RuntimeError("no solardata")

    def g(tag):
        e = sd.find(tag)
        return (e.text or "").strip() if e is not None and e.text else None

    def gf(tag):
        try:
            return float(g(tag))
        except (TypeError, ValueError):
            return None
    bands = {}
    cc = sd.find("calculatedconditions")
    if cc is not None:
        for b in cc.findall("band"):
            bands["%s_%s" % (b.get("name"), b.get("time"))] = (b.text or "").strip()
    hf_good = sum(1 for v in bands.values() if v.lower() == "good")
    return {"sfi": gf("solarflux"), "sunspots": gf("sunspots"), "aindex": gf("aindex"),
            "kindex": gf("kindex"), "aurora": gf("aurora"), "solarwind": gf("solarwind"),
            "xray": g("xray"), "magfield": g("magneticfield"), "bands": bands,
            "hf_good": hf_good, "updated": g("updated")}


def main():
    snap = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "sources": {}, "notes": [],
    }

    def run(name, fn, default):
        try:
            v = fn()
            snap["sources"][name] = "ok"
            return v
        except Exception as e:
            snap["sources"][name] = "error"
            snap["notes"].append(f"{name}: {e}")
            return default

    quakes = run("usgs", get_quakes, [])
    hazards = run("eonet", get_hazards, [])
    gdacs = run("gdacs", get_gdacs, [])
    space = run("noaa", get_space_weather, {})
    indices = run("markets", get_indices, [])
    commodities = run("commodities", get_commodities, [])
    crypto = run("coingecko", get_crypto, [])
    rates = run("rates", get_rates, {})
    fear_greed = run("fear_greed", get_fear_greed, {})
    solar_wind = run("solarwind", get_solar_wind, {})
    ham = run("hamqsl", get_hamqsl, {})
    iss = run("iss", get_iss, None)
    news = run("gdelt", get_news_hotspots, [])
    weather = run("openmeteo", get_weather_grid, [])
    air = run("airquality", get_air_grid, [])
    flights = run("adsb", get_flights, [])
    satellites = run("celestrak", get_satellites, [])
    sky = run("sky", sky.compute, {})

    snap["quakes"] = quakes
    snap["hazards"] = hazards
    snap["gdacs"] = gdacs
    snap["space_weather"] = space
    snap["indices"] = indices
    snap["commodities"] = commodities
    snap["crypto"] = crypto
    snap["rates"] = rates
    snap["fear_greed"] = fear_greed
    snap["solar_wind"] = solar_wind
    snap["ham"] = ham
    snap["iss"] = iss
    snap["news_hotspots"] = news
    snap["weather_grid"] = weather
    snap["air_grid"] = air
    snap["flights"] = flights
    snap["satellites"] = satellites
    snap["sky"] = sky
    snap["stress"] = compute_stress(quakes, hazards, space, indices, crypto)
    snap["feed"] = build_feed(quakes, hazards, space, news)

    temps = [w["temp"] for w in weather]
    winds = [w["wind"] for w in weather]
    aqis = [a["aqi"] for a in air]
    snap["globals"] = {
        "avg_temp_c": round(sum(temps) / len(temps), 1) if temps else None,
        "max_temp_c": max(temps) if temps else None,
        "min_temp_c": min(temps) if temps else None,
        "max_wind_kmh": max(winds) if winds else None,
        "avg_aqi": round(sum(aqis) / len(aqis)) if aqis else None,
        "max_aqi": max(aqis) if aqis else None,
        "flights_tracked": len(flights),
        "military_aircraft": len([f for f in flights if f.get("mil")]),
    }
    snap["counts"] = {
        "quakes_24h": len(quakes),
        "quakes_sig": len([q for q in quakes if q["mag"] >= 4.5]),
        "hazards": len(hazards),
        "news_clusters": len(news),
        "weather_pts": len(weather),
        "air_pts": len(air),
        "flights": len(flights),
        "satellites": len(satellites),
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, default=str)
    ok = [k for k, v in snap["sources"].items() if v == "ok"]
    print(f"wrote {OUT} — sources ok: {', '.join(ok) or 'none'} | "
          f"quakes={len(quakes)} hazards={len(hazards)} weather={len(weather)} "
          f"air={len(air)} flights={len(flights)} stress={snap['stress']['score']}")


if __name__ == "__main__":
    main()
