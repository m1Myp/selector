import sys
import json
import shutil
from contextlib import contextmanager
from typing import Generator, Callable, Dict, TypedDict, Any
from jsonschema import validate, ValidationError
from pathlib import Path

Histogram = Dict[str, int]


class FilesJsonEntry(TypedDict):
    type: str
    source_file: Path


class HistosJsonEntry(TypedDict):
    type: str
    source_file: Path
    histo: Histogram


class PipelineError(Exception):
    """
    Base exception for all pipeline-related errors.
    """

    pass


def validate_json(data: Any, schema: dict) -> bool:
    """
    Validates whether `data` conforms to the provided JSON `schema`.

    Args:
        data (Any): The data to validate (typically a dict or list).
        schema (dict): The JSON schema to validate against.

    Returns:
        bool: True if the data is valid, False otherwise (and prints the error).
    """
    try:
        validate(instance=data, schema=schema)
        return True
    except Exception as e:
        raise ValidationError(f"Validation error: {e}")


def save_json(output_data: list, output_file: Path) -> None:
    """
    Saves the provided data to a JSON file.

    The JSON file will be created using UTF-8 encoding, with indentation
    for readability and Unicode characters preserved.

    Args:
        output_data (list): A list of dictionaries or serializable objects to write.
        output_file (Path): Path to the file where the JSON will be saved.

    Raises:
        PipelineError: If writing to the file fails.
    """
    try:
        reset_output(output_file)
        with open_with_default_encoding(output_file, "w") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[+] JSON written to: {output_file}")
    except Exception as e:
        raise PipelineError(f"Failed to write output JSON: {e}")


def load_files_json(files_json_path: Path) -> list:
    """
    Loads and parses a list of entries from a JSON file.

    Args:
        files_json_path (Path): Path to the JSON file to load.

    Returns:
        list: Parsed list of entries from the JSON file.

    Raises:
        FileNotFoundError: If reading or parsing the file fails.
    """
    try:
        with open_with_default_encoding(files_json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Failed to load input json file: {e}")


def reset_output(output_path: Path) -> None:
    """
    Deletes an existing output directory or file, or creates the directory if not a file.

    If the path exists, it will be removed. If the path does not exist and is a directory,
    it will be created (unless it's expected to be a JSON file).

    Args:
        output_path (Path): Path to the file or directory to reset.

    Raises:
        PipelineError: If the file or directory could not be deleted or created.
    """
    if output_path.exists():
        try:
            if output_path.is_dir():
                shutil.rmtree(output_path)
            else:
                output_path.unlink()
        except Exception as e:
            raise PipelineError(f"Failed to delete '{output_path}': {e}")

    if not (
        output_path.suffix == ".json"
        or (output_path.name == "weight" and output_path.suffix == "")
    ):
        output_path.mkdir(parents=True, exist_ok=True)


@contextmanager
def open_with_default_encoding(file_path: Path, mode: str) -> Generator:
    """
    Context manager that opens a file using UTF-8 encoding.

    This is a thin wrapper around the built-in `open()` function that
    ensures consistent UTF-8 encoding across platforms.

    Args:
        file_path (Path): Path to the file.
        mode (str): File open mode (e.g., 'r', 'w').

    Yields:
        Generator[TextIOWrapper, None, None]: File object with UTF-8 encoding.
    """
    with open(file_path, mode, encoding="utf-8") as f:
        yield f


def parse_args_and_run(
    parse_args: Callable[[], any], run_pipeline: Callable[[any], None]
) -> None:
    """
    Entry point of the script and top-level error handler.

    This function parses command-line arguments using the provided parser function,
    runs the main pipeline logic, and handles exceptions consistently.
    If the --debug flag is set, a full traceback is printed on error.

    Args:
        parse_args: A function with no arguments that returns an argparse.Namespace.
        run_pipeline: A function that takes the parsed arguments and executes the main logic.
    """
    args = parse_args()
    try:
        run_pipeline(args)
    except Exception as e:
        sys.stderr.write(f"[ERROR]: {e}\n")
        if args.debug:
            traceback.print_exc()
        sys.exit(1)


def validate_work_dir_exists(work_dir: Path) -> None:
    """
    Validates that the specified working directory exists.

    Args:
        work_dir (Path): The path to the working directory.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    if not work_dir.exists():
        raise FileNotFoundError(f"--work-dir={work_dir} does not exist.")
