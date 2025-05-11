import os
import sys
import argparse
import numpy as np
import cvxpy as cp
from typing import List, Tuple, Dict, Union

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including work directory, maximum selected samples and minimum similarity.
    """
    parser = argparse.ArgumentParser(description="Optimize sample files weights for similarity to target histogram")
    parser.add_argument("--work-dir", type=str, required=True, help="Working directory containing stages/histos.json;"
                                                                    "also used as the output directory for stages/weight.json")
    parser.add_argument("--max-selected-samples", type=int, default=5, help="Maximum number of selected sample files (default: 5)")
    parser.add_argument("--min-similarity", type=float, default=95.0, help="Minimum similarity threshold (0-100%) (default: 95.0)")
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
    return float(np.sum(np.minimum(a, b)))


def load_histograms(input_path: str) -> Tuple[Dict[str, Union[str, int]], List[Dict[str, int]], List[str], Dict[str, int]]:
    """
    Loads histograms from the specified JSON file.

    Args:
        input_path (str): Path to the input JSON file.

    Returns:
        Tuple[Dict[str, Union[str, int]], List[Dict[str, int]], List[str], Dict[str, int]]:
            - reference (Dict[str, Union[str, int]]): Reference histogram with source_file which could be str or int.
            - samples (List[Dict[str, int]]): List of sample histograms.
            - all_ids (List[str]): List of all unique IDs across histograms.
            - identifiers_to_index (Dict[str, int]): Mapping of IDs to indices.

    Raises:
        ValueError: If the reference histogram is empty.
    """
    data = utils.load_files_json(input_path)

    required_keys = {"type", "histo", "source_file"}
    for json_entry in data:
        utils.input_json_validation(json_entry, required_keys)

    reference = next((d for d in data if d["type"] == "reference"), None)
    if reference is None:
        raise ValueError("No reference histogram found.")

    if not reference.get("histo"):
        raise ValueError(f"Reference histogram is empty in '{reference.get('source_file', '<unknown>')}'")

    samples = [
        d for d in data
        if d["type"] == "sample" and d.get("histo") and isinstance(d["histo"], dict) and len(d["histo"]) > 0
    ]

    if not samples:
        raise ValueError("No valid sample histograms found.")

    all_identifiers = sorted(set().union(reference["histo"].keys(), *(d["histo"].keys() for d in samples)))
    identifiers_to_index = {id_: i for i, id_ in enumerate(all_identifiers)}

    if isinstance(reference.get("source_file"), int):
        reference["source_file"] = str(reference["source_file"])

    return reference, samples, all_identifiers, identifiers_to_index


def prepare_vectors(reference: Dict, samples: List[Dict], identifiers_to_index: Dict[str, int]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Prepares the target vector and sample vectors based on the histograms.

    Args:
        reference (Dict): The reference histogram.
        samples (List[Dict]): List of sample histograms.
        identifiers_to_index (Dict[str, int]): Mapping of IDs to indices.

    Returns:
        Tuple[np.ndarray, np.ndarray, List[str]]:
            - target (np.ndarray): The normalized target vector.
            - sample_vectors (np.ndarray): Array of sample vectors.
            - paths (List[str]): List of file paths for each sample.
    """
    target = np.zeros(len(identifiers_to_index))
    for k, v in reference["histo"].items():
        target[identifiers_to_index[k]] = v
    target = normalize(target)

    sample_vectors = []
    paths = []
    for sample in samples:
        vec = np.zeros(len(identifiers_to_index))
        for k, v in sample["histo"].items():
            vec[identifiers_to_index[k]] = v
        vec = normalize(vec)
        sample_vectors.append(vec)
        paths.append(sample["source_file"])

    return target, np.array(sample_vectors), paths


