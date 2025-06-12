#!/usr/bin/env python3
"""Convert core JSON files to CSV."""

import csv
import json
from pathlib import Path

from src.utils.path_manager import path_manager


def convert_roles_to_csv(json_path: Path, csv_path: Path) -> None:
    with open(json_path, encoding="utf-8") as f:
        roles = json.load(f)
    fieldnames = ["display", "label", "category"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for role in roles:
            writer.writerow({k: role.get(k, "") for k in fieldnames})


def convert_role_mapping_to_csv(json_path: Path, csv_path: Path) -> None:
    with open(json_path, encoding="utf-8") as f:
        mapping = json.load(f)
    fieldnames = ["remarks", "roles", "match"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for remarks, info in mapping.items():
            if remarks == "_comment":
                continue
            roles = (
                ";".join(info.get("roles", []))
                if isinstance(info, dict)
                else ""
            )
            match = (
                info.get("match", "") if isinstance(info, dict) else ""
            )
            writer.writerow({
                "remarks": remarks,
                "roles": roles,
                "match": match,
            })


def convert_records_to_csv(records_dir: Path, csv_path: Path) -> None:
    fieldnames = [
        "id",
        "photo_category",
        "category",
        "type",
        "subtype",
        "remarks",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec_file in sorted(records_dir.glob("rec_*.json")):
            with open(rec_file, encoding="utf-8") as rf:
                data = json.load(rf)
            data["id"] = rec_file.stem
            writer.writerow({k: data.get(k, "") for k in fieldnames})


def convert_master_to_csv(json_path: Path, csv_path: Path) -> None:
    with open(json_path, encoding="utf-8") as f:
        images = json.load(f)
    fieldnames = ["filename", "image_path", "bboxes"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for img in images:
            writer.writerow({
                "filename": img.get("filename", ""),
                "image_path": img.get("image_path", ""),
                "bboxes": json.dumps(
                    img.get("bboxes", []), ensure_ascii=False
                ),
            })


def main() -> None:
    out_dir = Path("csv")
    out_dir.mkdir(exist_ok=True)
    convert_roles_to_csv(
        path_manager.preset_roles,
        out_dir / "preset_roles.csv",
    )
    convert_role_mapping_to_csv(
        path_manager.role_mapping,
        out_dir / "role_mapping.csv",
    )
    records_dir = path_manager.data_dir / "dictionaries" / "records"
    convert_records_to_csv(records_dir, out_dir / "records.csv")
    convert_master_to_csv(
        path_manager.image_preview_cache_master,
        out_dir / "image_preview_cache_master.csv",
    )
    print(f"CSV files written to {out_dir}")


if __name__ == "__main__":
    main()
