"""Build a complete installer using a pinned official base and fork-built component.

Unchanged upstream binaries retain their signatures. No installed client is needed
on the build host. The installer contains the entire client, not a patch download.
SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--base-installer", type=Path, required=True)
parser.add_argument("--qt", type=Path, required=True)
parser.add_argument("--frameworks", type=Path, required=True)
parser.add_argument("--nsis", type=Path, required=True)
parser.add_argument("--sevenzip", default="7z")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
source = Path(__file__).resolve().parents[2]
scripts = Path(__file__).resolve().parent
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((scripts / "runtime-manifest.json").read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, **kwargs):
    subprocess.run([str(x) for x in command], check=True, **kwargs)

if sha(args.base_installer) != manifest["baseInstallerSha256"]:
    raise SystemExit("Official installer hash mismatch")
# Verify the upstream publisher as well as the content hash.
ps_env = os.environ.copy()
# A VS developer prompt can prepend incompatible PowerShell 7 module directories.
ps_env["PSModulePath"] = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/Modules")
run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
     "$s=Get-AuthenticodeSignature -LiteralPath '" + str(args.base_installer.resolve()).replace("'", "''") +
     "'; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notlike '*K Desktop Environment*'){exit 1}"], env=ps_env)
base = out / "base"
run([args.sevenzip, "x", args.base_installer.resolve(), "*.7z", "-o" + str(base), "-y", "-bso0", "-bsp0"])
archives = list(base.glob("*.7z"))
if len(archives) != 1:
    raise SystemExit("Expected a single official application archive")
runtime = out / "runtime"
run([args.sevenzip, "x", archives[0], "-o" + str(runtime), "-y", "-bso0", "-bsp0"])
build = out / "native"
run([sys.executable, scripts / "build_clipboard.py", "--qt", args.qt.resolve(), "--frameworks", args.frameworks.resolve(),
     "--kde-source", source, "--runtime", runtime / "bin", "--output", build])
info = dict(manifest)
info["sourceRepository"] = "https://github.com/finalpi/kdeconnect-kde"
info["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
info["sourceDirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=source))
info["componentSha256"] = sha(build / "kdeconnect_clipboard.dll")
info["sourceFilesSha256"] = {str(p.relative_to(source)).replace("\\", "/"): sha(p)
    for p in sorted((source / "plugins/clipboard").glob("*.cpp")) + sorted((source / "plugins/clipboard").glob("*.h"))}
info["buildMethod"] = "Fork-built native clipboard component; unchanged binaries from the pinned official installer"
info_path = out / "fork-build.json"
info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
target = out / f"kdeconnect-{manifest['forkVersion']}-windows-x64.exe"
run([args.nsis.resolve(), "/V2", "/DBASE=" + str(args.base_installer.resolve()), "/DCOMPONENT=" + str(build / "kdeconnect_clipboard.dll"),
     "/DINFO=" + str(info_path), "/DSOURCE=" + str(source), "/DVERSION=" + manifest["forkVersion"], "/DOUTPUT=" + str(target), scripts / "installer.nsi"])
(out / "SHA256SUMS.txt").write_text(sha(target) + "  " + target.name + "\n", encoding="utf-8")
print("Complete Windows installer:", target)
