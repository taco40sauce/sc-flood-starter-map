"""
sc_flood_now.py — builds the live files for the South Carolina flood starter
maps: one statewide map and one map for each of the six SC ARES districts.

Each run reads two public, official sources:
  1. National Weather Service: active Flood Warnings, Flash Flood Warnings,
     Flood Watches and Flash Flood Watches for South Carolina
  2. SCDOT road conditions: closures caused by flooding, washouts, trees or
     power lines, for all 46 counties (planned work zones are skipped)

It writes, for the state ("sc") and each district ("d1" ... "d6"):
  out/<area>/warnings.geojson   flood warning areas (clipped to the area)
  out/<area>/watches.geojson    flood watch areas (clipped to the area)
  out/<area>/closures.geojson   SCDOT storm closures (red pins)
  out/<area>/outline.geojson    county lines and the area's outer edge

Alerts are matched to districts by the county codes NWS includes with every
alert, and SCDOT closures by their county name. County and district outlines
come from NWS county zone shapes; they are fetched once and saved in data/.

No people-entered data is used here. Districts and counties that want local
road reports set up their own Grist doc and county map (see SETUP-GUIDE.md).

Run:  python3 sc_flood_now.py
"""
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = HERE / "data"
TIMEOUT = 60

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
NWS_ZONE_URL = "https://api.weather.gov/zones/county/SCC{fips}"
NWS_HEADERS = {"User-Agent": "sc-flood-starter-map (github.com/taco40sauce/sc-flood-starter-map)",
               "Accept": "application/geo+json"}
WARNING_EVENTS = ("Flash Flood Warning", "Flood Warning")
WATCH_EVENTS = ("Flood Watch", "Flash Flood Watch")

SCDOT_URL = "https://ris.scdot.org/roadconditions/"

# SC county FIPS codes (state 45). NWS alerts list counties as SAME codes "045" + FIPS.
COUNTY_FIPS = {
    "ABBEVILLE": "001", "AIKEN": "003", "ALLENDALE": "005", "ANDERSON": "007",
    "BAMBERG": "009", "BARNWELL": "011", "BEAUFORT": "013", "BERKELEY": "015",
    "CALHOUN": "017", "CHARLESTON": "019", "CHEROKEE": "021", "CHESTER": "023",
    "CHESTERFIELD": "025", "CLARENDON": "027", "COLLETON": "029", "DARLINGTON": "031",
    "DILLON": "033", "DORCHESTER": "035", "EDGEFIELD": "037", "FAIRFIELD": "039",
    "FLORENCE": "041", "GEORGETOWN": "043", "GREENVILLE": "045", "GREENWOOD": "047",
    "HAMPTON": "049", "HORRY": "051", "JASPER": "053", "KERSHAW": "055",
    "LANCASTER": "057", "LAURENS": "059", "LEE": "061", "LEXINGTON": "063",
    "MCCORMICK": "065", "MARION": "067", "MARLBORO": "069", "NEWBERRY": "071",
    "OCONEE": "073", "ORANGEBURG": "075", "PICKENS": "077", "RICHLAND": "079",
    "SALUDA": "081", "SPARTANBURG": "083", "SUMTER": "085", "UNION": "087",
    "WILLIAMSBURG": "089", "YORK": "091",
}

# SC ARES districts (from the ARES-SC leadership directory, Oct 2026).
DISTRICTS = {
    "d1": ["ABBEVILLE", "ANDERSON", "EDGEFIELD", "GREENVILLE", "GREENWOOD", "MCCORMICK",
           "OCONEE", "PICKENS"],
    "d2": ["CHEROKEE", "CHESTER", "LANCASTER", "LAURENS", "SPARTANBURG", "UNION", "YORK"],
    "d3": ["CALHOUN", "FAIRFIELD", "KERSHAW", "LEXINGTON", "NEWBERRY", "RICHLAND", "SALUDA"],
    "d4": ["CHESTERFIELD", "DARLINGTON", "DILLON", "FLORENCE", "HORRY", "LEE", "MARION",
           "MARLBORO"],
    "d5": ["BERKELEY", "CHARLESTON", "CLARENDON", "DORCHESTER", "GEORGETOWN", "ORANGEBURG",
           "SUMTER", "WILLIAMSBURG"],
    "d6": ["AIKEN", "ALLENDALE", "BAMBERG", "BARNWELL", "BEAUFORT", "COLLETON", "HAMPTON",
           "JASPER"],
}
AREAS = {"sc": sorted(COUNTY_FIPS), **DISTRICTS}

