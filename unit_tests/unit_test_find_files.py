import unittest
import sys
import shutil
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))
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
        base = Path("C:/Users/timm0/PycharmProjects/selector_OS").resolve()
        self.tool_dir = base
        self.script = self.tool_dir / "stage1" / "find_files.py"
        self.valid_sample_dir = self.tool_dir / "1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"
        self.valid_work_dir = self.tool_dir / "work_dir"
        self.lookup_mask = "*.histo"
        self.output_file = self.valid_work_dir / "stages" / "files.json"

    def run_script_find_files(
        self, sample_dir: Path, reference_dir: Path, work_dir: Path, lookup_mask: str
    ) -> subprocess.CompletedProcess:
        """
        Runs the find_files.py script as a subprocess.

        Args:
            sample_dir (Path): Path to the sample directory.
            reference_dir (Path): Path to the reference directory.
            work_dir (Path): Path to the work directory.
            lookup_mask (str): The lookup mask to match files.

        Returns:
            subprocess.CompletedProcess: The result of the subprocess run.
        """
        command = (
            f"python {self.script} "
            f"--sample-dir={sample_dir} "
            f"--reference-dir={reference_dir} "
            f"--work-dir={work_dir} "
            f"--lookup-mask={lookup_mask}"
        )
        return subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_success_find_files_histo(self) -> None:
        """
        Tests a successful case with histo files in the correct input directories.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            self.output_file.exists(), "Output file 'files.json' not created"
        )

    def test_success_find_files_jfr(self) -> None:
        """
        Tests a successful case with jfr files in the correct input directories.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.lookup_mask = "*.jfr"
        self.valid_sample_dir = self.tool_dir / "jfr_07_04_ksj" / "1-1-1"
        self.valid_reference_dir = self.valid_sample_dir / "compare_input"

        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            self.output_file.exists(), "Output file 'files.json' not created"
        )

    def test_success_find_files_txt(self) -> None:
        """
        Tests a successful case with some files in the correct input directories.

        Verifies that the script completes successfully (return code 0) and the output file exists.
        """
        self.lookup_mask = "*.some"
        self.valid_reference_dir.mkdir(parents=True, exist_ok=True)
        txt_file = self.valid_reference_dir / "file.some"
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
            self.output_file.exists(), "Output file 'files.json' not created"
        )

        txt_file.unlink()

    def test_missing_work_dir(self) -> None:
        """
        Tests the case where the --work-dir argument points to a non-existent directory.

        Verifies that the script exits with error code 1 and includes an error message indicating that
        the work directory does not exist.
        """
        missing_dir = self.tool_dir / "not_exist_dir_abc"
        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            missing_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--work-dir=", result.stderr)

    def test_invalid_reference_count(self) -> None:
        """
        Tests the case where more than one reference file is found.

        Verifies that the script exits with error code 1 and includes an error message
        about the expected number of reference files.
        """
        self.valid_reference_dir.mkdir(parents=True, exist_ok=True)
        ref1 = self.valid_reference_dir / "invalid_reference1.histo"
        ref2 = self.valid_reference_dir / "invalid_reference2.histo"
        ref1.write_text("hello", encoding="utf-8")
        ref2.write_text("world", encoding="utf-8")

        result = self.run_script_find_files(
            self.valid_sample_dir,
            self.valid_reference_dir,
            self.valid_work_dir,
            self.lookup_mask,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Expected exactly one reference file", result.stderr)

        ref1.unlink()
        ref2.unlink()

    def tearDown(self) -> None:
        """
        Cleans up the output file if it exists after each test.
        """
        stages_path = self.valid_work_dir / "stages"
        if stages_path.exists() and stages_path.is_dir():
            shutil.rmtree(stages_path)


if __name__ == "__main__":
    unittest.main()
