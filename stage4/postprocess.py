import argparse
import sys
import os
import shutil

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including
        how many directory levels upward from the sample and reference files the artifacts should be copied.
    """
    parser = argparse.ArgumentParser(
        description="Postprocess stage: copy artifacts and write weight file."
    )
    parser.add_argument(
        "--reference-artifact-depth",
        type=int,
        default=2,
        help="Depth from reference profile to root artifact folder (default: 2)",
    )
    parser.add_argument(
        "--sample-artifact-depth",
        type=int,
        default=2,
        help="Depth from sample profile to root artifact folder (default: 2)",
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        required=True,
        help="Working directory containing stages/weight.json;"
        "also used as the output directory for artifacts and the weight file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print full traceback on error for debugging purposes"
    )
    return parser.parse_args()


def validate_weight_json(input_json_data: dict) -> None:
    """
    Validates the structure of a weight.json entry.

    Args:
        input_json_data (dict): A dictionary representing a JSON entry.

    Raises:
        PipelineError: If the structure is not as expected.
    """
    if not isinstance(input_json_data, dict):
        raise utils.PipelineError(
            f"Expected dictionary, got {type(input_json_data).__name__}"
        )

    required_keys = {"reference_file", "similarity", "selected_samples"}
    missing = required_keys - input_json_data.keys()
    if missing:
        raise utils.PipelineError(f"Missing required keys: {missing}")

    if not isinstance(input_json_data["selected_samples"], list):
        raise utils.PipelineError("`selected_samples` must be a list")

    for sample in input_json_data["selected_samples"]:
        if not isinstance(sample, dict):
            raise utils.PipelineError(
                "Each item in `selected_samples` must be a dictionary"
            )
        if "sample_path" not in sample or "weight" not in sample:
            raise utils.PipelineError(
                "Each sample test must contain `sample_path` and `weight` keys"
            )


def copy_artifact(source_file: utils.Path, depth: int, destination_root: utils.Path) -> utils.Path:
    """
    Copies the artifact starting from a source file upward to the specified depth.

    Args:
        source_file (utils.Path): Path to the profile file.
        depth (int): Number of levels upward to determine the artifact root.
        destination_root (utils.Path): Root directory where artifacts are copied.

    Returns:
        utils.Path: Name of the top artifact folder copied.
    """
    path = os.path.abspath(source_file)

    if depth == 0:
        destination = os.path.join(destination_root, os.path.basename(path))
        shutil.copy2(path, destination)
        return os.path.basename(path)

    for _ in range(depth):
        path = os.path.dirname(path)

    destination_path = os.path.join(destination_root, os.path.basename(path))
    shutil.copytree(path, destination_path, dirs_exist_ok=True)
    return os.path.basename(path)


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to copying artifact folders, and generating the output weight file.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        FileNotFoundError: If the working directory does not exist.
    """
    work_dir = os.path.abspath(args.work_dir)
    reference_artifact_depth = args.reference_artifact_depth
    sample_artifact_depth = args.sample_artifact_depth

    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")

    print(f"[INFO] WORK_DIR:                 {work_dir}")
    print(f"[INFO] REFERENCE_ARTIFACT_DEPTH: {reference_artifact_depth}")
    print(f"[INFO] SAMPLE_ARTIFACT_DEPTH:    {sample_artifact_depth}")

    weight_json_path = os.path.join(work_dir, "stages", "weight.json")
    output_weight_path = os.path.join(work_dir, "weight")

    input_data = utils.load_files_json(weight_json_path)

    validate_weight_json(input_data)

    output_weight_lines = []

    copy_artifact(input_data["reference_file"], reference_artifact_depth, work_dir)
    for selected_samples in input_data["selected_samples"]:
        name = copy_artifact(
            selected_samples["sample_path"], sample_artifact_depth, work_dir
        )
        output_weight_lines.append(f"{name} {selected_samples['weight']}")

    utils.reset_output(output_weight_path)
    with utils.open_with_default_encoding(output_weight_path, "w") as f:
        for line in output_weight_lines:
            f.write(line + "\n")

    print(f"[INFO] Artifacts copied and weight file created at {output_weight_path}")


if __name__ == "__main__":
    utils.main(parse_arguments, run_pipeline)
