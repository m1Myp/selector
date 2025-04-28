import os
import sys
import json
import argparse
import subprocess


# Parses the command-line arguments for the script to extract necessary input parameters.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract histograms from profile files."
    )
    parser.add_argument("--work-dir", type=str, required=True, help="Working directory")
    parser.add_argument(
        "--lookup-mask",
        type=str,
        required=True,
        help="Hint for file format processing (.jfr, .histo, etc.)",
    )
    parser.add_argument(
        "--block-compression",
        type=str,
        default="true",
        help="Enable block compression (true/false)",
    )
    parser.add_argument(
        "--hotness-compression",
        type=int,
        default=97,
        help="Percentage for hotness compression (0-100)",
    )
    return parser.parse_args()


# If the "stages/histos.json" file exists, it will be deleted.
def reset_histos_json(histos_json_path: str) -> None:
    if os.path.exists(histos_json_path):
        try:
            os.remove(histos_json_path)
        except Exception as e:
            sys.stderr.write(
                f"[ERROR] Failed to delete file '{histos_json_path}': {e}\n"
            )
            sys.exit(1)


# Loads a list of profile entries from the specified JSON file.
def load_files_json(files_json_path: str) -> list:
    try:
        with open(files_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to load files.json: {e}\n")
        sys.exit(2)


# Loads a profile entry based on the file format indicated by the lookup mask.
# The mask determines whether to load a .histo or .jfr file.
def load_profile(entry: dict, work_dir: str, lookup_mask: str) -> dict:
    file_path = entry["source_file"]
    if lookup_mask == "*.histo":
        return load_histo(file_path)
    elif lookup_mask == "*.jfr":
        return load_jfr(file_path, work_dir)
    else:
        sys.stderr.write(f"[ERROR] Unsupported lookup mask: {lookup_mask}\n")
        sys.exit(3)


# Loads histogram data from a .histo file. Each line contains a function name and a count.
def load_histo(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = []
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    try:
                        function_name = parts[0]
                        number = int(parts[1])
                        data.append((function_name, number))
                    except ValueError:
                        sys.stderr.write(
                            f"[ERROR] Invalid number format in file "
                            f"'{file_path}' at line {line_num}: {line}\n"
                        )
                        sys.exit(4)
                else:
                    sys.stderr.write(
                        f"[ERROR] Invalid line in file "
                        f"'{file_path}' at line {line_num}: {line}\n"
                    )
                    sys.exit(5)

            result = {func: val for func, val in data}
    except Exception as e:
        sys.stderr.write(f"[ERROR] Error reading the file {file_path}: {e}\n")
        sys.exit(6)
    return result


# Uses an external Java tool (JFRParser.jar) to parse a .jfr file and extract histogram data.
def load_jfr(file_path: str, work_dir: str) -> dict:
    stage_2_dir = os.path.join(work_dir, "stage2")
    jar_name = os.path.join(stage_2_dir, "JFRParser.jar")

    cmd = [
        "java",
        "-jar",
        jar_name,
        file_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        histo = {}
        for line in result.stdout.splitlines():
            method, count = line.split(": ")
            histo[method.strip('"')] = int(count)

        return histo

    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[ERROR] Failed to parse JFR file {file_path}: {e.stderr}\n")
        sys.exit(7)


# Processes each entry in the profile list, loading the histogram data for each.
# This function collects all histograms into a list of JSON-compatible dictionaries.
def build_json_entries(entries: list, work_dir: str, lookup_mask: str) -> list:
    result = []
    for entry in entries:
        histo = load_profile(entry, work_dir, lookup_mask)
        result.append(
            {"type": entry["type"], "source_file": entry["source_file"], "histo": histo}
        )
    return result


# Saves the generated list of histograms to a specified JSON file.
def save_json(histos: list, output_path: str) -> None:
    try:
        reset_histos_json(output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(histos, f, indent=2, ensure_ascii=False)
        print(f"[+] JSON written to: {output_path}")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to write histos.json: {e}\n")
        sys.exit(8)


# This function loads files, processes entries, and saves the results to a JSON file.
def run_pipeline(args: argparse.Namespace) -> None:
    work_dir = os.path.abspath(args.work_dir)
    lookup_mask = args.lookup_mask
    hotness_compression = args.hotness_compression
    block_compression = args.block_compression

    stages_dir = os.path.join(work_dir, "stages")
    files_json_path = os.path.join(stages_dir, "files.json")
    output_path = os.path.join(stages_dir, "histos.json")

    print(f"[INFO] WORK_DIR:            {work_dir}")
    print(f"[INFO] LOOKUP_MASK:         {lookup_mask}")
    print(f"[INFO] HOTNESS_COMPRESSION: {hotness_compression}")
    print(f"[INFO] BLOCK_COMPRESSION:   {block_compression}")

    entries = load_files_json(files_json_path)
    uncompressed_result = build_json_entries(entries, work_dir, lookup_mask)
    save_json(uncompressed_result, output_path)


# The main function, responsible for handling command-line arguments and running the pipeline.
def main() -> None:
    try:
        args = parse_args()
        run_pipeline(args)
    except FileNotFoundError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(9)
    except Exception as e:
        sys.stderr.write(f"[ERROR] An unexpected error occurred: {e}\n")
        sys.exit(10)


if __name__ == "__main__":
    main()
