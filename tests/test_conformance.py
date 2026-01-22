import contextlib
import io
from pathlib import Path
import unittest

from greyalien import cli


BASE_DIR = Path(__file__).resolve().parent / "conformance"
PASS_DIR = BASE_DIR / "pass"
FAIL_DIR = BASE_DIR / "fail"


def run_program(path: Path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = cli.run_path(str(path))
    output = buf.getvalue().replace("\r\n", "\n").rstrip()
    return exit_code, output


class ConformanceTests(unittest.TestCase):
    def test_pass_fixtures(self):
        greyalien_files = sorted(PASS_DIR.glob("*.grl"))
        self.assertTrue(greyalien_files, "No conformance pass fixtures found")

        for greyalien_path in greyalien_files:
            expected_path = greyalien_path.with_suffix(".out")
            self.assertTrue(
                expected_path.exists(), f"Missing expected output for {greyalien_path.name}"
            )
            exit_code, output = run_program(greyalien_path)
            expected = expected_path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
            self.assertEqual(exit_code, 0, f"Conformance pass failed: {greyalien_path.name}")
            self.assertEqual(output, expected, f"Output mismatch: {greyalien_path.name}")

    def test_fail_fixtures(self):
        greyalien_files = sorted(FAIL_DIR.glob("*.grl"))
        self.assertTrue(greyalien_files, "No conformance fail fixtures found")

        for greyalien_path in greyalien_files:
            expected_path = greyalien_path.with_suffix(".err")
            self.assertTrue(
                expected_path.exists(), f"Missing expected error for {greyalien_path.name}"
            )
            exit_code, output = run_program(greyalien_path)
            expected_lines = [
                line.strip()
                for line in expected_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(exit_code, 1, f"Conformance fail did not error: {greyalien_path.name}")
            for line in expected_lines:
                self.assertIn(line, output, f"Missing error text '{line}' in {greyalien_path.name}")


if __name__ == "__main__":
    unittest.main()
