"""Standalone CLI entry point for running the screening pipeline without the API."""

from __future__ import annotations

import argparse
import json

from config import load_config
from models import JobDescriptionRequest
from pipeline import run_screening


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the resume screening pipeline once.")
    parser.add_argument("--location", default="", help="Job location")
    parser.add_argument("--skills", default="", help="Required skills, comma-separated")
    parser.add_argument("--other-details", default="", help="Experience level, domain, certifications, etc.")
    args = parser.parse_args()

    jd = JobDescriptionRequest(
        location=args.location,
        skills=args.skills,
        other_details=args.other_details,
    )

    results = run_screening(jd, load_config())
    print(json.dumps([r.model_dump() for r in results], indent=2))


if __name__ == "__main__":
    main()
