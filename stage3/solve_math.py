import sys
import json
import argparse
import numpy as np
import cvxpy as cp
from typing import List, Tuple, Dict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including work directory, maximum selected samples and minimum similarity.
    """
    parser = argparse.ArgumentParser(
        description="Optimize sample files weights for similarity to target histogram"
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=95.0,
        help="Minimum similarity threshold (0-100%) (default: 95.0)",
    )
    parser.add_argument(
        "--max-selected-samples",
        type=int,
        default=5,
        help="Maximum number of selected sample files (default: 5)",
    )
    parser.add_argument(
        "--time-limit-seconds",
        type=int,
        default=60,
        help="Maximum time limit for solver in seconds (default: 60)",
    )
    parser.add_argument(
        "--threads-count",
        type=int,
        default=4,
        help="Maximum number of threads for solver (default: 4)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Working directory containing stages/histos.json;"
        "also used as the output directory for stages/weight.json",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logs from the solver",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print full traceback on error for debugging purposes",
    )
    return parser.parse_args()


def normalize(vector: np.ndarray) -> np.ndarray:
    """
    Normalizes a vector to sum to 100.

    Args:
        vector (np.ndarray): Input vector to normalize.

    Returns:
        np.ndarray: Normalized vector.
    """
    total = np.sum(vector)
    return (vector / total) * 100 if total > 0 else np.zeros_like(vector)


def compute_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Computes similarity between two vectors as the sum of minimum values.

    Args:
        a (np.ndarray): First vector.
        b (np.ndarray): Second vector.

    Returns:
        float: Similarity score between the two vectors.
    """
    return np.minimum(a, b).sum().item()


def load_histograms(
    input_path: Path,
) -> Tuple[
    utils.HistosJsonEntry,
    List[utils.HistosJsonEntry],
    List[str],
    Dict[str, int],
]:
    """
    Loads histograms from the specified JSON file.

    Args:
        input_path (Path): Path to the input JSON file.

    Returns:
        Tuple[utils.HistosJsonEntry, List[utils.HistosJsonEntry], List[str], Dict[str, int]]:
            - reference (utils.HistosJsonEntry): JSON entry for the reference histogram.
            - samples (List[utils.HistosJsonEntry]): List of JSON entries for sample histograms.
            - all_ids (List[str]): List of all unique IDs across histograms.
            - identifiers_to_index (Dict[str, int]): Mapping from each ID to its index.

    Raises:
        ValueError: If the reference histogram is missing, duplicated, empty, or if no sample histograms are found.
    """
    data = utils.load_files_json(input_path)

    schema_path = Path(__file__).resolve().parent / "input_file_schema.json"
    with utils.open_with_default_encoding(schema_path, "r") as f:
        input_file_schema = json.load(f)
    utils.validate_json(data, input_file_schema)

    references = [d for d in data if d["type"] == "reference"]
    if not references:
        raise ValueError("No reference histogram found.")
    if len(references) > 1:
        raise ValueError(
            f"Expected exactly one reference histogram, found: {len(references)}, {references}."
        )
    reference = references[0]
    if not reference.get("histo"):
        raise ValueError("Reference histogram is empty.")

    samples = [d for d in data if d["type"] == "sample" and d["histo"]]

    if not samples:
        raise ValueError("Sample histograms not found.")

    all_ids = sorted(
        set(reference["histo"].keys()).union(*(s["histo"].keys() for s in samples))
    )
    identifiers_to_index = {id_: i for i, id_ in enumerate(all_ids)}

    if isinstance(reference.get("source_file"), int):
        reference["source_file"] = str(reference["source_file"])

    return reference, samples, all_ids, identifiers_to_index


