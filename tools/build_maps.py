"""
build_maps.py — builds the uMap import files in maps/: one statewide starter
map and one map for each SC ARES district. Every layer reads a live file from
this repo, so the maps never need rebuilding when warnings or closures change.

Run from the repo root:  python3 tools/build_maps.py
Then import a file into uMap (see README).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "maps"

GITHUB_REPO = "taco40sauce/sc-flood-starter-map"
RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/out"
KERSHAW_MAP = "https://umap.openstreetmap.fr/en/map/kershaw-county-flood-trouble-spots_1471681"
GUIDE = f"https://github.com/{GITHUB_REPO}/blob/main/SETUP-GUIDE.md"
CREDIT = "Starter map by KC4RC / Kershaw County ARES."

RED = "#d7191c"
OUTLINE = "#555555"

# area: (map name, center lon/lat, zoom, county list)
AREAS = {
    "sc": ("South Carolina Flood Trouble Spots", [-80.9, 33.85], 7,
           "all 46 counties"),
    "d1": ("SC ARES District 1 Flood Trouble Spots", [-82.35, 34.45], 9,
           "Abbeville, Anderson, Edgefield, Greenville, Greenwood, McCormick, Oconee, Pickens"),
    "d2": ("SC ARES District 2 Flood Trouble Spots", [-81.45, 34.75], 9,
           "Cherokee, Chester, Lancaster, Laurens, Spartanburg, Union, York"),
    "d3": ("SC ARES District 3 Flood Trouble Spots", [-81.15, 34.05], 9,
           "Calhoun, Fairfield, Kershaw, Lexington, Newberry, Richland, Saluda"),
    "d4": ("SC ARES District 4 Flood Trouble Spots", [-79.75, 34.3], 9,
           "Chesterfield, Darlington, Dillon, Florence, Horry, Lee, Marion, Marlboro"),
    "d5": ("SC ARES District 5 Flood Trouble Spots", [-80.1, 33.25], 9,
           "Berkeley, Charleston, Clarendon, Dorchester, Georgetown, Orangeburg, Sumter, Williamsburg"),
    "d6": ("SC ARES District 6 Flood Trouble Spots", [-81.0, 32.95], 9,
           "Aiken, Allendale, Bamberg, Barnwell, Beaufort, Colleton, Hampton, Jasper"),
}

NEVER_DRIVE = ("Never drive into water over a road. Six inches of moving water can stall a car, "
               "and a foot can carry it away. Turn around, don't drown.")
COMMON = {"displayOnLoad": True, "browsable": True, "inCaption": True}


def remote(area, kind, licence="NOAA / National Weather Service (public domain)"):
    return {"url": f"{RAW}/{area}/{kind}.geojson", "format": "geojson", "dynamic": False,
            "licence": licence}


def layers_for(area):
    # Order = drawing order: later layers draw on top (uMap lists them first).
    return [
        {"type": "FeatureCollection", "features": [], "properties": {
            **COMMON, "name": "Now: Flood watch (flooding possible)",
            "description": "National Weather Service Flood Watches and Flash Flood Watches. "
                           "Blank when no watch is in effect.",
            "color": RED, "fillOpacity": 0.07, "weight": 1, "dashArray": "6,6", "opacity": 0.6,
            "popupShape": "Panel",
            "popupContentTemplate": "# {event}\n{headline}\n\nUntil: {expires}\n\nFlooding is "
                                    "possible. Check this map again before you drive.",
            "remoteData": remote(area, "watches")}},
        {"type": "FeatureCollection", "features": [], "properties": {
            **COMMON, "name": "Now: Flood warnings",
            "description": "National Weather Service Flood Warnings and Flash Flood Warnings. "
                           "Blank when no warning is in effect.",
            "color": RED, "fillOpacity": 0.25, "weight": 2,
            "popupShape": "Panel",
            "popupContentTemplate": "# {event}\n{headline}\n\nUntil: {expires}\n\n{instruction}",
            "remoteData": remote(area, "warnings")}},
        {"type": "FeatureCollection", "features": [], "properties": {
            **COMMON, "name": "County lines and district edge" if area != "sc" else "County lines and state edge",
            "description": "County lines, and the outer edge of the area this map covers.",
            "color": OUTLINE, "weight": 2, "opacity": 0.7, "fill": False, "interactive": False,
            "remoteData": remote(area, "outline", licence="Outlines: NOAA / National Weather Service")}},
        {"type": "FeatureCollection", "features": [], "properties": {
            **COMMON, "name": "Now: SCDOT road closures (storm damage)",
            "description": "Roads SCDOT reports closed or blocked by flooding, washouts, trees or "
                           "power lines. Planned work zones are left out. Some closures are "
                           "long-term (for example, a washed-out road awaiting repair).",
            "color": RED, "iconClass": "Default",
            "popupContentTemplate": "# {name}\n{description}\n\n" + NEVER_DRIVE,
            "remoteData": remote(area, "closures", licence="SCDOT road conditions (public)")}},
    ]


def description_for(area):
    name, _, _, counties = AREAS[area]
    scope = ("South Carolina" if area == "sc"
             else f"SC ARES District {area[1:]}: {counties} counties")
    return (
        f"**Flood warnings, watches and storm road closures: {scope}.**\n\n"
        "## Now\n"
        "**Red shaded area:** a flood warning is in effect.\n"
        "**Pale red area with a dashed edge:** a flood watch. Flooding is possible; be ready.\n"
        "**Red pin:** SCDOT reports the road closed or blocked by flooding, a washout, trees, "
        "or power lines.\n\n"
        "Tap any symbol for details. Reload the page for the latest information; it updates "
        "about every five minutes from the National Weather Service and SCDOT.\n\n"
        "If water covers the road, turn around. A road with no mark is not guaranteed safe. "
        "Follow your local NWS office and county emergency management.\n\n"
        "## Want more detail for your county?\n"
        "Counties can add creek crossings, past flooding and local road reports. See a full "
        f"county example: [[{KERSHAW_MAP}|Kershaw County Flood Trouble Spots]]. "
        f"Setup guide: [[{GUIDE}|SETUP-GUIDE]].\n\n"
        + CREDIT
    )


def build(area):
    name, center, zoom, _ = AREAS[area]
    return {
        "type": "umap",
        "geometry": {"type": "Point", "coordinates": center},
        "properties": {
            "name": name, "description": description_for(area), "zoom": zoom,
            "onLoadPanel": "caption", "captionBar": True, "datalayersControl": True,
            "tilelayersControl": True, "scaleControl": True, "searchControl": True,
            "locateControl": True, "fullscreenControl": True, "scrollWheelZoom": True,
            "displayPopupFooter": False,
            "tilelayer": {
                "name": "USGS Topo (elevation contours)",
                "url_template": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
                "attribution": "USGS The National Map", "minZoom": 0, "maxZoom": 16,
            },
        },
        "layers": layers_for(area),
    }


OUT.mkdir(exist_ok=True)
for area in AREAS:
    fname = "sc_statewide.umap" if area == "sc" else f"sc_district_{area[1:]}.umap"
    (OUT / fname).write_text(json.dumps(build(area), indent=1))
    print(f"wrote maps/{fname}")