def solve_optimization(sample_vectors: np.ndarray, target: np.ndarray, max_selected: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solves the optimization problem to find the best weights for matching the target histogram.

    Args:
        sample_vectors (np.ndarray): Array of sample vectors.
        target (np.ndarray): The target vector to match.
        max_selected (int): Maximum number of samples to select.

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

    constraints = [
        w >= 0,
        w <= z,
        cp.sum(z) <= max_selected,
        cp.sum(w) == 1
    ]

    objective = cp.Minimize(cp.sum(cp.abs(sample_vectors.T @ w - target)))
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CBC)

    if problem.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
        raise RuntimeError("Optimization failed")

    return w.value, sample_vectors.T @ w.value


def write_output(output_path: str, reference_file: str, similarity: float, weights: np.ndarray, paths: List[str]) -> None:
    """
    Writes the optimization results to a JSON file, rounding weights to 4 decimals
    and adjusting to ensure the sum is exactly 1.0.

    Args:
        output_path (str): Path to the output JSON file.
        reference_file (str): Path to the reference file.
        similarity (float): Similarity score of the result.
        weights (np.ndarray): Weights for each selected sample file.
        paths (List[str]): File paths for each selected sample file.

    Raises:
        ValueError: If weights cannot be normalized to sum to 1.0.
    """

    selected_raw = [
        (paths[i], weights[i])
        for i in range(len(weights)) if weights[i] > 1e-6
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
            raise ValueError("Unable to normalize weights to sum to 1.0")

    selected = [
        {
            "sample_path": selected_raw[i][0],
            "weight": rounded_weights[i]
        }
        for i in range(len(rounded_weights))
    ]

    output_weight_data = {
        "reference_file": reference_file,
        "similarity": round(similarity, 2),
        "selected_samples": selected
    }

    utils.save_json(output_weight_data, output_path)


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Main pipeline to execute the entire process from loading data to saving results.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        FileNotFoundError: If the optimization fails or unexpected errors occur.
    """

    work_dir = os.path.abspath(args.work_dir)
    max_selected_samples = args.max_selected_samples
    min_similarity = args.min_similarity

    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")

    print(f"[INFO] WORK_DIR:             {work_dir}")
    print(f"[INFO] MAX_SELECTED_SAMPLES: {max_selected_samples}")
    print(f"[INFO] MIN_SIMILARITY:       {min_similarity}")

    input_path = os.path.join(args.work_dir, "stages", "histos.json")
    output_path = os.path.join(args.work_dir, "stages", "weight.json")

    reference, samples, all_identifiers, identifiers_to_index = load_histograms(input_path)
    target, sample_vectors, paths = prepare_vectors(reference, samples, identifiers_to_index)

    weights, result_vector = solve_optimization(sample_vectors, target, args.max_selected_samples)
    result_vector = normalize(result_vector)
    similarity = compute_similarity(result_vector, target)

    if similarity < args.min_similarity:
        print(f"[INFO] Similarity {similarity:.2f}% is below the minimum threshold. Selecting maximum samples.")
        weights, result_vector = solve_optimization(sample_vectors, target, len(sample_vectors))
        result_vector = normalize(result_vector)
        similarity = compute_similarity(result_vector, target)

    write_output(output_path, reference["source_file"], similarity, weights, paths)

    print(f"[INFO] Optimization complete. Similarity: {similarity:.2f}%")


def main() -> None:
    """
    Entry point of the script and top-level error handler.

    Parses command-line arguments and runs the processing pipeline.
    Handles and categorizes known exceptions, writes error messages to stderr,
    and exits with appropriate status codes:

    Exit Codes:
        1: PipelineError, any other unexpected error
        2: InvalidReferenceCountError
        4: StageResetError, ArtifactDiscoveryError, OutputWriteError
        5: FileNotFoundError
    """
    try:
        args = parse_arguments()
        run_pipeline(args)
    except (ValueError, utils.InvalidInputDataError) as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(2)
    except (utils.OutputResetError, utils.OutputWriteError, RuntimeError) as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(4)
    except FileNotFoundError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(5)
    except utils.PipelineError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"[ERROR] An unexpected error occurred: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
