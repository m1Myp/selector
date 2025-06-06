import unittest
import sys
import shutil
import subprocess
import unit_test_find_files
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
import utils


class TestBuildHistoScript(unittest.TestCase):
    """
    Unit tests for the build_histo.py script.

    These tests verify correct behavior for success and failure cases,
    including missing directories, invalid input, and internal script errors.
    """

    def setUp(self) -> None:
        """
        Sets up the necessary paths for testing.

        Initializes the paths for the tool directory, script, valid directories for run,
        reference, and work, and the lookup mask for file selection.
        """
        base = Path("C:/Users/timm0/PycharmProjects/selector_OS").resolve()
        self.tool_dir = base
        self.script = self.tool_dir / "stage2" / "build_histo.py"
        self.valid_sample_dir = self.tool_dir / "1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"
        self.valid_work_dir = self.tool_dir / "work_dir"
        self.valid_lookup_mask = "*.histo"
        self.output_file = self.valid_work_dir / "stages" / "histos.json"

        self.test_find_files = unit_test_find_files.TestFindFilesScript()
        self.test_find_files.setUp()

    def run_script_build_histo(self, work_dir: Path) -> subprocess.CompletedProcess:
        """
        Runs the build_histo.py script as a subprocess using environment variables.

        Args:
            work_dir (Path): Path to the work directory.

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = f"python {self.script} --work-dir={work_dir}"

        return subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_success_build_histos_from_histo(self) -> None:
        """
        Tests a successful case where the histos file is processed and 'histos.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            self.output_file.exists(), "Output file 'histos.json' not created"
        )

    def test_success_build_histos_from_jfr(self) -> None:
        """
        Tests a successful case where the jfrs file is processed and 'histos.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.valid_lookup_mask = "*.jfr"
        self.valid_sample_dir = self.tool_dir / "jfr_07_04_ksj" / "1-1-1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            self.output_file.exists(), "Output file 'histos.json' not created"
        )

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        the work directory does not exist.
        """
        missing_dir = self.tool_dir / "not_exist_dir_abc"
        result = self.run_script_build_histo(missing_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("--work-dir=", result.stderr)

    def test_unsupported_file_format(self) -> None:
        """
        Tests the case where the reference file has an unsupported format.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        the file format is unsupported.
        """
        unsupported_lookup_mask = "*.unsupported"
        self.valid_reference_dir.mkdir(parents=True, exist_ok=True)
        file_with_unsupported_format = (
            self.valid_reference_dir / "file_with_unsupported_format.unsupported"
        )
        with utils.open_with_default_encoding(file_with_unsupported_format, "w") as f:
            f.write("unsupported")

        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            unsupported_lookup_mask,
        )

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported file format", result.stderr)

        file_with_unsupported_format.unlink()

    def test_missing_files_json(self) -> None:
        """
        Tests the case where the 'stages/files.json' file is missing in the working directory.

        Verifies that the script exits with error code 1 and includes an error message
        about failing to load 'stages/files.json'.
        """
        invalid_work_dir = self.tool_dir / "1"
        result = self.run_script_build_histo(invalid_work_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to load input json file", result.stderr)

    def test_invalid_number_format_in_histo_file(self) -> None:
        """
        Tests the case where a .histo file contains a line with an invalid number format.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        the number format in the file is invalid.
        """
        another_reference_dir = self.valid_sample_dir / "another_reference_dir"
        another_reference_dir.mkdir(parents=True, exist_ok=True)
        invalid_file = another_reference_dir / "invalid_number_format.histo"
        with utils.open_with_default_encoding(invalid_file, "w") as f:
            f.write("hello 0.00001")
        stages_dir = self.valid_work_dir / "stages"
        stages_dir.mkdir(parents=True, exist_ok=True)
        histos_path = stages_dir / "files.json"

        input_data = [
            {"type": "reference", "source_file": f"{invalid_file}"},
        ]

        utils.save_json(input_data, histos_path)

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid number format in file", result.stderr)

        invalid_file.unlink()
        shutil.rmtree(another_reference_dir)

    def test_invalid_line_in_histo_file(self) -> None:
        """
        Tests the case where a .histo file contains an invalid line.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        a line in the file is invalid.
        """
        another_reference_dir = self.valid_sample_dir / "another_reference_dir"
        another_reference_dir.mkdir(parents=True, exist_ok=True)
        invalid_file = another_reference_dir / "invalid_number_format.histo"
        with utils.open_with_default_encoding(invalid_file, "w") as f:
            f.write("hello")
        stages_dir = self.valid_work_dir / "stages"
        stages_dir.mkdir(parents=True, exist_ok=True)
        histos_path = stages_dir / "files.json"

        input_data = [
            {"type": "reference", "source_file": f"{invalid_file}"},
        ]

        utils.save_json(input_data, histos_path)

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid line in file", result.stderr)

        invalid_file.unlink()
        shutil.rmtree(another_reference_dir)

    def test_invalid_input_json(self):
        """
        Tests the case where the 'stages/files.json' file is incorrectly formatted.

        Verifies that the script exits with error code 1 and includes an error message about validation error.
        """
        stages_dir = self.valid_work_dir / "stages"
        stages_dir.mkdir(parents=True, exist_ok=True)
        histos_path = stages_dir / "files.json"

        invalid_input_data = [
            {"type": "reference", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample2", "histo": {"a": 1, "b": 1}},
        ]

        utils.save_json(invalid_input_data, histos_path)

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Validation error:", result.stderr)

    def tearDown(self) -> None:
        """
        Cleans up the output file if it exists after each test.
        """
        stages_path = self.valid_work_dir / "stages"
        if stages_path.exists() and stages_path.is_dir():
            shutil.rmtree(stages_path)


if __name__ == "__main__":
    unittest.main()
