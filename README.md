# South Carolina Flood Starter Maps

Free public maps of **flood warnings, flood watches and storm road closures**
for South Carolina: one statewide map and one map for each of the six SC ARES
districts.

They are **starter maps**. They show only official, automatic information, so
they work with nobody tending them. Districts and counties can then add more
detail (creek crossings, past flooding, local road reports) by building
county maps like the
[Kershaw County Flood Trouble Spots](https://umap.openstreetmap.fr/en/map/kershaw-county-flood-trouble-spots_1471681)
map. See [SETUP-GUIDE.md](SETUP-GUIDE.md).

**Live maps:**
- [South Carolina Flood Trouble Spots](https://umap.openstreetmap.fr/en/map/south-carolina-flood-trouble-spots_1476690) (statewide)
- District maps: coming soon

Built by KC4RC / Kershaw County ARES. Open source (MIT).

## What the maps show

| Layer | Symbol | Source |
|---|---|---|
| Flood watch | Pale red, dashed edge | National Weather Service, live |
| Flood warning | Red shaded area | National Weather Service, live |
| SCDOT road closures (storm damage) | Red pin | SCDOT road conditions, live |
| County lines and area edge | Grey lines | NWS county zones |

SCDOT closures are kept only when SCDOT's description points to flooding,
a washout or sinkhole, trees or debris, or power lines. Planned work zones
(resurfacing, replacements, repairs, contractor work) are left out. Some
closures are long-term, such as a road washed out years ago and not yet
rebuilt; they are still real closures.

## Areas

| Map file | Area | Counties |
|---|---|---|
| `maps/sc_statewide.umap` | South Carolina | all 46 |
| `maps/sc_district_1.umap` | District 1 | Abbeville, Anderson, Edgefield, Greenville, Greenwood, McCormick, Oconee, Pickens |
| `maps/sc_district_2.umap` | District 2 | Cherokee, Chester, Lancaster, Laurens, Spartanburg, Union, York |
| `maps/sc_district_3.umap` | District 3 | Calhoun, Fairfield, Kershaw, Lexington, Newberry, Richland, Saluda |
| `maps/sc_district_4.umap` | District 4 | Chesterfield, Darlington, Dillon, Florence, Horry, Lee, Marion, Marlboro |
| `maps/sc_district_5.umap` | District 5 | Berkeley, Charleston, Clarendon, Dorchester, Georgetown, Orangeburg, Sumter, Williamsburg |
| `maps/sc_district_6.umap` | District 6 | Aiken, Allendale, Bamberg, Barnwell, Beaufort, Colleton, Hampton, Jasper |

District list from the ARES-SC leadership directory (October 2026).

## How it works

`sc_flood_now.py` runs on GitHub Actions about every five minutes. It reads
NWS alerts for South Carolina and SCDOT's road-conditions feed, sorts them by
area, and writes `out/<area>/warnings.geojson`, `watches.geojson`,
`closures.geojson` and `outline.geojson` for `sc` and `d1`–`d6`.

- **Alerts by district:** every NWS alert lists the counties it covers; an
  alert goes into a district's file only if it covers one of that district's
  counties, and its shape is trimmed to the district.
- **Watches:** NWS usually sends watches as whole forecast zones with no
  shape attached; the script fetches the zone shapes and fills them in.
- **Outlines:** county shapes come from NWS county zones, fetched once on the
  first run and saved in `data/counties.geojson`.
- **If a source is down:** the last files are kept (alerts that have already
  expired are dropped).

The uMap maps read these files directly, so the maps never need rebuilding
when warnings or closures change. Viewers reload the page for the latest.

## What's in this repo

| Path | What it is |
|---|---|
| `sc_flood_now.py` | The update script |
| `out/` | Live files the maps read (made by the script) |
| `data/` | County outlines (made by the script on its first run) |
| `.github/workflows/sc-flood-now.yml` | Runs the script and commits changes |
| `tools/build_maps.py` | Builds the seven `.umap` files in `maps/` |
| `maps/` | uMap import files |
| `SETUP-GUIDE.md` | For districts and counties adding local detail |

## Setup (for whoever runs this repo)

1. **Trigger every 5 minutes (cron-job.org).** GitHub's own schedule (every
   15 minutes) is only a backup and often runs late.
   - URL: `https://api.github.com/repos/taco40sauce/sc-flood-starter-map/actions/workflows/sc-flood-now.yml/dispatches`
   - Method POST; body `{"ref":"main"}`
   - Headers: `Authorization: Bearer <token>` and `Accept: application/vnd.github+json`
     (add each as a row, then save, and reopen to confirm they stayed)
   - Token: a GitHub fine-grained token with **Actions: Read and write** on
     this repo only.
2. **Load a map into uMap:** create a new map on umap.openstreetmap.fr, press
   **Ctrl+I**, choose a file from `maps/`, **Import data**, then **Save**.
   If the legend didn't come through, paste it in from `tools/build_maps.py`
   (map "i" icon → description).

## Handing it over

GitHub's **Settings → Transfer ownership** moves this repo, with its history,
to another account (for example ARES-SC). The new owner sets up their own
token and cron-job.org trigger; uMap maps can be shared with them as editors.

## Limits

- A road with no mark is not guaranteed safe. If water covers the road, turn around.
- SCDOT closures depend on SCDOT's wording; the keyword filter may miss
  unusual descriptions.
- This is a volunteer project, not an official alert service. Follow the
  National Weather Service and county emergency management.

## License

MIT. See `LICENSE`.