# --- SCDOT wording (same rules as the Kershaw County flood map) -----------------
ROAD_CAUSES = {"FL": "flooding", "BR": "bridge or washout damage",
               "TR": "trees or debris down", "PL": "power lines down"}
CAUSE_PATTERNS = [
    ("FL", re.compile(r"flood|high water|water over|water on (the )?road|under ?water|inundat|"
                      r"standing water|ponding|dam (failure|breach)", re.I)),
    ("BR", re.compile(r"wash ?out|washed out|sinkhole|undermin|collaps|"
                      r"bridge (is )?(out|damaged|failure)|culvert (failure|failed|collaps)", re.I)),
    ("PL", re.compile(r"power ?lines?|lines? down|wires? down|downed (power )?lines?", re.I)),
    ("TR", re.compile(r"\btrees?\b|debris|\blimbs?\b|downed", re.I)),
]
SCDOT_PLANNED_WORK = re.compile(
    r"resurfac|replac|repair|install|construct|paving|patching|inspection|storm drain|"
    r"water ?line|sewer|maintenance|widening|utility|striping|roundabout|rest area|shoulder work|"
    r"shoulder closure|contractor|asphalt|operating under|stations? \d+\+\d+",
    re.I)
SCDOT_STATUS = {"Closed": "Road closed", "Lane(s) blocked": "Partly blocked", "Caution": "Use caution"}


