import os
import fnmatch
import argparse
import sys
from typing import List, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including sample directory,
                            reference directory, work directory and lookup mask.
    """
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
        help="Used as the output directory for stages/files.json",
    )
    parser.add_argument(
        "--lookup-mask", default="*.jfr", help="File mask to identify profiles"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print full traceback on error for debugging purposes"
    )
    return parser.parse_args()


def write_output(
    reference_files: List[utils.Path], sample_files: List[utils.Path], output_file: utils.Path
) -> None:
    """
    Writes reference and sample files into a JSON array.

    Args:
        reference_files (List[utils.Path]): List of reference file paths.
        sample_files (List[utils.Path]): List of sample file paths.
        output_file (utils.Path): Destination path for the JSON output.

    Raises:
        PipelineError: If the number of reference files is not exactly one.
    """
    if len(reference_files) != 1:
        raise utils.PipelineError(
            f"Expected exactly one reference file, found: {len(reference_files)}, {reference_files}"
        )

    combined_data = [
        {"type": "reference", "source_file": reference_files[0]},
        *[{"type": "sample", "source_file": sf} for sf in sample_files],
    ]

    utils.save_json(combined_data, output_file)


def find_artifacts(
    reference_dir: utils.Path, sample_dir: utils.Path, lookup_mask: str
) -> Tuple[List[utils.Path], List[utils.Path]]:
    """
    Finds and classifies profiling files as reference or sample.

    Recursively searches in both reference and sample directories for files
    matching the provided mask. Ensures that reference files are excluded
    from the sample list.

    Args:
        reference_dir (utils.Path): Directory containing a single reference profile file.
        sample_dir (utils.Path): Directory containing multiple sample (unit test) profile files.
        lookup_mask (str): Filename pattern to match (e.g., '*.jfr').

    Returns:
        Tuple[List[utils.Path], List[utils.Path]]: A tuple containing:
            - reference_files (List[utils.Path]): List of matched reference file paths.
            - sample_files (List[utils.Path]): List of matched sample file paths (excluding references).

    Raises:
        PipelineError: If an error occurs during file discovery.
    """
    try:
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
    except Exception as e:
        raise utils.PipelineError(f"Failed to search for artifacts: {e}")


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to generate a JSON file with classified profiling artifacts.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        FileNotFoundError: If the working directory does not exist.
    """
    work_dir = os.path.abspath(args.work_dir)
    reference_dir = os.path.abspath(args.reference_dir)
    sample_dir = os.path.abspath(args.sample_dir)
    lookup_mask = args.lookup_mask

    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")

    stages_dir = os.path.join(work_dir, "stages")
    os.makedirs(os.path.dirname(stages_dir), exist_ok=True)
    utils.reset_output(stages_dir)

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
    write_output(reference_files, sample_files, output_json_path)


if __name__ == "__main__":

    utils.parse_args_and_run(parse_arguments, run_pipeline)
