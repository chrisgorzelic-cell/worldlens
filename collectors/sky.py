#!/usr/bin/env python3
"""Worldlens sky engine — deterministic, keyless astronomy. Computes geocentric ecliptic
longitudes (→ tropical zodiac sign + degree), retrograde state, RA/Dec and distance for the
Sun, Moon and planets, plus Moon phase/illumination. Method: JPL "Approximate Positions of the
Planets" (Keplerian elements) + a truncated Meeus lunar series. Pure stdlib (math + datetime)."""
import math, datetime

D2R = math.pi / 180.0
R2D = 180.0 / math.pi
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋", "Leo": "♌",
              "Virgo": "♍", "Libra": "♎", "Scorpio": "♏", "Sagittarius": "♐",
              "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}
PLANET_GLYPH = {"Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
                "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"}

# a, e, I, L, longPeri(ϖ), longNode(Ω) at J2000 and per-century rates (Standish 1800–2050).
ELEMENTS = {
    "Mercury": [0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593,
                0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081],
    "Venus":   [0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255,
                0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418],
    "Earth":   [1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0,
                0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0],
    "Mars":    [1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891,
                0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343],
    "Jupiter": [5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909,
                -0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106],
    "Saturn":  [9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448,
                -0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794],
    "Uranus":  [19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503,
                -0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589],
    "Neptune": [30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574,
                0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664],
}
PLANETS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]


def julian_day(dt):
    y, m = dt.year, dt.month
    d = (dt.day + dt.hour / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0)
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _norm360(x):
    return x % 360.0


def _kepler(M_deg, e):
    M = _norm360(M_deg)
    if M > 180:
        M -= 360
    M *= D2R
    E = M + e * math.sin(M)
    for _ in range(8):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-8:
            break
    return E


