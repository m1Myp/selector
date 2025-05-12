import os
import unittest
import subprocess
import shutil
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
import utils


class TestFindFilesScript(unittest.TestCase):
    """
    Unit tests for the find_files.py script.

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
        self.script = os.path.join(self.tool_dir, "stage1", "find_files.py")
        self.valid_sample_dir = os.path.join(self.tool_dir, "1")
        self.valid_reference_dir = os.path.join(self.valid_sample_dir, "compare_input")
        self.valid_work_dir = os.path.join(self.tool_dir, "work_dir")
        self.lookup_mask = "*.histo"
        self.output_file = os.path.join(self.valid_work_dir, "stages", "files.json")

    def run_script_find_files(
        self, sample_dir: str, reference_dir: str, work_dir: str, lookup_mask: str
    ) -> subprocess.CompletedProcess:
        """
        Runs the find_files.py script as a subprocess.

        Args:
            sample_dir (str): Path to the sample directory.
            reference_dir (str): Path to the reference directory.
            work_dir (str): Path to the work directory.
            lookup_mask (str): The lookup mask to match files.

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = (
            f"python {self.tool_dir}/stage1/find_files.py "
            f"--sample-dir={sample_dir} "
            f"--reference-dir={reference_dir} "
            f"--work-dir={work_dir} "
            f"--lookup-mask={lookup_mask}"
        )
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result

    def test_success_find_files_histo(self) -> None:
        """
        Tests a successful case with histo files in the correct input directories.

        Verifies that the script completes successfully (return code 0).
        """
        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            os.path.exists(self.output_file), "Output file 'files.json' not created"
        )

    def test_success_find_files_jfr(self) -> None:
        """
        Tests a successful case with jfr files in the correct input directories.

        Verifies that the script completes successfully (return code 0).
        """
        self.lookup_mask = "*.jfr"
        self.valid_sample_dir = os.path.join(self.tool_dir, "jfr_07_04_ksj", "1-1-1")
        self.valid_reference_dir = os.path.join(self.valid_sample_dir, "compare_input")

        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            os.path.exists(self.output_file), "Output file 'files.json' not created"
        )

    def test_success_find_files_txt(self) -> None:
        """
        Tests a successful case with some files in the correct input directories.

        Verifies that the script completes successfully (return code 0).
        """
        self.lookup_mask = "*.some"
        os.makedirs(self.valid_reference_dir, exist_ok=True)
        txt_file = os.path.join(self.valid_reference_dir, "file.some")
        with utils.open_with_default_encoding(txt_file, "w") as f:
            f.write("unsupported")

        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            os.path.exists(self.output_file), "Output file 'files.json' not created"
        )

        os.remove(txt_file)

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 5 and includes the expected error message.
        """
        missing_dir = os.path.join(self.tool_dir, "not_exist_dir_abc")
        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            missing_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 5)
        self.assertIn("--work-dir=", result.stderr)

    def test_invalid_reference_count(self) -> None:
        """
        Tests the case where more than one reference file is found.

        Verifies that the script exits with error code 3 and includes an error message
        about the expected number of reference files.
        """
        os.makedirs(self.valid_reference_dir, exist_ok=True)
        invalid_count_reference1 = os.path.join(
            self.valid_reference_dir, "invalid_reference1.histo"
        )
        invalid_count_reference2 = os.path.join(
            self.valid_reference_dir, "invalid_reference2.histo"
        )
        with utils.open_with_default_encoding(invalid_count_reference1, "w") as f:
            f.write("hello")
        with utils.open_with_default_encoding(invalid_count_reference2, "w") as f:
            f.write("world")

        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Expected exactly one reference file", result.stderr)

        os.remove(invalid_count_reference1)
        os.remove(invalid_count_reference2)

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
