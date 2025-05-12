import os
import sys
import json
import argparse
import subprocess
from typing import Optional, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


class UnsupportedFileFormatError(utils.PipelineError):
    """
    Raised when an unsupported profile file format is encountered.
    """

    pass


class HistoParseError(utils.PipelineError):
    """
    Raised when parsing a .histo file fails.
    """

    pass


class JavaToolError(utils.PipelineError):
    """
    Raised when a Java tool fails to parse a JFR file.
    """

    pass


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including work directory, block compression flag
                            and hotness compression percentage.
    """
    parser = argparse.ArgumentParser(
        description="Extract histograms from profile files."
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        required=True,
        help="Working directory containing stages/files.json;"
        "also used as the output directory for stages/histos.json",
    )
    parser.add_argument(
        "--block-compression",
        type=str,
        default="true",
        help="Enable block compression (true/false) (default: true)",
    )
    parser.add_argument(
        "--hotness-compression",
        type=int,
        default=97,
        help="Percentage for hotness compression (0-100) (default: 97)",
    )
    return parser.parse_args()


def build_histo_from_profile(json_entry: dict) -> dict:
    """
    Builds a histogram from a profile entry, depending on the file extension.

    Args:
        json_entry (dict): Profile entry containing a "source_file" field.

    Returns:
        dict: Histogram mapping function names to counts.

    Raises:
        UnsupportedFileFormatError: If the source file format is unsupported.
    """
    file_path = str(json_entry["source_file"])
    file_extension = os.path.splitext(file_path)[1][1:]
    if file_extension == "histo":
        return build_from_raw_histo(file_path)
    elif file_extension == "jfr":
        return build_from_jfr(file_path)
    else:
        raise UnsupportedFileFormatError("Unsupported file format")


def parse_raw_histo_line(
    file_path: str, line: str, line_num: int
) -> Optional[Tuple[str, int]]:
    """
    Parses a single line from a .histo file.

    Args:
        file_path (str): Path to the .histo file.
        line (str): Line content to parse.
        line_num (int): Current line number (used for error reporting).

    Returns:
        Optional[Tuple[str, int]]: A tuple containing function name and count,
            or None if the line is a comment or empty.

    Raises:
        HistoParseError: If the line is invalid or count conversion fails.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split()
    if len(parts) >= 2:
        try:
            return parts[0], int(parts[1])
        except ValueError:
            raise HistoParseError(
                f"Invalid number format in file '{file_path}' at line {line_num}: {line}"
            )
    else:
        raise HistoParseError(
            f"Invalid line in file '{file_path}' at line {line_num}: {line}"
        )


def build_from_raw_histo(file_path: str) -> dict:
    """
    Builds a histogram dictionary from a raw .histo file.

    Args:
        file_path (str): Path to the .histo file.

    Returns:
        dict: Histogram of function names to counts.

    Raises:
        HistoParseError: If reading or parsing the file fails.
    """
    try:
        with utils.open_with_default_encoding(file_path, "r") as f:
            data = []
            for line_num, line in enumerate(f, start=1):
                result = parse_raw_histo_line(file_path, line, line_num)
                if result:
                    identifier, count = result
                    data.append((identifier, count))
            return {func: val for func, val in data}
    except Exception as e:
        raise HistoParseError(f"Error reading the file {file_path}: {e}")


