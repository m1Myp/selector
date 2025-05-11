import os
import shutil
import json
from contextlib import contextmanager
from typing import Generator


class PipelineError(Exception):
    """
    Base exception for all pipeline-related errors.
    """
    pass


class OutputResetError(PipelineError):
    """
    Raised when the stage directory cannot be reset.
    """
    pass


class OutputWriteError(PipelineError):
    """
    Raised when the script fails to write output files.
    """
    pass


class InvalidInputDataError(Exception):
    """Raised when a JSON entry does not contain exactly the required keys."""

    pass


def input_json_validation(json_entry, required_keys):
    if set(json_entry.keys()) != required_keys:
        raise InvalidInputDataError(
            f"Each histogram entry must contain exactly the keys {required_keys}. "
            f"Found {set(json_entry.keys())} in entry: {json_entry}"
        )


def save_json(output_data: list, output_file: str) -> None:
    """
    Saves the provided data to a JSON file.

    The JSON file will be created using UTF-8 encoding, with indentation
    for readability and Unicode characters preserved.

    Args:
        output_data (list): A list of dictionaries or serializable objects to write.
        output_file (str): Path to the file where the JSON will be saved.

    Raises:
        OutputWriteError: If writing to the file fails.
    """
    try:
        reset_output(output_file)
        with open_with_default_encoding(output_file, "w") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[+] JSON written to: {output_file}")
    except Exception as e:
        raise OutputWriteError(f"Failed to write output JSON: {e}")


def load_files_json(files_json_path: str) -> list:
    """
    Loads and parses a list of entries from a JSON file.

    Args:
        files_json_path (str): Path to the JSON file to load.

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


def reset_output(output_path: str) -> None:
    """
    Deletes an existing output directory or file, or creates the directory if not a file.

    If the path exists, it will be removed. If the path does not exist and is a directory,
    it will be created (unless it's expected to be a JSON file).

    Args:
        output_path (str): Path to the file or directory to reset.

    Raises:
        OutputResetError: If the file or directory could not be deleted or created.
    """
    if os.path.exists(output_path):
        try:
            if os.path.isdir(output_path):
                shutil.rmtree(output_path)
            else:
                os.remove(output_path)
        except Exception as e:
            raise OutputResetError(f"Failed to delete '{output_path}': {e}")
    if not (output_path.endswith('.json') or output_path.endswith('weight')):
        os.makedirs(output_path)


@contextmanager
def open_with_default_encoding(file_path: str, mode: str) -> Generator:
    """
    Context manager that opens a file using UTF-8 encoding.

    This is a thin wrapper around the built-in `open()` function that
    ensures consistent UTF-8 encoding across platforms.

    Args:
        file_path (str): Path to the file.
        mode (str): File open mode (e.g., 'r', 'w').

    Yields:
        Generator[TextIOWrapper, None, None]: File object with UTF-8 encoding.
    """
    with open(file_path, mode, encoding="utf-8") as f:
        yield f
