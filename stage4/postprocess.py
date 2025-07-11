import sys
import json
import argparse
import shutil
from tqdm import tqdm
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including
        how many directory levels upward from the sample and reference files the artifacts should be copied.
    """
    parser = argparse.ArgumentParser(
        description="Postprocess stage: copy artifacts and write weight file"
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
        type=Path,
        required=True,
        help="Working directory containing stages/weight.json;"
        "also used as the output directory for artifacts and the weight file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print full traceback on error for debugging purposes",
    )
    return parser.parse_args()


def copy_artifact(source_file: Path, depth: int, destination_root: Path) -> str:
    """
    Copies the artifact starting from a source file upward to the specified depth.

    Args:
        source_file (Path): Path to the profile file.
        depth (int): Number of levels upward to determine the artifact root.
        destination_root (Path): Root directory where artifacts are copied.

    Returns:
        str: Name of the top artifact folder copied.
    """

    if depth < 0:
        raise ValueError(f"Invalid artifact depth: {depth}. Must be >= 0")

    path = Path(source_file).resolve()

    current = path
    for _ in range(depth):
        current = current.parent
        if current.name in {"selector"}:
            raise ValueError(
                f"Invalid artifact copy: encountered forbidden folder '{current.name}' "
                f"while traversing {depth} levels up from {original_path}"
            )
    
    if depth == 0:
        destination = destination_root / path.name
        shutil.copy2(path, destination)
        return path.name

    for _ in range(depth):
        path = path.parent

    destination_path = destination_root / path.name
    shutil.copytree(path, destination_path, dirs_exist_ok=True)
    return path.name


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to copying artifact folders, and generating the output weight file.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    work_dir = args.work_dir.resolve()
    reference_artifact_depth = args.reference_artifact_depth
    sample_artifact_depth = args.sample_artifact_depth

    utils.validate_work_dir_exists(work_dir)

    print(f"[INFO] WORK_DIR:                 {work_dir}")
    print(f"[INFO] REFERENCE_ARTIFACT_DEPTH: {reference_artifact_depth}")
    print(f"[INFO] SAMPLE_ARTIFACT_DEPTH:    {sample_artifact_depth}")

    weight_json_path = work_dir / "stages" / "weight.json"
    output_weight_path = work_dir / "weight"

    input_data = utils.load_files_json(weight_json_path)
    schema_path = Path(__file__).resolve().parent / "input_file_schema.json"
    with utils.open_with_default_encoding(schema_path, "r") as f:
        input_file_schema = json.load(f)
    utils.validate_json(input_data, input_file_schema)

    output_weight_lines = []

    copy_artifact(input_data["reference_file"], reference_artifact_depth, work_dir)

    selected_samples = input_data["selected_samples"]
    total_selected = len(selected_samples)

    for i, sample in enumerate(
        tqdm(selected_samples, desc="Copying samples", unit="sample"), start=1
    ):
        artifact_root = Path(sample["sample_path"]).resolve()
        for _ in range(sample_artifact_depth):
            artifact_root = artifact_root.parent
        dst_path = work_dir / artifact_root.name

        tqdm.write(
            f"[INFO] Copying [{i}/{total_selected}]: {artifact_root} -> {dst_path}"
        )
        try:
            name = copy_artifact(sample["sample_path"], sample_artifact_depth, work_dir)
        except Exception as e:
            raise utils.PipelineError(
                f"Cant copy an artifact {sample['sample_path']}: {e}"
            )
        output_weight_lines.append(f"{name} {sample['weight']}")

    utils.reset_output(output_weight_path)
    with utils.open_with_default_encoding(output_weight_path, "w") as f:
        for line in output_weight_lines:
            f.write(line + "\n")

    print(f"[INFO] Artifacts copied and weight file created at {work_dir}")


if __name__ == "__main__":
    utils.parse_args_and_run(parse_arguments, run_pipeline)
