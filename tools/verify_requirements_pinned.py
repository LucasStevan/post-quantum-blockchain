from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"


def main():
    bad = []
    for line_no, raw in enumerate(REQ.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line or any(op in line for op in (">=", "<=", "~=", "!=", ">")):
            bad.append((line_no, line))
    if bad:
        formatted = ", ".join(f"{line_no}:{line}" for line_no, line in bad)
        raise SystemExit(f"Unpinned requirements: {formatted}")
    print("requirements are exact-pinned")


if __name__ == "__main__":
    main()
