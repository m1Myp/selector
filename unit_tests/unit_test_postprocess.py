import unittest
import sys
import shutil
import subprocess
import unit_test_find_files
import unit_test_build_histo
import unit_test_solve_math
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
import utils


class TestPostprocessScript(unittest.TestCase):
    """
    Unit tests for the postprocess.py script.

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
        self.script = self.tool_dir / "stage4" / "postprocess.py"
        self.valid_sample_dir = self.tool_dir / "1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"
        self.valid_work_dir = self.tool_dir / "work_dir"
        self.valid_lookup_mask = "*.histo"
        self.output_file = self.valid_work_dir / "weight"
        self.sample_artifact_depth = 2
        self.reference_artifact_depth = 1

        self.test_find_files = unit_test_find_files.TestFindFilesScript()
        self.test_find_files.setUp()

        self.test_build_histos = unit_test_build_histo.TestBuildHistoScript()
        self.test_build_histos.setUp()

        self.test_solve_math = unit_test_solve_math.TestSolveMathScript()
        self.test_solve_math.setUp()

    def run_script_postprocess(
        self, work_dir: Path, sample_artifact_depth: int, reference_artifact_depth: int
    ) -> subprocess.CompletedProcess:
        """
        Runs the postprocess.py script as a subprocess using environment variables.

        Args:
            work_dir (Path): Path to the work directory.
            sample_artifact_depth (int): The number of directory levels to consider
            for the sample artifacts during postprocessing.
            reference_artifact_depth (int): The number of directory levels to consider
            for the reference artifacts during postprocessing.


        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = (
            f"python {self.script} "
            f"--work-dir={work_dir} "
            f"--sample-artifact-depth={sample_artifact_depth} "
            f"--reference-artifact-depth={reference_artifact_depth}"
        )

        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result

    def test_success_scripts_sequence_from_histo(self) -> None:
        """
        Tests a successful case where all scripts work correct and 'weight' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        self.test_build_histos.run_script_build_histo(self.valid_work_dir)

        self.test_solve_math.run_script_solve_math(self.valid_work_dir)

        result = self.run_script_postprocess(
            self.valid_work_dir,
            self.sample_artifact_depth,
            self.reference_artifact_depth,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.output_file.exists(), "Output file 'weight' not created")

    def test_success_scripts_sequence_from_jfr(self) -> None:
        """
        Tests a successful case where the jfrs file is processed and 'weight' is generated.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.valid_lookup_mask = "*.jfr"
        self.valid_sample_dir = self.tool_dir / "jfr_07_04_ksj" / "1-1-1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"
        self.sample_artifact_depth = 1
        self.reference_artifact_depth = 1
        self.test_find_files.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.valid_lookup_mask,
        )

        self.test_build_histos.run_script_build_histo(self.valid_work_dir)

        self.test_solve_math.run_script_solve_math(self.valid_work_dir)

        result = self.run_script_postprocess(
            self.valid_work_dir,
            self.sample_artifact_depth,
            self.reference_artifact_depth,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.output_file.exists(), "Output file 'weight' not created")

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        the work directory does not exist.
        """
        missing_dir = self.tool_dir / "not_exist_dir_abc"
        result = self.run_script_postprocess(
            missing_dir, self.sample_artifact_depth, self.reference_artifact_depth
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--work-dir=", result.stderr)

    def test_missing_weight_json(self) -> None:
        """
        Tests the case where the 'stages/histos.json' file is missing in the working directory.

        Verifies that the script exits with error code 1 and includes an error message
        about failing to load 'stages/weight.json'.
        """
        invalid_work_dir = self.tool_dir / "1"
        result = self.run_script_postprocess(
            invalid_work_dir, self.sample_artifact_depth, self.reference_artifact_depth
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed to load input json file", result.stderr)

    def test_invalid_input_json(self):
        """
        Tests the case where the 'stages/weight.json' file is incorrectly formatted.

        Verifies that the script exits with error code 1 and includes an error message about validation error.
        """
        stages_dir = self.valid_work_dir / "stages"
        stages_dir.mkdir(parents=True, exist_ok=True)
        histos_path = stages_dir / "weight.json"

        invalid_input_data = [
            {"type": "reference", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample1", "histo": {"a": 1, "b": 1}},
            {"type": "sample", "source_file": "sample2", "histo": {"a": 1, "b": 1}},
        ]

        utils.save_json(invalid_input_data, histos_path)

        result = self.run_script_postprocess(
            self.valid_work_dir,
            self.sample_artifact_depth,
            self.reference_artifact_depth,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Validation error:", result.stderr)

    def tearDown(self) -> None:
        """
        Cleans up the output file if it exists after each test.
        """
        stages_path = self.valid_work_dir / "stages"
        if stages_path.exists() and stages_path.is_dir():
            shutil.rmtree(stages_path)
        if self.valid_work_dir.exists() and self.valid_work_dir.is_dir():
            shutil.rmtree(self.valid_work_dir)
        self.valid_work_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    unittest.main()
