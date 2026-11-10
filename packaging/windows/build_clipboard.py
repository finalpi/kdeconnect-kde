"""Build only the existing KDE clipboard plugin against a matching Windows installation.

SPDX-License-Identifier: GPL-3.0-only
Run from an x64 MSVC developer environment. No new runtime process is installed.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess


def run(args, **kwargs):
    result = subprocess.run([str(x) for x in args], capture_output=True, encoding="utf-8", errors="replace", **kwargs)
    if result.returncode:
        print(result.stdout[-12000:])
        print(result.stderr[-12000:])
        raise SystemExit(result.returncode)
    return result.stdout


parser = argparse.ArgumentParser()
parser.add_argument("--qt", type=pathlib.Path, required=True)
parser.add_argument("--frameworks", type=pathlib.Path, required=True)
parser.add_argument("--kde-source", type=pathlib.Path, required=True)
parser.add_argument("--runtime", type=pathlib.Path, required=True)
parser.add_argument("--output", type=pathlib.Path, required=True)
args = parser.parse_args()
source = args.kde_source / "plugins/clipboard"
manifest = json.loads(pathlib.Path(__file__).with_name("runtime-manifest.json").read_text())
if hashlib.sha256((args.runtime / "kdeconnectcore.dll").read_bytes()).hexdigest() != manifest["runtimeCoreSha256"]:
    raise SystemExit("The runtime is not the pinned KDE Connect release; refusing an ABI mismatch")
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
generated = out / "include"
generated.mkdir(exist_ok=True)

for prefix in ["KCOREADDONS", "KGUIADDONS", "KDECONNECTCORE", "KCONFIGCORE", "KI18N"]:
    body = "#pragma once\n"
    for name, value in {
        "EXPORT": "__declspec(dllimport)", "NO_EXPORT": "", "DEPRECATED": "__declspec(deprecated)",
        "DEPRECATED_EXPORT": "__declspec(dllimport)", "DEPRECATED_NO_EXPORT": "",
        "ENABLE_DEPRECATED_SINCE(major,minor)": "1", "BUILD_DEPRECATED_SINCE(major,minor)": "1",
        "DEPRECATED_VERSION(major,minor,text)": "", "DEPRECATED_VERSION_BELATED(major,minor,a,b,text)": "",
        "ENUMERATOR_DEPRECATED_VERSION(major,minor,text)": "", "DEPRECATED_VERSION_EXPORT(major,minor,text)": "__declspec(dllimport)",
    }.items():
        body += "#define " + prefix + "_" + name + " " + value + "\n"
    (generated / (prefix.lower() + "_export.h")).write_text(body)

headers = []
for repo in ["kcoreaddons", "kguiaddons", "kconfig", "ki18n"]:
    headers.extend((args.frameworks / repo / "src").rglob("*.h"))
by_stem = {p.stem.lower(): p.resolve() for p in headers}
for header in headers:
    text = header.read_text(encoding="utf-8", errors="replace")
    for name in re.findall(r"\b(K[A-Z][A-Za-z0-9_]+)\b", text):
        actual = by_stem.get(name.lower())
        if actual:
            (generated / name).write_text('#include "' + actual.as_posix() + '"\n')

(generated / "plugin_clipboard_debug.h").write_text("#include <QLoggingCategory>\nQ_DECLARE_LOGGING_CATEGORY(KDECONNECT_PLUGIN_CLIPBOARD)\n")
(out / "debug.cpp").write_text('#include "plugin_clipboard_debug.h"\nQ_LOGGING_CATEGORY(KDECONNECT_PLUGIN_CLIPBOARD, "kdeconnect.plugin.clipboard")\n')

includes = [source, generated, args.kde_source, args.kde_source / "core", args.qt / "include"]
includes += [args.qt / "include" / name for name in ["QtCore", "QtGui", "QtWidgets", "QtNetwork", "QtDBus"]]
includes += sorted({p.parent for p in headers})
defines = ["QT_NO_DEBUG", "NDEBUG", "QT_CORE_LIB", "QT_GUI_LIB", "QT_WIDGETS_LIB", "QT_NETWORK_LIB", "QT_DBUS_LIB"]
common = ["-I" + str(p) for p in includes] + ["-D" + d for d in defines]
moc = args.qt / "bin/moc.exe"
for name in ["clipboardplugin", "clipboardlistener"]:
    run([moc, *common, source / (name + ".h"), "-o", out / ("moc_" + name + ".cpp")])
run([moc, *common, source / "clipboardplugin.cpp", "-o", out / "clipboardplugin.moc"])

libraries = []
for dll_name in ["kdeconnectcore", "KF6CoreAddons", "KF6GuiAddons"]:
    exports = run(["dumpbin.exe", "/exports", args.runtime / (dll_name + ".dll")])
    names = re.findall(r"^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(\S+)", exports, re.MULTILINE)
    definition = out / (dll_name + ".def")
    definition.write_text('LIBRARY "' + dll_name + '.dll"\nEXPORTS\n' + "\n".join(names) + "\n")
    library = out / (dll_name + ".lib")
    run(["lib.exe", "/nologo", "/machine:x64", "/def:" + str(definition), "/out:" + str(library)])
    libraries.append(library)

objects = []
for cpp in [source / "clipboardplugin.cpp", source / "clipboardlistener.cpp", out / "debug.cpp"]:
    obj = out / (cpp.stem + ".obj")
    response = out / (cpp.stem + ".rsp")
    options = ["/nologo", "/c", "/std:c++20", "/MD", "/EHsc", "/utf-8", "/Zc:__cplusplus", "/permissive-", "/I" + str(out)]
    options += ["/I" + str(p) for p in includes] + ["/D" + d for d in defines]
    options += ["/Fo" + str(obj), str(cpp)]
    response.write_text("\n".join('"' + x + '"' for x in options), encoding="utf-8-sig")
    run(["cl.exe", "@" + str(response)])
    objects.append(obj)
target = out / "kdeconnect_clipboard.dll"
run(["link.exe", "/nologo", "/dll", "/machine:x64", "/out:" + str(target), *objects, *libraries,
     *[args.qt / "lib" / (name + ".lib") for name in ["Qt6Core", "Qt6Gui", "Qt6Widgets", "Qt6Network", "Qt6DBus"]]])
print("Built existing native clipboard plugin:", target)

# Load the real native factory and exercise the actual listener against an isolated
# offscreen clipboard. These checks do not touch the desktop user's clipboard.
test_dir = pathlib.Path(__file__).with_name("tests")
env = os.environ.copy()
env["PATH"] = str(args.runtime.resolve()) + os.pathsep + env["PATH"]
env["QT_QPA_PLATFORM"] = "offscreen"
env["QT_PLUGIN_PATH"] = str(args.runtime.resolve())
test_includes = ["/I" + str(p) for p in includes] + ["/I" + str(out), "/I" + str(args.qt / "include/QtTest")]
test_defines = ["/D" + d for d in defines]
for name in ["factorytest", "clipboardimagetest"]:
    cpp = test_dir / (name + ".cpp")
    if name == "clipboardimagetest":
        run([moc, *common, "-I" + str(args.qt / "include/QtTest"), cpp, "-o", out / (name + ".moc")])
    exe = out / (name + ".exe")
    test_objects = [out / "clipboardlistener.obj", out / "debug.obj"] if name == "clipboardimagetest" else []
    response = out / (name + ".rsp")
    options = ["/nologo", "/std:c++20", "/MD", "/EHsc", "/utf-8", "/Zc:__cplusplus", *test_includes, *test_defines,
               "/Fe" + str(exe), "/Fo" + str(out / (name + ".obj")), str(cpp), *map(str, test_objects), "/link",
               *map(str, libraries), *[str(args.qt / "lib" / (x + ".lib")) for x in ["Qt6Core", "Qt6Gui", "Qt6Widgets", "Qt6Network", "Qt6DBus", "Qt6Test"]]]
    response.write_text("\n".join('"' + str(x) + '"' for x in options), encoding="utf-8-sig")
    run(["cl.exe", "@" + str(response)])
    report = out / "clipboard-test-results.xml"
    if name == "clipboardimagetest":
        report.unlink(missing_ok=True)
    output = run([exe, target] if name == "factorytest" else [exe, "-o", str(report) + ",junitxml"], env=env)
    print(output)
    if name == "clipboardimagetest":
        import xml.etree.ElementTree as ET
        suite = ET.parse(report).getroot()
        if int(suite.get("tests", "0")) < 6 or int(suite.get("failures", "0")) or int(suite.get("errors", "0")):
            raise SystemExit("Clipboard behavior tests did not all pass")
        print("Clipboard behavior tests:", suite.get("tests"), "passed")