def build_from_jfr(file_path: str) -> dict:
    """
    Extracts a histogram from a .jfr file using an external Java tool.

    Args:
        file_path (str): Path to the .jfr file.

    Returns:
        dict: Histogram parsed from the JFR output.

    Raises:
        JavaToolError: If the Java tool fails or returns invalid output.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    java_name = os.path.join(current_dir, "JFRParser.java")

    cmd = ["java", java_name, file_path]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise JavaToolError(f"Failed to parse JFR file {file_path}: {e.stderr}")


def build_histos(profiles: list) -> list:
    """
    Builds histograms for each profile entry.

    Args:
        profiles (list): List of profile dictionaries from files.json.

    Returns:
        list: List of dictionaries with type, source_file, and histogram data.
    """
    result = []
    required_keys = {"type", "source_file"}
    for json_entry in profiles:
        utils.input_json_validation(json_entry, required_keys)
        histo = build_histo_from_profile(json_entry)
        result.append(
            {
                "type": json_entry["type"],
                "source_file": json_entry["source_file"],
                "histo": histo,
            }
        )
    return result


def hotness_compress(uncompressed_result: list, hotness_compression: int) -> list:
    """
    Applies hotness-based compression to histograms.

    Keeps only the most frequently used functions until the cumulative count
    reaches the specified hotness percentage.

    Args:
        uncompressed_result (list): List of histogram entries before compression.
        hotness_compression (int): Threshold percentage (0–100).

    Returns:
        list: Compressed histogram entries.

    Raises:
        ValueError: If hotness_compression is outside the range [0, 100].
    """
    if hotness_compression < 0 or hotness_compression > 100:
        raise ValueError("HOTNESS_COMPRESSION must be between 0 and 100")

    if hotness_compression == 100:
        return uncompressed_result

    result = []
    threshold = hotness_compression / 100

    for entry in uncompressed_result:
        histo = entry["histo"]
        sorted_histo = dict(sorted(histo.items(), key=lambda item: (-item[1], item[0])))
        total_sum = sum(sorted_histo.values())
        current_hotness = 0
        compressed_histo = {}

        for method, count in sorted_histo.items():
            if current_hotness + count <= threshold * total_sum:
                compressed_histo[method] = count
                current_hotness += count
            else:
                break

        entry["histo"] = compressed_histo
        result.append(entry)

    return result


def block_compress(uncompressed_result: list) -> list:
    """
    Compresses histogram entries by merging functions with identical profiles.

    Args:
        uncompressed_result (list): List of histogram entries before compression.

    Returns:
        list: New list of histogram entries with compressed histograms.
    """
    if not uncompressed_result:
        return []

    num_entries = len(uncompressed_result)
    merged_dict = {}
    for idx, entry in enumerate(uncompressed_result):
        histo = entry["histo"]
        for key, value in histo.items():
            key_str = str(key)
            if key_str not in merged_dict:
                merged_dict[key_str] = [0] * num_entries
            merged_dict[key_str][idx] = value

    value_to_keys = {}
    for key, values in merged_dict.items():
        value_tuple = tuple(values)
        value_to_keys.setdefault(value_tuple, []).append(key)

    merged_blocks = {}
    for value_tuple, keys in value_to_keys.items():
        main_key = keys[0]
        if len(keys) == 1:
            merged_blocks[main_key] = list(value_tuple)
        else:
            summed = [sum(merged_dict[k][i] for k in keys) for i in range(num_entries)]
            merged_blocks[main_key] = summed

    compressed_result = []
    for i in range(num_entries):
        histo = {}
        for key, values in merged_blocks.items():
            if values[i] > 0:
                histo[key] = values[i]
        new_entry = dict(uncompressed_result[i])
        new_entry["histo"] = histo
        compressed_result.append(new_entry)

    return compressed_result


def run_pipeline(args: argparse.Namespace) -> None:
    """
    Runs the full pipeline to generate and compress histograms.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        FileNotFoundError: If the working directory does not exist.
    """
    work_dir = os.path.abspath(args.work_dir)
    hotness_compression = args.hotness_compression
    block_compression = args.block_compression.lower() == "true"

    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")

    stages_dir = os.path.join(work_dir, "stages")
    input_path = os.path.join(stages_dir, "files.json")
    output_path = os.path.join(stages_dir, "histos.json")

    print(f"[INFO] WORK_DIR:            {work_dir}")
    print(f"[INFO] HOTNESS_COMPRESSION: {hotness_compression}")
    print(f"[INFO] BLOCK_COMPRESSION:   {block_compression}")

    profiles = utils.load_files_json(input_path)
    result = build_histos(profiles)
    compressed_result = hotness_compress(result, hotness_compression)
    if block_compression:
        compressed_result = block_compress(compressed_result)
    utils.save_json(compressed_result, output_path)


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
    except (UnsupportedFileFormatError, utils.InvalidInputDataError) as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(2)
    except (
        HistoParseError,
        JavaToolError,
        utils.OutputResetError,
        utils.OutputWriteError,
    ) as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(4)
    except FileNotFoundError as e:
        sys.stderr.write(f"[ERROR] File not found: {e}\n")
        sys.exit(5)
    except utils.PipelineError as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"[ERROR] An unexpected error occurred: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
