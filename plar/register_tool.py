"""Register the prepared Python tool in PLAR's JSON configuration."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile


def register(config_path: Path):
    config_path = config_path.resolve(strict=True)
    entry = json.loads(Path(__file__).with_name("Screen Spotlight.tool.json").read_text(encoding="utf-8"))
    script = Path(entry["script"])
    if not script.is_file():
        raise ValueError(f"Runner does not exist: {script}")
    before = config_path.read_bytes()
    tools = json.loads(before.decode("utf-8-sig"))
    if not isinstance(tools, list) or not all(isinstance(tool, dict) for tool in tools):
        raise ValueError("Expected PLAR's JSON array of tool objects")
    matches = [tool for tool in tools if tool.get("name") == entry["name"]]
    if matches:
        if len(matches) == 1 and matches[0] == entry:
            print("Screen Spotlight is already registered.")
            return
        raise ValueError("A different Screen Spotlight entry already exists; it was not overwritten")
    tools.append(entry)
    backup = config_path.with_name(config_path.name + ".spotlight-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    payload = (json.dumps(tools, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    fd, staging = tempfile.mkstemp(prefix=".spotlight-", suffix=".json", dir=config_path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
        if config_path.read_bytes() != before:
            raise RuntimeError("PLAR configuration changed during registration; retry after closing PLAR")
        with backup.open("xb") as output:
            output.write(before)
        os.replace(staging, config_path)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)
    print(f"Registered: {entry['name']}")
    print(f"Backup: {backup}")
    print("Reload PLAR's tools configuration before editing or saving tools.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    register(args.config)
