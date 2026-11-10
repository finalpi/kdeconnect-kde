"""Download the pinned build inputs. Does not install anything on the build host.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--sevenzip", default="7z")
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=True)
manifest = json.loads(Path(__file__).with_name("runtime-manifest.json").read_text())

def download(url, path, expected=None):
    if not path.exists():
        print("Downloading", url, flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
    if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"SHA-256 mismatch: {path}")

for name, url_key, hash_key in [("official.exe", "baseInstallerUrl", "baseInstallerSha256"),
                                ("qtbase.7z", "qtBaseUrl", "qtBaseSha256"),
                                ("nsis.zip", "nsisUrl", "nsisSha256")]:
    download(manifest[url_key], root / name, manifest[hash_key])
if not (root / "qt/bin/moc.exe").exists():
    subprocess.run([args.sevenzip, "x", str(root / "qtbase.7z"), "-o" + str(root / "qt"), "-y", "-bso0", "-bsp0"], check=True)
if not (root / "nsis/nsis-3.13/makensis.exe").exists():
    with zipfile.ZipFile(root / "nsis.zip") as archive:
        archive.extractall(root / "nsis")
for repo in ["kcoreaddons", "kguiaddons", "kconfig", "ki18n"]:
    target = root / "frameworks" / repo
    if target.exists():
        continue
    archive_path = root / (repo + ".tar.gz")
    download(f"https://codeload.github.com/KDE/{repo}/tar.gz/refs/tags/v{manifest['frameworksVersion']}", archive_path)
    with tarfile.open(archive_path) as archive:
        archive.extractall(root / "frameworks", filter="data")
    (root / "frameworks" / f"{repo}-{manifest['frameworksVersion']}").rename(target)
print("Build inputs ready:", root)
