"""Run manually (no cloud/GitHub automation) whenever a new prospective camera
snapshot is wanted, to eventually build a real installation-date panel for the
DiD extension (see SCOPE.md Part 2). Pulls Oakland's current ALPR camera set
from OSM/Overpass and appends it to data/raw/oakland_camera_snapshots/.
"""

import csv
import json
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
CAMERAS_PATH = HERE.parent.parent.parent / "src" / "data" / "generated" / "cameras.json"
SNAPSHOT_DIR = HERE.parent / "data" / "raw" / "oakland_camera_snapshots"

USER_AGENT = "unwatched-latino-exposure-research/0.1 (public-interest research)"
OVERPASS_ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def fetch_cameras(bbox: dict) -> list:
    query = (
        f'[out:json][timeout:60];\nnode["surveillance:type"="ALPR"]'
        f'({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});\nout body;'
    )
    data = urllib.parse.urlencode({"data": query}).encode()
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=65) as resp:
                return json.load(resp)["elements"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise RuntimeError(f"Both Overpass endpoints failed: {last_err}")


def main():
    bbox = json.loads(CAMERAS_PATH.read_text())["bbox"]
    elements = fetch_cameras(bbox)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot_path = SNAPSHOT_DIR / f"{today}.json"
    snapshot_path.write_text(json.dumps(elements))

    manifest_path = SNAPSHOT_DIR / "manifest.csv"
    is_new = not manifest_path.exists()
    with open(manifest_path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["date", "camera_count"])
        writer.writerow([today, len(elements)])

    print(f"Snapshot for {today}: {len(elements)} cameras -> {snapshot_path}")
    print(f"Manifest updated -> {manifest_path}")


if __name__ == "__main__":
    main()
