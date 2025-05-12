import os
import unittest
import subprocess
import shutil
import unit_test_build_histo
import unit_test_find_files
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


class TestSolveMathScript(unittest.TestCase):
    """
    Unit tests for the solve_math.py script.

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
        self.output_file = os.path.join(self.valid_work_dir, "stages", "weight.json")

        self.test_find_files = unit_test_find_files.TestFindFilesScript()
        self.test_find_files.setUp()

        self.test_build_histos = unit_test_build_histo.TestBuildHistoScript()
        self.test_build_histos.setUp()

    def run_script_solve_math(self, work_dir: str) -> subprocess.CompletedProcess:
        """
        Runs the solve_math.py script as a subprocess using environment variables.

        Args:
            work_dir (str): Path to the work directory.

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = (
            f"python {self.tool_dir}/stage3/solve_math.py " f"--work-dir={work_dir}"
        )

        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result

    def test_success_solve_math_from_histo(self) -> None:
        """
        Tests a successful case where the histos files is processed and 'weight.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        self.test_build_histos.run_script_build_histo(self.valid_work_dir)

        result = self.run_script_solve_math(self.valid_work_dir)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            os.path.exists(self.output_file), "Output file 'weight.json' not created"
        )

    def test_success_solve_math_from_jfr(self) -> None:
        """
        Tests a successful case where the jfrs file is processed and 'weight.json' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.valid_lookup_mask = "*.jfr"
        self.valid_sample_dir = os.path.join(self.tool_dir, "jfr_07_04_ksj", "1-1-1")
        self.valid_reference_dir = os.path.join(self.valid_sample_dir, "compare_input")
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        self.test_build_histos.run_script_build_histo(self.valid_work_dir)

        result = self.run_script_solve_math(self.valid_work_dir)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            os.path.exists(self.output_file), "Output file 'weight.json' not created"
        )

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 5 and includes the expected error message.
        """
        missing_dir = os.path.join(self.tool_dir, "not_exist_dir_abc")
        result = self.run_script_solve_math(missing_dir)
        self.assertEqual(result.returncode, 5)
        self.assertIn("--work-dir=", result.stderr)

    def test_missing_histos_json(self) -> None:
        """
        Tests the case where the 'stages/histos.json' file is missing in the working directory.

        Verifies that the script exits with error code 4 and includes an error message
        about failing to load 'stages/histos.json'.
        """
        invalid_work_dir = os.path.join(self.tool_dir, "1")
        result = self.run_script_solve_math(invalid_work_dir)
        self.assertEqual(result.returncode, 5)
        self.assertIn("Failed to load input json file", result.stderr)

    def test_no_reference(self):
        """
        Tests the case where the 'stages/histos.json' file is missing the reference histogram.

        Verifies that the script raises a ValueError and includes an error message about the missing reference.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "histos.json")

        no_reference_data = [
            {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 2}},
            {"type": "sample", "source_file": "sample2", "histo": {"c": 3, "d": 4}},
        ]
        utils.save_json(no_reference_data, histos_path)

        result = self.run_script_solve_math(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("No reference histogram found.", result.stderr)

    def test_no_samples(self):
        """
        Tests the case where the 'stages/histos.json' file is missing the samples histogram.

        Verifies that the script raises a ValueError and includes an error message about the missing reference.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "histos.json")

        no_samples_data = [
            {
                "type": "reference",
                "source_file": "reference_file",
                "histo": {"a": 1, "b": 2},
            },
        ]
        utils.save_json(no_samples_data, histos_path)

        result = self.run_script_solve_math(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("No valid sample histograms found.", result.stderr)

    def test_empty_reference(self):
        """
        Tests the case where the reference histogram is empty in the 'stages/histos.json' file.

        Verifies that the script raises a ValueError and includes an error message about the empty reference histogram.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "histos.json")

        empty_reference_data = [
            {"type": "reference", "source_file": "reference_file", "histo": {}},
            {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 2}},
        ]
        utils.save_json(empty_reference_data, histos_path)

        result = self.run_script_solve_math(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Reference histogram is empty", result.stderr)

    def test_empty_samples(self):
        """
        Tests the case where the histograms of all samples are empty in the 'stages/histos.json' file.

        Verifies that the script raises a ValueError and includes an error message indicating that the histograms of all samples are empty.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "histos.json")

        empty_samples_data = [
            {
                "type": "reference",
                "source_file": "reference_file",
                "histo": {"a": 1, "b": 1},
            },
            {"type": "sample", "source_file": "sample1", "histo": {}},
            {"type": "sample", "source_file": "sample2", "histo": {}},
        ]
        utils.save_json(empty_samples_data, histos_path)

        result = self.run_script_solve_math(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("No valid sample histograms found.", result.stderr)

    def test_invalid_input_json(self):
        """
        Tests the case where the histograms of all entries in the 'stages/histos.json' file are incorrectly formatted.

        Verifies that the script raises a ValueError and includes an error message indicating that each histogram entry must contain exactly the expected keys.
        """
        stages_dir = os.path.join(self.valid_work_dir, "stages")
        os.makedirs(stages_dir, exist_ok=True)
        histos_path = os.path.join(stages_dir, "histos.json")

        invalid_input_data = [
            {"type": "reference", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample2", "histo": {"a": 1, "b": 1}},
        ]

        utils.save_json(invalid_input_data, histos_path)

        result = self.run_script_solve_math(self.valid_work_dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "Each histogram entry must contain exactly the keys ", result.stderr
        )

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
