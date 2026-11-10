#!/usr/bin/env python3
"""Compile real sources plus the unchanged SDK; no project/release phases run."""
import argparse
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "f429a2b58c0533a73f2c9fc727d6882d7df4d572"
CASES = (
    "path", "bytes", "copy-units", "copy-owners", "gray-owners", "size-owners",
    "handoffs", "failure", "borrowed-param",
    "picture-create-failure", "arrays", "scalars",
)
DEFECTS = {"path", "bytes", "copy-units", "copy-owners", "gray-owners",
           "size-owners", "handoffs", "failure", "borrowed-param"}
MARKERS = {
    "path": "path alias disposed twice",
    "bytes": "all picture references balanced",
    "copy-units": "AddressSanitizer: heap-buffer-overflow",
    "gray-owners": "all picture references balanced",
    "copy-owners": ("ownership assertion: copy-owners", "all picture references balanced"),
    "size-owners": "all picture references balanced",
    "handoffs": "all picture references balanced",
    "failure": "all picture references balanced",
    "borrowed-param": "all picture references balanced",
}


def build(source, output):
    api = source / "4D Plugin API"
    subprocess.run([
        "clang++", "-std=c++11", "-x", "objective-c++",
        "-include", "Carbon/Carbon.h", "-I", str(api),
        "-I", str(api / "Classes"), "-g", "-O1",
        "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
        "-fno-omit-frame-pointer", "-Wno-deprecated-declarations",
        "-Wno-logical-op-parentheses", "-Wno-writable-strings",
        str(api / "4DPluginAPI.c"), str(source / "4DPlugin.cpp"),
        *map(str, sorted((api / "Classes").glob("*.cpp"))),
        str(ROOT / "tests/ownership/host.mm"),
        "-framework", "Cocoa", "-framework", "Carbon",
        "-o", str(output),
    ], check=True)


def run(binary, logs, baseline=False):
    failures = set()
    for case in CASES:
        for empty in ("allocated", "null"):
            result = subprocess.run(
                [str(binary), case, empty], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
                     "UBSAN_OPTIONS": "halt_on_error=1"},
            )
            (logs / f"{case}-{empty}.log").write_text(result.stdout)
            expected_failure = baseline and case in DEFECTS
            assert bool(result.returncode) == expected_failure, (
                f"Unexpected result for {case}/{empty}:\n{result.stdout}"
            )
            if result.returncode:
                failures.add(case)
                print(f"{'EXPECTED BASELINE FAILURE' if baseline else 'FAIL'} {case}/{empty}")
                if baseline and case in MARKERS:
                    markers = MARKERS[case]
                    if isinstance(markers, str):
                        markers = (markers,)
                    assert any(marker in result.stdout for marker in markers), result.stdout
                if not baseline:
                    print(result.stdout)
            else:
                print(result.stdout.strip())
    if baseline:
        assert failures == DEFECTS, failures
    else:
        assert not failures, f"Fixed source failures: {failures}"

    result = subprocess.run(
        [str(binary), "deferred-array-create"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
             "UBSAN_OPTIONS": "halt_on_error=1"},
    )
    (logs / "deferred-array-create.log").write_text(result.stdout)
    assert result.returncode and "DEFERRED: initial array creation" in result.stdout, result.stdout
    print("DEFERRED (not a passing regression): initial array allocation failure")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true", help="also run immutable baseline")
    parser.add_argument("--output", type=Path, required=True, help="scratch output, outside tracked products")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    build(ROOT, args.output / "fixed")
    run(args.output / "fixed", args.output)
    if args.baseline:
        with tempfile.TemporaryDirectory(prefix="ownership-baseline-") as directory:
            baseline = Path(directory)
            archive = baseline / "baseline.tar"
            with archive.open("wb") as stream:
                subprocess.run(["git", "archive", BASELINE], cwd=ROOT, stdout=stream, check=True)
            with tarfile.open(archive) as source:
                source.extractall(baseline, filter="data")
            # Every original tracked file is preserved except these intentional edits.
            exemptions = {"4D Plugin API/Classes/C_PICTURE.cpp", "README.md"}
            tracked = subprocess.check_output(
                ["git", "ls-tree", "-r", "-z", BASELINE], cwd=ROOT,
            ).decode().split("\0")
            for entry in filter(None, tracked):
                metadata, name = entry.split("\t", 1)
                mode = metadata.split()[0]
                path = baseline / name
                if name not in exemptions:
                    assert path.read_bytes() == (ROOT / path.relative_to(baseline)).read_bytes(), path
                assert bool((ROOT / name).stat().st_mode & 0o111) == (mode == "100755"), name
            build(baseline, args.output / "baseline")
            logs = args.output / "baseline-logs"
            logs.mkdir(exist_ok=True)
            run(args.output / "baseline", logs, baseline=True)


if __name__ == "__main__":
    main()
