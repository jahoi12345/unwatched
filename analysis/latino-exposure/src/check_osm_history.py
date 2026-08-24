"""One-off feasibility check: does OSM node-edit history for Oakland's ALPR
cameras reflect organic, spread-out tagging (usable as an install-date proxy),
or bulk mass-edit events (not usable at fine time resolution)?

Not part of the pipeline -- a diagnostic run once to decide whether Design A
of the DiD scope (SCOPE.md, Part 2) is viable as specified.
"""

import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMERAS_PATH = HERE.parent.parent.parent / "src" / "data" / "generated" / "cameras.json"
OUT_PATH = HERE.parent / "data" / "raw" / "osm_node_history_sample.json"

USER_AGENT = "unwatched-latino-exposure-research/0.1 (public-interest research, one-off feasibility check)"


def fetch_history(node_id: int) -> list[dict]:
    url = f"https://api.openstreetmap.org/api/0.6/node/{node_id}/history.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    return data.get("elements", [])


def main(sample_size: int = 120, delay_s: float = 0.3) -> None:
    cameras = json.loads(CAMERAS_PATH.read_text())["cameras"]
    ids = [c["id"] for c in cameras[:sample_size]]

    results = []
    for i, node_id in enumerate(ids):
        try:
            versions = fetch_history(node_id)
        except Exception as exc:  # noqa: BLE001 -- diagnostic script, log and continue
            print(f"  [{i+1}/{len(ids)}] node {node_id}: ERROR {exc}")
            continue

        first_alpr = None
        last_alpr_edit = None
        for v in versions:
            tags = v.get("tags", {})
            if tags.get("surveillance:type") == "ALPR":
                ts = v["timestamp"]
                if first_alpr is None:
                    first_alpr = ts
                last_alpr_edit = ts

        results.append(
            {
                "id": node_id,
                "version_count": len(versions),
                "first_alpr_tagged_at": first_alpr,
                "last_alpr_edit_at": last_alpr_edit,
            }
        )
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(ids)}] fetched")
        time.sleep(delay_s)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} node histories to {OUT_PATH}")


if __name__ == "__main__":
    main()
