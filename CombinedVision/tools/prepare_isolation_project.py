"""Export the combined Q/E offline test project using MOD source only.

No game file, Steam connection, original resource, or previous build is needed.
The standalone E source remains unchanged; combined settings are exported to a
separate new directory. Run Godot 4.1.1 against the resulting project.
"""
import argparse
from pathlib import Path
import shutil

from build_variants import ROOT, RUNTIME_FILES, configure_combined_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Test project destination already exists; refusing overwrite")
    runtime = {"res://ProbabilityVision/" + name: (ROOT / "ProbabilityVision" / name).read_bytes()
               for name in RUNTIME_FILES}
    combined = configure_combined_runtime(runtime)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in combined.items():
        target = args.output / name.removeprefix("res://")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    files = ("project.godot", "ProbabilityVision/tests/run_tests.gd",
             "CombinedVision/QSingleplayer.gdfrag", "CombinedVision/QMultiplayer.gdfrag",
             "CombinedVision/tests/run_isolation_tests.gd", "CombinedVision/tests/render_preview.gd")
    for name in files:
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    print(f"Offline combined test project exported: {args.output}")


if __name__ == "__main__":
    main()
