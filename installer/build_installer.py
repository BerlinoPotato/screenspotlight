"""Rebuild the app and PLAR runner, then package a per-user Windows installer."""
import argparse
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def app_version():
    tree = ast.parse((ROOT / "spotlight.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_VERSION"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError("APP_VERSION is missing from spotlight.py")


def find_compiler(explicit):
    if explicit:
        candidates = [Path(explicit)]
    else:
        candidates = []
        if os.environ.get("ISCC"):
            candidates.append(Path(os.environ["ISCC"]))
        if shutil.which("ISCC.exe"):
            candidates.append(Path(shutil.which("ISCC.exe")))
        candidates.extend(sorted((ROOT / "build/toolchains").glob("innosetup-*/ISCC.exe"), reverse=True))
        for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                     str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs")):
            if base:
                candidates.extend(Path(base) / name / "ISCC.exe" for name in ("Inno Setup 7", "Inno Setup 6"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Inno Setup compiler not found. Install Inno Setup 6.3+ from "
        "https://jrsoftware.org/isdl.php and pass --iscc PATH_TO_ISCC.exe, "
        "or set the ISCC environment variable."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", help="Path to the Inno Setup command-line compiler")
    args = parser.parse_args()
    compiler = find_compiler(args.iscc)
    version = app_version()
    subprocess.run([sys.executable, "plar/prepare_runner.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "ScreenSpotlight.spec"], cwd=ROOT, check=True)
    subprocess.run([str(compiler), f"/DExpectedVersion={version}",
                    str(ROOT / "installer/ScreenSpotlight.iss")], cwd=ROOT, check=True)
    print(f"Built {ROOT / 'dist' / f'ScreenSpotlight-Setup-{version}.exe'}", flush=True)


if __name__ == "__main__":
    main()