def prepare_vectors(
    reference: utils.HistosJsonEntry,
    samples: List[utils.HistosJsonEntry],
    identifiers_to_index: Dict[str, int],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepares the target vector and sample vectors based on the histograms.

    Args:
        reference (utils.HistosJsonEntry): JSON entry for the reference histogram.
        samples (List[utils.HistosJsonEntry]): List of JSON entries for sample histograms.
        identifiers_to_index (Dict[str, int]): Mapping from each ID to its index.

    Returns:
        Tuple[np.ndarray, np.ndarray]:
            - target (np.ndarray): The normalized target vector.
            - sample_vectors (np.ndarray): Array of sample vectors.
    """
    target = np.zeros(len(identifiers_to_index))
    for k, v in reference["histo"].items():
        target[identifiers_to_index[k]] = v
    target = normalize(target)

    sample_vectors = []
    for sample in samples:
        vec = np.zeros(len(identifiers_to_index))
        for k, v in sample["histo"].items():
            vec[identifiers_to_index[k]] = v
        vec = normalize(vec)
        sample_vectors.append(vec)

    return target, np.array(sample_vectors)


def solve_optimization(
    sample_vectors: np.ndarray,
    target: np.ndarray,
    max_selected: int,
    time_limit: int,
    threads: int,
    verbose: bool,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solves the optimization problem to find the best weights for matching the target histogram.

    Args:
        sample_vectors (np.ndarray): Array of sample vectors.
        target (np.ndarray): The target vector to match.
        max_selected (int): Maximum number of samples to select.
        time_limit (int): Time limit for the solver in seconds.
        threads (int): Maximum number of threads the solver can use.
        verbose (bool): Whether to enable verbose logging from the solver.

    Returns:
        Tuple[np.ndarray, np.ndarray]:
            - weights (np.ndarray): Optimized weights for each sample.
            - result_vector (np.ndarray): Resulting weighted sum of sample vectors.

    Raises:
        RuntimeError: If the optimization solver fails.
    """
    n = len(sample_vectors)
    w = cp.Variable(n)
    z = cp.Variable(n, boolean=True)

    constraints = [w >= 0, w <= z, cp.sum(z) <= max_selected, cp.sum(w) == 1]
    objective = cp.Minimize(cp.sum(cp.abs(sample_vectors.T @ w - target)))
    problem = cp.Problem(objective, constraints)

    scip_params = {
        "limits/time": time_limit,
        "parallel/maxnthreads": threads,
    }
    if verbose:
        scip_params.update(
            {
                "display/verblevel": 5,
                "display/freq": 1,
            }
        )

    problem.solve(
        solver=cp.SCIP,
        scip_params=scip_params,
        verbose=verbose,
    )

    if problem.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
        raise RuntimeError("Optimization failed.")

    return w.value, sample_vectors.T @ w.value


def write_output(
    output_path: Path,
    reference_file_path: Path,
    sample_files_paths: List[Path],
    similarity: float,
    weights: np.ndarray,
) -> None:
    """
    Writes the optimization results to a JSON file, rounding weights to 4 decimals
    and adjusting to ensure the sum is exactly 1.0.

    Args:
        output_path (Path): Path to the output JSON file.
        reference_file_path (Path): Path to the reference file.
        sample_files_paths (List[Path]): File paths for each selected sample file.
        similarity (float): Similarity score of the result.
        weights (np.ndarray): Weights for each selected sample file.

    Raises:
        ValueError: If weights cannot be normalized to sum to 1.0.
    """

    selected_raw = [
        (sample_files_paths[i], weights[i])
        for i in range(len(weights))
        if weights[i] > 1e-6
    ]

    rounded_weights = [round(w, 4) for _, w in selected_raw]

    diff = round(1.0 - sum(rounded_weights), 4)

    if abs(diff) >= 0.0001:
        for i in range(len(rounded_weights)):
            adjusted = round(rounded_weights[i] + diff, 4)
            if 0 <= adjusted <= 1:
                rounded_weights[i] = adjusted
                break
        else:
            raise ValueError("Unable to normalize weights to sum to 1.0.")

    selected = [
        {"sample_path": selected_raw[i][0], "weight": rounded_weights[i]}
        for i in range(len(rounded_weights))
    ]

    output_weight_data = {
        "reference_file": reference_file_path,
        "similarity": round(similarity, 2),
        "selected_samples": selected,
    }

    utils.save_json(output_weight_data, output_path)


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to solve math task, and generating the output weight JSON file.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    work_dir = args.work_dir.resolve()
    max_selected_samples = args.max_selected_samples
    min_similarity = args.min_similarity
    time_limit_seconds = args.time_limit_seconds
    threads_count = args.threads_count
    verbose = args.verbose

    utils.validate_work_dir_exists(work_dir)

    print(f"[INFO] WORK_DIR:             {work_dir}")
    print(f"[INFO] MAX_SELECTED_SAMPLES: {max_selected_samples}")
    print(f"[INFO] MIN_SIMILARITY:       {min_similarity}")
    print(f"[INFO] TIME_LIMIT_SECONDS:   {time_limit_seconds}")
    print(f"[INFO] THREADS_COUNT:        {threads_count}")

    input_path = work_dir / "stages" / "histos.json"
    output_path = work_dir / "stages" / "weight.json"

    reference, samples, all_identifiers, identifiers_to_index = load_histograms(
        input_path
    )
    target, sample_vectors = prepare_vectors(reference, samples, identifiers_to_index)

    weights, result_vector = solve_optimization(
        sample_vectors,
        target,
        max_selected_samples,
        time_limit_seconds,
        threads_count,
        verbose,
    )
    result_vector = normalize(result_vector)
    similarity = compute_similarity(result_vector, target)

    if similarity < min_similarity:
        print(
            f"[INFO] Similarity {similarity:.2f}% is below the minimum threshold. Selecting maximum samples"
        )
        weights, result_vector = solve_optimization(
            sample_vectors,
            target,
            len(sample_vectors),
            time_limit_seconds,
            threads_count,
            verbose,
        )
        result_vector = normalize(result_vector)
        similarity = compute_similarity(result_vector, target)

    write_output(
        output_path,
        reference["source_file"],
        [sample["source_file"] for sample in samples],
        similarity,
        weights,
    )

    print(f"[INFO] Optimization complete. Similarity: {similarity:.2f}%")
    selected_count = sum(w > 1e-6 for w in weights)
    total_count = len(weights)
    print(f"[INFO] Selected samples: {selected_count} / {total_count}")


if __name__ == "__main__":
    utils.parse_args_and_run(parse_arguments, run_pipeline)