# --- Helpers -----------------------------------------------------------------------
def get(url, **params):
    r = requests.get(url, params=params or None, headers=NWS_HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def fc(features):
    return {"type": "FeatureCollection", "features": features}


def write_if_changed(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def not_expired(feature):
    exp = feature.get("properties", {}).get("expires", "")
    try:
        return datetime.fromisoformat(exp) > datetime.now(timezone.utc)
    except ValueError:
        return True


# --- County and district outlines (fetched once, saved in data/) ----------------
def load_outlines():
    """Return {county: shape} and {area: shape}. Builds data/*.geojson on first run."""
    counties_file = DATA / "counties.geojson"
    if not counties_file.exists():
        feats = []
        for name, fips in sorted(COUNTY_FIPS.items()):
            z = get(NWS_ZONE_URL.format(fips=fips)).json()
            # Some NWS zone shapes arrive as a collection of pieces; buffer(0)
            # turns them into one standard (multi)polygon.
            geom = shape(z["geometry"]).buffer(0).simplify(0.001, preserve_topology=True)
            feats.append({"type": "Feature", "geometry": mapping(geom),
                          "properties": {"name": name.title().replace("Mccormick", "McCormick"),
                                         "county": name, "fips": "45" + fips}})
        write_if_changed(counties_file, fc(feats))
        print(f"[outlines] built data/counties.geojson ({len(feats)} counties)")
    counties = {f["properties"]["county"]: shape(f["geometry"]).buffer(0)
                for f in json.loads(counties_file.read_text())["features"]}
    areas = {area: unary_union([counties[c] for c in names]).buffer(0)
             for area, names in AREAS.items()}
    return counties, areas


def outline_features(area, geom, counties):
    """County lines (thin) plus the area's outer edge (thicker)."""
    label = "South Carolina" if area == "sc" else f"SC ARES District {area[1:]}"
    names = ", ".join(n.title().replace("Mccormick", "McCormick") for n in AREAS[area])
    feats = [{"type": "Feature",
              "geometry": mapping(counties[c].boundary.simplify(0.002)),
              "properties": {"name": f"{c.title().replace('Mccormick', 'McCormick')} County",
                             "_umap_options": {"weight": 1, "opacity": 0.5}}}
             for c in AREAS[area]]
    feats.append({"type": "Feature", "geometry": mapping(geom.boundary.simplify(0.002)),
                  "properties": {"name": label, "counties": names,
                                 "_umap_options": {"weight": 3, "opacity": 0.8}}})
    return feats


# --- NWS alerts ----------------------------------------------------------------------
def fetch_alerts(events):
    data = get(NWS_ALERTS_URL, area="SC", event=",".join(events)).json()
    zone_cache, alerts = {}, []
    for f in data.get("features", []):
        p = f.get("properties", {})
        geom = shape(f["geometry"]) if f.get("geometry") else None
        if geom is None:
            parts = []
            for url in p.get("affectedZones", []):
                if url not in zone_cache:
                    try:
                        z = get(url).json()
                        zone_cache[url] = shape(z["geometry"]) if z.get("geometry") else None
                    except Exception as exc:
                        print(f"[nws] zone {url} failed: {exc}")
                        zone_cache[url] = None
                if zone_cache[url] is not None:
                    parts.append(zone_cache[url])
            geom = unary_union(parts) if parts else None
        if geom is None or geom.is_empty:
            continue
        same = [c for c in p.get("geocode", {}).get("SAME", []) if c.startswith("045")]
        alerts.append({"geometry": geom.buffer(0), "same": {c[3:] for c in same},
                       "props": {"name": p.get("event", ""), "event": p.get("event", ""),
                                 "headline": p.get("headline") or "",
                                 "expires": p.get("ends") or p.get("expires") or "",
                                 "area": p.get("areaDesc", ""),
                                 "instruction": (p.get("instruction") or "").strip()}})
    return alerts


def alerts_for_area(alerts, area, area_geom):
    fips = {COUNTY_FIPS[c] for c in AREAS[area]}
    feats = []
    for a in alerts:
        if a["same"] and not (a["same"] & fips) and area != "sc":
            continue
        clipped = a["geometry"].intersection(area_geom)
        if clipped.is_empty:
            continue
        feats.append({"type": "Feature",
                      "geometry": mapping(clipped.simplify(0.002, preserve_topology=True)),
                      "properties": a["props"]})
    return feats


# --- SCDOT ------------------------------------------------------------------------------
def cause_from_text(text):
    for code, pattern in CAUSE_PATTERNS:
        if pattern.search(text or ""):
            return code
    return None


def _field(pm, label):
    m = re.search(r"<b>" + re.escape(label) + r":</b>(.*?)<br", pm, re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""


def parse_scdot_kml(text):
    """Storm-damage closures from SCDOT's road-conditions KML, statewide.
    One condition can span several Placemarks; they are grouped and pinned at
    the middle of the whole stretch."""
    groups = {}
    tally = {"entries": 0, "county": 0, "status": 0, "not_planned": 0, "storm": 0}
    for raw_pm in re.findall(r"<Placemark\b.*?</Placemark>", text, re.S):
        tally["entries"] += 1
        # The live feed may send the description's formatting encoded
        # (&lt;b&gt;County:&lt;/b&gt;) or wrapped in CDATA; decode both so the
        # fields can be read either way. Plain text is left unchanged.
        pm = html.unescape(raw_pm.replace("<![CDATA[", "").replace("]]>", ""))
        county = re.sub(r"\s+COUNTY$", "", _field(pm, "County").upper()).strip()
        if county not in COUNTY_FIPS:
            continue
        tally["county"] += 1
        style = (re.search(r"<styleUrl>#(.*?)</styleUrl>", pm) or [None, ""])[1]
        if style not in SCDOT_STATUS:
            continue
        tally["status"] += 1
        m = re.search(r"<b>Description:</b>(.*?)(?:<br/>GPS:|</span></p>|$)", pm, re.S)
        desc = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()) if m else ""
        if SCDOT_PLANNED_WORK.search(desc):
            continue
        tally["not_planned"] += 1
        cause = cause_from_text(desc)
        if not cause:
            continue
        tally["storm"] += 1
        coords = []
        for block in re.findall(r"<coordinates>(.*?)</coordinates>", pm, re.S):
            for triple in block.split():
                parts = triple.split(",")
                if len(parts) >= 2:
                    try:
                        coords.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        pass
        if not coords:
            continue
        key = re.search(r'<Placemark id="([^"]*)"', pm)
        key = key.group(1) if key else (_field(pm, "Road Name") + desc)
        g = groups.setdefault(key, {"pm": pm, "desc": desc, "style": style, "cause": cause,
                                    "county": county, "coords": []})
        g["coords"].extend(coords)

    feats = []
    for g in groups.values():
        pm = g["pm"]
        lon, lat = g["coords"][len(g["coords"]) // 2]
        road = _field(pm, "Road Name") or _field(pm, "Route")
        span = re.search(r"<br/><br/>(From .*?)<br/>", pm, re.S)
        location = road + (f": {html.unescape(span.group(1)).strip()}" if span else "")
        since = re.search(r"(\d{2}/\d{2}/\d{4})\s*-", pm)
        detail = g["desc"].split(" . ", 1)[-1].strip()
        county = g["county"].title().replace("Mccormick", "McCormick")
        lines = [f"**{location}**", f"{county} County"]
        if detail:
            lines.append(detail)
        if since:
            lines.append(f"Since {since.group(1)}")
        lines.append("Source: SCDOT road conditions")
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                      "properties": {"name": f"{SCDOT_STATUS[g['style']]}: {ROAD_CAUSES[g['cause']]}",
                                     "county": g["county"], "description": "\n".join(lines)}})
    feats.sort(key=lambda f: (f["properties"]["county"], f["properties"]["name"]))
    print(f"[scdot] read {tally['entries']} entries: {tally['county']} with an SC county, "
          f"{tally['status']} closed/blocked/caution, {tally['not_planned']} not planned work, "
          f"{tally['storm']} storm damage")
    return feats


# --- Main ---------------------------------------------------------------------------------
def main():
    counties, areas = load_outlines()

    try:
        warnings = fetch_alerts(WARNING_EVENTS)
        watches = fetch_alerts(WATCH_EVENTS)
        nws_ok = True
        print(f"[nws] {len(warnings)} warnings, {len(watches)} watches in SC")
    except Exception as exc:
        nws_ok = False
        print(f"[nws] FAILED ({exc}); keeping last files, minus anything expired")

    try:
        r = requests.get(SCDOT_URL, timeout=TIMEOUT)
        entries = len(re.findall(r"<Placemark\b", r.text))
        print(f"[scdot] response {r.status_code}, {len(r.text):,} characters, "
              f"{entries} entries before filtering")
        first = re.search(r"<Placemark\b.*?</Placemark>", r.text, re.S)
        if first:
            sample = re.sub(r"\s+", " ", first.group(0))[:500]
            print(f"[scdot] sample entry: {sample}")
        r.raise_for_status()
        closures = parse_scdot_kml(r.text)
        scdot_ok = True
        print(f"[scdot] {len(closures)} storm closures statewide")
    except Exception as exc:
        scdot_ok = False
        print(f"[scdot] FAILED ({exc}); keeping last closures files")

    for area, geom in areas.items():
        folder = OUT / area
        write_if_changed(folder / "outline.geojson", fc(outline_features(area, geom, counties)))
        for kind, alerts in (("warnings", warnings if nws_ok else None),
                             ("watches", watches if nws_ok else None)):
            path = folder / f"{kind}.geojson"
            if alerts is not None:
                data = fc(alerts_for_area(alerts, area, geom))
            else:
                old = json.loads(path.read_text()) if path.exists() else fc([])
                data = fc([f for f in old["features"] if not_expired(f)])
            write_if_changed(path, data)
        if scdot_ok:
            names = set(AREAS[area])
            write_if_changed(folder / "closures.geojson",
                             fc([f for f in closures if f["properties"]["county"] in names]))
        elif not (folder / "closures.geojson").exists():
            write_if_changed(folder / "closures.geojson", fc([]))
        counts = {k: len(json.loads((folder / f"{k}.geojson").read_text())["features"])
                  for k in ("warnings", "watches", "closures")}
        print(f"[{area}] warnings {counts['warnings']}, watches {counts['watches']}, "
              f"closures {counts['closures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
