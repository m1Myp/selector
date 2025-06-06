import sys
import argparse
from typing import List, Tuple
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including sample directory,
                            reference directory, work directory and lookup mask.
    """
    parser = argparse.ArgumentParser(description="Find and classify profiling files")
    parser.add_argument(
        "--sample-dir",
        required=True,
        type=Path,
        help="Directory with unit test profiles",
    )
    parser.add_argument(
        "--reference-dir",
        required=True,
        type=Path,
        help="Directory with target profile",
    )
    parser.add_argument(
        "--lookup-mask", default="*.jfr", help="File mask to identify profiles"
    )
    parser.add_argument(
        "--work-dir",
        required=True,
        type=Path,
        help="Used as the output directory for stages/files.json",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print full traceback on error"
    )
    return parser.parse_args()


def write_output(
    reference_files: List[Path], sample_files: List[Path], output_file: Path
) -> None:
    """
    Writes reference and sample files into a JSON array.

    Args:
        reference_files (List[Path]): List of reference file paths.
        sample_files (List[Path]): List of sample file paths.
        output_file (Path): Destination path for the JSON output.

    Raises:
        PipelineError: If the number of reference files is not exactly one.
    """
    if len(reference_files) != 1:
        raise utils.PipelineError(
            f"Expected exactly one reference file, found: {len(reference_files)}, {reference_files}."
        )

    combined_data = [
        {"type": "reference", "source_file": str(reference_files[0])},
        *[{"type": "sample", "source_file": str(sf)} for sf in sample_files],
    ]

    utils.save_json(combined_data, output_file)


def find_artifacts(
    reference_dir: Path, sample_dir: Path, lookup_mask: str
) -> Tuple[List[Path], List[Path]]:
    """
    Finds and classifies profiling files as reference or sample.

    Recursively searches in both reference and sample directories for files
    matching the provided mask. Ensures that reference files are excluded
    from the sample list.

    Args:
        reference_dir (Path): Directory containing a single reference profile file.
        sample_dir (Path): Directory containing multiple sample (unit test) profile files.
        lookup_mask (str): Filename pattern to match (e.g., '*.jfr').

    Returns:
        Tuple[List[Path], List[Path]]: A tuple containing:
            - reference_files (List[Path]): List of matched reference file paths.
            - sample_files (List[Path]): List of matched sample file paths (excluding references).

    Raises:
        PipelineError: If an error occurs during file discovery.
    """
    try:
        if lookup_mask.startswith("*."):
            required_suffix = lookup_mask[1:]
        else:
            raise utils.PipelineError(f"Unsupported mask format: {lookup_mask}.")

        reference_files = [
            p.resolve()
            for p in reference_dir.rglob("*")
            if p.is_file() and p.suffix == required_suffix
        ]

        sample_files = [
            p.resolve()
            for p in sample_dir.rglob("*")
            if p.is_file()
            and p.suffix == required_suffix
            and p.resolve() not in reference_files
        ]

        return reference_files, sample_files
    except Exception as e:
        raise utils.PipelineError(f"Failed to search for artifacts: {e}")


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to generate a JSON file with classified profiling artifacts.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    work_dir = args.work_dir.resolve()
    reference_dir = args.reference_dir.resolve()
    sample_dir = args.sample_dir.resolve()
    lookup_mask = args.lookup_mask

    utils.validate_work_dir_exists(work_dir)

    stages_dir = work_dir / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)
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

    output_json_path = stages_dir / "files.json"
    write_output(reference_files, sample_files, output_json_path)


if __name__ == "__main__":
    utils.parse_args_and_run(parse_arguments, run_pipeline)
