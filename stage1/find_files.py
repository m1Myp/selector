import os
import fnmatch
import json
import shutil
import argparse
import sys
from typing import List, Tuple


# Ensures the "stages" directory is reset and ready for output
# Deletes it if it exists and creates a new one
def reset_stages_dir(stages_dir: str) -> None:
    try:
        if os.path.exists(stages_dir):
            try:
                shutil.rmtree(stages_dir)
            except Exception as e:
                sys.stderr.write(
                    f"[ERROR] Failed to delete folder '{stages_dir}': {e}\n"
                )
                sys.exit(1)
        os.makedirs(stages_dir)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to ensure stages directory: {e}\n")
        sys.exit(2)


# Recursively searches for files matching the mask in the reference and sample directories
# Ensures that reference files are excluded from the sample files list
# Returns two lists: one for reference files and one for sample files
def find_artifacts(
    reference_dir: str, sample_dir: str, lookup_mask: str
) -> Tuple[List[str], List[str]]:
    reference_files = []
    sample_files = []

    for folder, _, files in os.walk(reference_dir):
        for filename in files:
            if fnmatch.fnmatch(filename, lookup_mask):
                full_path = os.path.abspath(os.path.join(folder, filename))
                reference_files.append(full_path)

    for folder, _, files in os.walk(sample_dir):
        for filename in files:
            if fnmatch.fnmatch(filename, lookup_mask):
                full_path = os.path.abspath(os.path.join(folder, filename))
                if full_path not in reference_files:
                    sample_files.append(full_path)

    return reference_files, sample_files


# Writes the found reference and sample files into a single JSON array
# Ensures only one reference file is included. Outputs to the specified file path
def write_output_json(
    reference_files: List[str], sample_files: List[str], output_file: str
) -> None:
    if len(reference_files) != 1:
        sys.stderr.write(
            "[ERROR] Expected exactly one reference file. Found: {}\n".format(
                len(reference_files)
            )
        )
        sys.exit(3)

    combined_data = [
        {"type": "reference", "source_file": reference_files[0]},
        *[
            {"type": "sample", "source_file": sample_file}
            for sample_file in sample_files
        ],
    ]

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"[+] JSON written to: {output_file}")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to write output JSON: {e}\n")
        sys.exit(4)


# Parses command-line arguments required for the script to run
# Includes paths to sample, reference, and work directories, and a filename mask
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find and classify profiling files.")
    parser.add_argument(
        "--sample-dir", required=True, help="Directory with unit test profiles"
    )
    parser.add_argument(
        "--reference-dir", required=True, help="Directory with target profile"
    )
    parser.add_argument(
        "--work-dir",
        required=True,
        help="Directory to store intermediate artifacts",
    )
    parser.add_argument(
        "--lookup-mask",
        default="*.jfr",
        help="File mask to identify profiles",
    )
    return parser.parse_args()


# Main processing pipeline that ties all functions together
# Validates inputs, prepares workspace, and outputs results to a file
def run_pipeline(args: argparse.Namespace) -> None:
    work_dir = os.path.abspath(args.work_dir)
    reference_dir = os.path.abspath(args.reference_dir)
    sample_dir = os.path.abspath(args.sample_dir)
    lookup_mask = args.lookup_mask

    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")

    stages_dir = os.path.join(work_dir, "stages")
    os.makedirs(os.path.dirname(stages_dir), exist_ok=True)
    reset_stages_dir(stages_dir)

    print(f"[INFO] WORK_DIR:      {work_dir}")
    print(f"[INFO] REFERENCE_DIR: {reference_dir}")
    print(f"[INFO] SAMPLE_DIR:    {sample_dir}")
    print(f"[INFO] LOOKUP_MASK:   {lookup_mask}")

    reference_files, sample_files = find_artifacts(
        reference_dir, sample_dir, lookup_mask
    )
    print(f"[INFO] Found {len(reference_files)} reference file(s)")
    print(f"[INFO] Found {len(sample_files)} sample file(s)")

    output_json_path = os.path.join(stages_dir, "files.json")
    write_output_json(reference_files, sample_files, output_json_path)


# Entry point for the script: gets arguments and runs the pipeline
def main() -> None:
    args = parse_arguments()
    try:
        run_pipeline(args)
    except FileNotFoundError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(5)
    except Exception as e:
        sys.stderr.write(f"[ERROR] An unexpected error occurred: {e}\n")
        sys.exit(6)


if __name__ == "__main__":
    main()
