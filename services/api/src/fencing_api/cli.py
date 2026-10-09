import argparse
import json
from pathlib import Path

from fencing_domain.registry import doctor


def main() -> None:
    parser = argparse.ArgumentParser(prog="datasets")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--root", default="data/datasets")
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps(doctor(Path(args.root)), indent=2))


if __name__ == "__main__":
    main()
