import os
import unittest
import subprocess
import shutil
import unit_test_find_files
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
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
        base = os.path.abspath(
            os.path.join(
                "C:", os.sep, "Users", "timm0", "PycharmProjects", "selector_OS"
            )
        )
        self.tool_dir = base
        self.script = os.path.join(self.tool_dir, "stage2", "build_histo.py")
        self.valid_sample_dir = os.path.join(self.tool_dir, "1")
        self.valid_reference_dir = os.path.join(self.valid_sample_dir, "compare_input")
        self.valid_work_dir = os.path.join(self.tool_dir, "work_dir")
        self.valid_lookup_mask = "*.histo"
        self.output_file = os.path.join(self.valid_work_dir, "stages", "histos.json")

        self.test_find_files = unit_test_find_files.TestFindFilesScript()
        self.test_find_files.setUp()

    def run_script_build_histo(
            self, work_dir: str
    ) -> subprocess.CompletedProcess:
        """
        Runs the build_histo.py script as a subprocess using environment variables.

        Args:
            work_dir (str): Path to the work directory.

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = f"python {self.tool_dir}/stage2/build_histo.py " \
                  f"--work-dir={work_dir}"

        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result

    def test_success_build_histos_from_histo(self) -> None:
        """
        Tests a successful case where the histos file is processed and 'histos.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask
        )

        result = self.run_script_build_histo(
            self.valid_work_dir
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(os.path.exists(self.output_file), "Output file 'histos.json' not created")

    def test_success_build_histos_from_jfr(self) -> None:
        """
        Tests a successful case where the jfrs file is processed and 'histos.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.valid_lookup_mask = "*.jfr"
        self.valid_sample_dir = os.path.join(self.tool_dir, "jfr_07_04_ksj", "1-1-1")
        self.valid_reference_dir = os.path.join(self.valid_sample_dir, "compare_input")
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask
        )

        result = self.run_script_build_histo(
            self.valid_work_dir
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(os.path.exists(self.output_file), "Output file 'histos.json' not created")

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 5 and includes the expected error message.
        """
        missing_dir = os.path.join(self.tool_dir, "not_exist_dir_abc")
        result = self.run_script_build_histo(
            missing_dir
        )
        self.assertEqual(result.returncode, 5)
        self.assertIn("--work-dir=", result.stderr)

    def test_unsupported_file_format(self) -> None:
        """
        Tests the case where the reference file has an unsupported format.

        Verifies that the script exits with error code 2 and outputs an error message
        indicating the file format is unsupported.
        """
        unsupported_lookup_mask = "*.unsupported"
        os.makedirs(self.valid_reference_dir, exist_ok=True)
        file_with_unsupported_format = os.path.join(self.valid_reference_dir, "file_with_unsupported_format.unsupported")
        with utils.open_with_default_encoding(file_with_unsupported_format, "w") as f:
            f.write("unsupported")

        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            unsupported_lookup_mask
        )

        result = self.run_script_build_histo(
            self.valid_work_dir
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unsupported file format", result.stderr)

        os.remove(file_with_unsupported_format)

    def test_missing_files_json(self) -> None:
        """
        Tests the case where the 'stages/files.json' file is missing in the working directory.

        Verifies that the script exits with error code 4 and includes an error message
        about failing to load 'stages/files.json'.
        """
        invalid_work_dir = os.path.join(self.tool_dir, "1")
        result = self.run_script_build_histo(
            invalid_work_dir
        )
        self.assertEqual(result.returncode, 5)
        self.assertIn("Failed to load input json file", result.stderr)

    def test_invalid_number_format_in_histo_file(self) -> None:
        """
        Tests the case where a .histo file contains a line with an invalid number format.

        Verifies that the build_histo.py script exits with error code 4 and includes an error
        message indicating that the number format in the file is invalid.
        """
        another_reference_dir = os.path.join(self.valid_sample_dir, "another_reference_dir")
        os.makedirs(another_reference_dir, exist_ok=True)
        invalid_number_format_histo = os.path.join(another_reference_dir, "invalid_number_format.histo")
        with utils.open_with_default_encoding(invalid_number_format_histo, "w") as f:
            f.write("hello 0.00001")
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            another_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask
        )

        result = self.run_script_build_histo(
            self.valid_work_dir
        )
        self.assertEqual(result.returncode, 4)
        self.assertIn("Invalid number format in file", result.stderr)

        os.remove(invalid_number_format_histo)
        shutil.rmtree(another_reference_dir)

    def test_invalid_line_in_histo_file(self) -> None:
        """
        Tests the case where a .histo file contains a completely malformed line.

        Verifies that the build_histo.py script exits with error code 4 and includes an error
        message indicating that a line in the file is invalid.
        """
        another_reference_dir = os.path.join(self.valid_sample_dir, "another_reference_dir")
        os.makedirs(another_reference_dir, exist_ok=True)
        invalid_line_histo = os.path.join(another_reference_dir, "invalid_number_format.histo")
        with utils.open_with_default_encoding(invalid_line_histo, "w") as f:
            f.write("hello")
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            another_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask
        )

        result = self.run_script_build_histo(
            self.valid_work_dir
        )
        self.assertEqual(result.returncode, 4)
        self.assertIn("Invalid line in file", result.stderr)

        os.remove(invalid_line_histo)
        shutil.rmtree(another_reference_dir)

    def test_invalid_input_json(self):
        """
        Tests the case where the histograms of all entries in the 'stages/files.json' file are incorrectly formatted.

        Verifies that the script raises a ValueError and includes an error message indicating that each histogram entry must contain exactly the expected keys.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "files.json")

        invalid_input_data = [{"type": "reference", "histo": {"a": 1, "b": 1}},
                              {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 1}},
                              {"type": "sample", "source_file": "sample2", "histo": {"a": 1, "b": 1}}]

        utils.save_json(invalid_input_data, histos_path)

        result = self.run_script_build_histo(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Each histogram entry must contain exactly the keys ", result.stderr)

    def tearDown(self) -> None:
        """
        Cleans up the output file if it exists after each test.
        """
        stages_path = os.path.join(self.valid_work_dir, "stages")
        if os.path.exists(stages_path):
            if os.path.isdir(stages_path):
                shutil.rmtree(stages_path)


if __name__ == "__main__":
    unittest.main()
