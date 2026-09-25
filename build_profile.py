import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from pipeline.cv_extractor import extract_text
from pipeline.profile_builder import build_profile_from_cv

ROOT = Path(__file__).parent
DEFAULT_OUTPUT = ROOT / "profile" / "candidate_profile.json"


def main():
    parser = argparse.ArgumentParser(
        description="Build profile/candidate_profile.json automatically from a CV PDF."
    )
    parser.add_argument("cv_path", help="Path to the CV PDF file")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT),
                         help=f"Output path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    cv_path = Path(args.cv_path)
    if not cv_path.exists():
        print(f"File not found: {cv_path}", file=sys.stderr)
        sys.exit(1)
    if cv_path.suffix.lower() != ".pdf":
        print(f"Only PDF files are supported right now (got {cv_path.suffix}).", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    if output_path.exists():
        answer = input(f"{output_path} already exists. Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    print(f"Extracting text from {cv_path}...")
    cv_text = extract_text(str(cv_path))
    print(f"Extracted {len(cv_text)} characters. Sending to LLM for structuring...")

    profile = build_profile_from_cv(cv_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\nProfile saved to {output_path}")
    print(f"Name: {profile.get('name')}")
    print(f"Target titles: {', '.join(profile.get('target_titles', []))}")
    print(f"Skills ({len(profile.get('skills', []))}): {', '.join(profile.get('skills', [])[:10])}...")
    print("\nReview the generated file and adjust anything the extraction got wrong before running main.py.")


if __name__ == "__main__":
    main()
