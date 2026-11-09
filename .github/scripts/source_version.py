"""Source display versions only; independent build, prebuilt and 4D counters are excluded."""

import argparse
import plistlib
import re
from pathlib import Path


PROJECT = Path("JSMin.xcodeproj/project.pbxproj")
PLIST = Path("Info.plist")
LOCALIZED = Path("English.lproj/InfoPlist.strings")
SOURCE_PATHS = (PROJECT, PLIST, LOCALIZED)
VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
BUILD_VERSION = r"[0-9]+(?:\.[0-9]+){0,2}"
KEYS = ("MARKETING_VERSION", "CURRENT_PROJECT_VERSION")
SETTING = re.compile(r"(?m)^(\s*(MARKETING_VERSION|CURRENT_PROJECT_VERSION)\s*=\s*)([^;\n]+)(;)")
REFERENCES = {f"$({key})": key for key in KEYS}
REFERENCES.update({f"${{{key}}}": key for key in KEYS})
LOCALIZED_SHORT = re.compile(r'(?m)^(CFBundleShortVersionString = ")([^"]*)(";)$')
LOCALIZED_INFO = re.compile(
    r'(?m)^(CFBundleGetInfoString = "JSMin version )([^,"]*)(, Copyright [^"]*";)$'
)


def unquote(value):
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def read(root=Path(".")):
    fields = {key: [] for key in KEYS}
    for match in SETTING.finditer((root / PROJECT).read_text()):
        fields[match[2]].append(unquote(match[3].strip()))
    if any(len(fields[key]) != 6 for key in KEYS):
        raise ValueError("Expected six source settings for each version key")
    marketing = set(fields["MARKETING_VERSION"])
    if len(marketing) != 1 or not re.fullmatch(VERSION, next(iter(marketing))):
        raise ValueError("MARKETING_VERSION must be one strict X.Y.Z across configurations")
    version = next(iter(marketing))
    # The original workflow explicitly selected marketing, with current only a fallback.
    current = set(fields["CURRENT_PROJECT_VERSION"])
    if len(current) != 1:
        raise ValueError("Independent CURRENT_PROJECT_VERSION settings have drifted")
    build = next(iter(current))
    if not re.fullmatch(BUILD_VERSION, build) and REFERENCES.get(build) != "MARKETING_VERSION":
        raise ValueError("CURRENT_PROJECT_VERSION is invalid or cyclic")
    resolved = {"MARKETING_VERSION": version, "CURRENT_PROJECT_VERSION":
                version if build in REFERENCES else build}
    with (root / PLIST).open("rb") as stream:
        plist = plistlib.load(stream)
    if not isinstance(plist, dict):
        raise ValueError("Source Info.plist must be a dictionary")
    value = plist.get("CFBundleShortVersionString")
    if not isinstance(value, str) or resolved.get(REFERENCES.get(value), value) != version:
        raise ValueError("CFBundleShortVersionString is missing, invalid, unresolved or has drifted")
    if "CFBundleVersion" in plist:
        value = plist["CFBundleVersion"]
        if not isinstance(value, str) or not re.fullmatch(
            BUILD_VERSION, resolved.get(REFERENCES.get(value), value)
        ):
            raise ValueError("CFBundleVersion is invalid or unresolved")
    localized = (root / LOCALIZED).read_text(encoding="utf-8-sig")
    for pattern in (LOCALIZED_SHORT, LOCALIZED_INFO):
        if [match[2] for match in pattern.finditer(localized)] != [version]:
            raise ValueError("Localized source version is missing, invalid or has drifted")
    return version


def bump(mode, root=Path(".")):
    current = read(root)
    index = ("major", "minor", "patch").index(mode)
    parts = list(map(int, current.split(".")))
    parts[index] += 1
    parts[index + 1:] = [0] * (2 - index)
    new = ".".join(map(str, parts))

    def replace(match):
        if match[2] != "MARKETING_VERSION":
            return match[0]
        return f"{match[1]}{new}{match[4]}"

    path = root / PROJECT
    path.write_text(SETTING.sub(replace, path.read_text()))
    path = root / PLIST
    path.write_text(re.sub(
        r"(<key>CFBundleShortVersionString</key>\s*<string>)([^<]*)(</string>)",
        lambda m: m[0] if m[2] in REFERENCES else f"{m[1]}{new}{m[3]}",
        path.read_text(),
    ))
    path = root / LOCALIZED
    text = path.read_text(encoding="utf-8-sig")
    for pattern in (LOCALIZED_SHORT, LOCALIZED_INFO):
        text = pattern.sub(lambda m: f"{m[1]}{new}{m[3]}", text)
    path.write_text(text, encoding="utf-8-sig")
    if read(root) != new:
        raise ValueError("Bumped metadata did not validate")
    return new


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=("patch", "minor", "major"))
    args = parser.parse_args()
    print(bump(args.bump) if args.bump else read())
