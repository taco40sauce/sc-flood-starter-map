# Setup Guide: Adding Local Detail to a Flood Map

For SC ARES districts, county emergency management, CERT teams and other
volunteers who want more than the starter maps provide.

The **starter maps** (statewide and one per district) show NWS flood warnings
and watches and SCDOT storm closures. They run on their own.

A **county map** adds the local detail that tells people which roads to avoid:

| Layer | What it shows |
|---|---|
| Creek crossings | Every place a public road crosses a creek (orange dots) |
| Road beside a creek | Low roads running along a creek (yellow dots) |
| Crossings inside a warning | Crossings inside an active NWS warning (orange pins) |
| Flooded before | Verified past flooding from NWS records (blue drops) |
| Local road reports | Your team's reports of water over a road, washouts, trees or power lines down (red pins) |

Working example:
[Kershaw County Flood Trouble Spots](https://umap.openstreetmap.fr/en/map/kershaw-county-flood-trouble-spots_1471681),
built from the open-source repo
[taco40sauce/kershaw-flood-trouble-spots](https://github.com/taco40sauce/kershaw-flood-trouble-spots).

**Why one map per county:** a single county already has several hundred
creek crossings. A map per county keeps load times short on a phone.

---

## Step 1. Decide who owns it

Choose the group that will keep the county map: county emergency management,
an ARES group, or a CERT team. Whoever owns the **Grist doc** (Step 3)
controls what people can add to the map, so pick an owner who will be around
during storms and can hand it on later.

## Step 2. Copy a district starter map (optional)

If you just want your district's starter map under your own account:
open it on uMap and use **Clone this map** (in the map's share/edit menu), or
ask the map owner to add you as an editor.

## Step 3. Set up a Grist doc for local road reports

[Grist](https://www.getgrist.com) is a free online spreadsheet. Team members
add a row; a few minutes later a red pin appears on the public map. Setting
the row's Status to **OP-open** removes the pin and keeps the record.

1. Create a free account and a new document (for example, "<County> Flood Road Reports").
2. Make one table with these columns:

| Column | Type | Choices / notes |
|---|---|---|
| ObjectName | Choice | `KCGR-ROAD-road/bridge` |
| Status | Choice | `CL-closed`, `LM-limited`, `CA-caution`, `UK-unknown`, `OP-open` |
| Specifier | Choice | `FL-flooding`, `BR-bridge damage`, `TR-trees/debris`, `PL-power lines down` |
| Location | Text | Road name and nearest landmark |
| DateTime | Text | When it was observed |
| Notes | Text | Anything else (dam breach, depth of water, detour) |
| Latitude | Numeric | Decimal degrees, e.g. 34.2477 |
| Longitude | Numeric | Decimal degrees, e.g. -80.7141 |
| ReportedBy | Text | Not shown on the public map |
| Verified | Toggle | Only verified rows appear on the map |

3. Invite your editors (Share → Manage Users → role **Editor**). Check
   Grist's current free-plan member limit.
4. Create an API key (profile → Profile Settings → API) for Step 4.

**Practice reports:** start the Notes with the word **EXERCISE** (or use
DRILL, TEST, PRACTICE or SIMULATED in the location or notes). Those rows are
never shown on the public map. For a deliberate end-to-end check, use other
wording, such as "System CHECK, not a report."

## Step 4. Build the county map

Copy the Kershaw repo (**Use this template** or **Fork** on GitHub, or
download it) and follow its README section **"Using this for another
county."** In short:

1. **Creek crossings:** download the county's two Census TIGER/Line files
   (roads and linear water) and run `tools/build_crossings.py`. The county's
   FIPS code is in `sc_flood_now.py` in this repo (Kershaw = 45055).
2. **Flood history:** from the NWS Storm Events Database, download the
   county's flash flood reports and add the ones that name a specific road
   or place to `data/history.geojson`.
3. **Settings:** edit the top of `tools/build_map.py` (map name, center,
   repo) and of `flood_now.py` (`SCDOT_COUNTIES`, `GRIST_DOC_ID`,
   `GRIST_SERVER`).
4. **Secrets and trigger:** add `GRIST_API_KEY` as a GitHub Actions secret,
   and set up a cron-job.org trigger with its own token (see the README).
5. **Map:** build the `.umap` file and import it into a new uMap map.

### Not comfortable running scripts?

Steps 1 and 5 need a little Python. If your group would rather not, ask for
help: [contact name and email to be added]. Send the county name, and the
crossings and map file can be built for you.

## Step 5. Link it

Add the county map to your district's pages and your county's emergency
information pages, and let residents know to bookmark it before the next storm.

---

## Quick answers

- **Does the county map replace the starter map?** No. The starter maps keep
  running; the county map adds detail for one county.
- **Who can change the county map?** NWS and SCDOT layers update
  automatically. People change it only through the Grist doc.
- **What does it cost?** Nothing: uMap, GitHub, Grist's free plan and
  cron-job.org are all free at this scale.
