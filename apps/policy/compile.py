"""Compile Open Policy Agent bundles for jurisdiction policies."""
from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

BASE_DIR = Path(__file__).resolve().parent
JURISDICTION_ROOT = BASE_DIR.parent / "city_regulatory_service" / "jurisdictions"
OUTPUT_ROOT = BASE_DIR / "bundles"


def _jurisdiction_files(slug: str) -> Iterable[tuple[Path, Path]]:
    """Yield filesystem and archive paths for a jurisdiction."""

    base = JURISDICTION_ROOT / slug
    for file_path in base.rglob("*"):
        if not file_path.is_file():
            continue
        arcname = Path("city_regulatory_service") / "jurisdictions" / slug / file_path.relative_to(base)
        yield file_path, arcname


def _write_bundle(destination: Path, jurisdictions: Sequence[str]) -> None:
    """Create a gzipped tar bundle with the provided jurisdictions."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as bundle:
        manifest = {
            "revision": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "roots": ["city_regulatory_service"],
            "jurisdictions": list(jurisdictions),
        }
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        bundle.addfile(manifest_info, io.BytesIO(manifest_bytes))

        for slug in jurisdictions:
            for file_path, arcname in _jurisdiction_files(slug):
                bundle.add(file_path, arcname=str(arcname))


def build_individual_bundles(jurisdictions: Sequence[str]) -> None:
    """Bundle each jurisdiction into its own artifact."""

    for slug in jurisdictions:
        destination = OUTPUT_ROOT / slug / "city_regulatory_service.tar.gz"
        _write_bundle(destination, [slug])


def build_region_bundles(region_map: dict[str, Sequence[str]]) -> None:
    """Bundle logical regions that contain multiple jurisdictions."""

    for region, slugs in region_map.items():
        destination = OUTPUT_ROOT / region / "city_regulatory_service.tar.gz"
        _write_bundle(destination, slugs)


def main() -> None:
    """Compile all jurisdiction bundles."""

    slugs = sorted(entry.name for entry in JURISDICTION_ROOT.iterdir() if entry.is_dir())
    build_individual_bundles(slugs)

    region_map = {
        "sf_bay_area": [
            "oakland",
            "san_francisco",
            "berkeley",
            "palo_alto",
            "san_jose",
        ],
        "joshua_tree": ["joshua_tree"],
    }
    build_region_bundles(region_map)


if __name__ == "__main__":
    main()