def _helio_ecliptic(name, T):
    """Heliocentric ecliptic (J2000) rectangular coords for a planet at time T (centuries)."""
    a0, e0, I0, L0, w0, O0, da, de, dI, dL, dw, dO = ELEMENTS[name]
    a = a0 + da * T
    e = e0 + de * T
    I = (I0 + dI * T) * D2R
    L = L0 + dL * T
    wbar = w0 + dw * T
    O = (O0 + dO * T) * D2R
    w = (wbar - (O0 + dO * T)) * D2R  # argument of perihelion (rad)
    M = L - wbar
    E = _kepler(M, e)
    xp = a * (math.cos(E) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(E)
    cw, sw = math.cos(w), math.sin(w)
    cO, sO = math.cos(O), math.sin(O)
    cI, sI = math.cos(I), math.sin(I)
    x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp
    y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp
    z = (sw * sI) * xp + (cw * sI) * yp
    return x, y, z


def _precession(T):
    # general precession in longitude since J2000, degrees (approx)
    return 1.396971 * T + 0.0003086 * T * T


def _ecl_to_radec(lon_deg, lat_deg, T):
    eps = (23.439291 - 0.0130042 * T) * D2R
    lon, lat = lon_deg * D2R, lat_deg * D2R
    sl, cl = math.sin(lon), math.cos(lon)
    sb, cb = math.sin(lat), math.cos(lat)
    se, ce = math.sin(eps), math.cos(eps)
    ra = math.atan2(sl * ce - (sb / cb if cb else 0) * se, cl) if cb else math.atan2(sl * ce, cl)
    # robust RA/Dec
    x = cl * cb
    y = sl * cb * ce - sb * se
    z = sl * cb * se + sb * ce
    ra = _norm360(math.atan2(y, x) * R2D)
    dec = math.asin(max(-1, min(1, z))) * R2D
    return ra, dec


def _sign(lon):
    lon = _norm360(lon)
    idx = int(lon // 30)
    return SIGNS[idx], round(lon - idx * 30, 1)


def _geocentric_lonlat(name, T):
    xe, ye, ze = _helio_ecliptic("Earth", T)
    if name == "Sun":
        xg, yg, zg = -xe, -ye, -ze
    else:
        xp, yp, zp = _helio_ecliptic(name, T)
        xg, yg, zg = xp - xe, yp - ye, zp - ze
    lon = _norm360(math.atan2(yg, xg) * R2D + _precession(T))
    lat = math.atan2(zg, math.sqrt(xg * xg + yg * yg)) * R2D
    dist = math.sqrt(xg * xg + yg * yg + zg * zg)
    return lon, lat, dist


def _moon(T):
    """Truncated Meeus (ch. 47) — geocentric ecliptic longitude/latitude of the Moon (of date)."""
    Lp = _norm360(218.3164477 + 481267.88123421 * T)
    D = _norm360(297.8501921 + 445267.1114034 * T)
    M = _norm360(357.5291092 + 35999.0502909 * T)
    Mp = _norm360(134.9633964 + 477198.8675055 * T)
    F = _norm360(93.2720950 + 483202.0175233 * T)
    d, m, mp, f = D * D2R, M * D2R, Mp * D2R, F * D2R
    lon = Lp + (6.288774 * math.sin(mp) + 1.274027 * math.sin(2 * d - mp)
                + 0.658314 * math.sin(2 * d) + 0.213618 * math.sin(2 * mp)
                - 0.185116 * math.sin(m) - 0.114332 * math.sin(2 * f)
                + 0.058793 * math.sin(2 * d - 2 * mp) + 0.057066 * math.sin(2 * d - m - mp)
                + 0.053322 * math.sin(2 * d + mp) + 0.045758 * math.sin(2 * d - m)
                - 0.040923 * math.sin(m - mp) - 0.034720 * math.sin(d)
                - 0.030383 * math.sin(m + mp))
    lat = (5.128122 * math.sin(f) + 0.280602 * math.sin(mp + f)
           + 0.277693 * math.sin(mp - f) + 0.173237 * math.sin(2 * d - f)
           + 0.055413 * math.sin(2 * d - mp + f) + 0.046271 * math.sin(2 * d - mp - f))
    return _norm360(lon), lat


def compute(dt=None):
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    jd = julian_day(dt)
    T = (jd - 2451545.0) / 36525.0
    T2 = (jd + 1 - 2451545.0) / 36525.0  # +1 day, for retrograde detection

    def body(name):
        lon, lat, dist = _geocentric_lonlat(name, T)
        ra, dec = _ecl_to_radec(lon, lat, T)
        sign, deg = _sign(lon)
        entry = {"name": name, "glyph": PLANET_GLYPH.get(name, "•"),
                 "lon": round(lon, 2), "sign": sign, "sign_glyph": SIGN_GLYPH[sign],
                 "deg": deg, "ra": round(ra, 2), "dec": round(dec, 2),
                 "dist_au": round(dist, 3)}
        if name not in ("Sun",):
            lon2, _, _ = _geocentric_lonlat(name, T2)
            diff = (lon2 - lon + 540) % 360 - 180
            entry["retro"] = diff < 0
        return entry

    planets = [body("Sun")] + [body(p) for p in PLANETS]

    # Moon
    mlon, mlat = _moon(T)
    mra, mdec = _ecl_to_radec(mlon, mlat, T)
    msign, mdeg = _sign(mlon)
    slon = planets[0]["lon"]
    elong = _norm360(mlon - slon)
    illum = round((1 - math.cos(elong * D2R)) / 2 * 100)
    phases = [(20, "New Moon", "🌑"), (70, "Waxing Crescent", "🌒"), (110, "First Quarter", "🌓"),
              (160, "Waxing Gibbous", "🌔"), (200, "Full Moon", "🌕"), (250, "Waning Gibbous", "🌖"),
              (290, "Last Quarter", "🌗"), (340, "Waning Crescent", "🌘"), (361, "New Moon", "🌑")]
    pname, pemoji = next((n, e) for lim, n, e in phases if elong < lim)
    moon = {"name": "Moon", "glyph": "☽", "lon": round(mlon, 2), "sign": msign,
            "sign_glyph": SIGN_GLYPH[msign], "deg": mdeg, "ra": round(mra, 2), "dec": round(mdec, 2),
            "phase": pname, "phase_emoji": pemoji, "illum": illum, "retro": False}

    return {"updated": dt.isoformat(timespec="seconds"),
            "sun": planets[0], "moon": moon, "planets": planets + [moon],
            "obliquity": round(23.439291 - 0.0130042 * T, 3)}


if __name__ == "__main__":
    sky = compute()
    print("Sun:", sky["sun"]["sign"], sky["sun"]["deg"], "°  (lon", sky["sun"]["lon"], ")")
    print("Moon:", sky["moon"]["sign"], sky["moon"]["deg"], "°",
          sky["moon"]["phase"], sky["moon"]["phase_emoji"], sky["moon"]["illum"], "%")
    for p in sky["planets"][1:-1]:
        print(f"  {p['glyph']} {p['name']:8} {p['sign_glyph']} {p['sign']:12} {p['deg']:5}°"
              f"  {'℞ retrograde' if p.get('retro') else ''}  RA {p['ra']} Dec {p['dec']}")
