import os
import fnmatch
import json
import shutil
import argparse
import sys

STAGES_DIR = os.path.join("stages", "stage1")
REFERENCE_DIR = ""
SAMPLE_DIR = ""


def ensure_stages_dir():
    """
    Ensure the stages directory exists, or create it by removing and recreating
    """
    try:
        if os.path.exists(STAGES_DIR):
            shutil.rmtree(STAGES_DIR)
        os.makedirs(STAGES_DIR)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to ensure stages directory: {e}\n")
        sys.exit(1)  # Return code 1 for failure in ensuring stages directory


def write_intermediate_json(file_type: str, file_path: str, index: int):
    """
    Creates an intermediate JSON file in the stages/stage1 directory with a fixed name format.
    """
    try:
        data = {
            "type": file_type,
            "source_file": file_path
        }
        # Use a fixed name format: input_0000.json, input_0001.json, etc.
        filename = f"input_{index:04}.json"
        output_path = os.path.join(STAGES_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved {file_type} file: {output_path}")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to write JSON file for {file_type}: {e}\n")
        sys.exit(2)  # Return code 2 for failure in writing JSON


def find_and_store_artifacts(base_dir: str, mask: str):
    """
    Searches for files using the given mask and stores information about them as intermediate artifacts.
    """
    reference_file_id = 0
    trace_file_id = 1

    try:
        for root, _, files in os.walk(base_dir):
            for filename in files:
                if fnmatch.fnmatch(filename, mask):
                    full_path = os.path.abspath(os.path.join(root, filename))

                    if REFERENCE_DIR in full_path:
                        write_intermediate_json("reference", full_path, reference_file_id)
                    elif SAMPLE_DIR in full_path:
                        write_intermediate_json("sample", full_path, trace_file_id)
                        trace_file_id += 1
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to find and store artifacts: {e}\n")
        sys.exit(3)  # Return code 3 for failure in finding and storing artifacts


def main():
    parser = argparse.ArgumentParser(description="Find and classify profiling files.")
    parser.add_argument("--sample-dir", required=True, help="Directory with unit test profiles")
    parser.add_argument("--reference-dir", required=True, help="Directory with target profile")
    parser.add_argument("--work-dir", required=True, help="Directory to store intermediate artifacts")
    parser.add_argument("--lookup-mask", default="*.jfr", help="File mask to identify profiles")

    args = parser.parse_args()

    try:
        run_dir = os.path.abspath(args.work_dir)
        reference_dir = os.path.abspath(args.reference_dir)
        sample_dir = os.path.abspath(args.sample_dir)
        lookup_mask = args.lookup_mask

        if not os.path.exists(run_dir):
            raise FileNotFoundError(f"WORK_DIR {run_dir} does not exist.")

        global REFERENCE_DIR, SAMPLE_DIR
        REFERENCE_DIR = reference_dir
        SAMPLE_DIR = sample_dir

        print(f"WORK_DIR: {run_dir}")
        print(f"REFERENCE_DIR: {REFERENCE_DIR}")
        print(f"SAMPLE_DIR: {SAMPLE_DIR}")
        print(f"LOOKUP_MASK: {lookup_mask}")

        ensure_stages_dir()
        find_and_store_artifacts(run_dir, lookup_mask)

    except FileNotFoundError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(4)  # Return code 4 for missing directory (WORK_DIR, REFERENCE_DIR, SAMPLE_DIR)

    except Exception as e:
        sys.stderr.write(f"[ERROR] An unexpected error occurred: {e}\n")
        sys.exit(5)  # Return code 5 for general errors


if __name__ == "__main__":
    main()
