import contextlib
import io
from pathlib import Path
import unittest

from roc import cli


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXPECTED_DIR = EXAMPLES_DIR / "expected"


class ExampleOutputTests(unittest.TestCase):
  def test_examples_match_expected_output(self):
    example_paths = sorted(EXAMPLES_DIR.rglob("*.roc"))
    runnable = []
    for example_path in example_paths:
      relative = example_path.relative_to(EXAMPLES_DIR)
      expected_path = EXPECTED_DIR / relative.with_suffix(".out")
      if expected_path.exists():
        runnable.append((example_path, expected_path))

    self.assertTrue(runnable, "No runnable examples found")

    for example_path, expected_path in runnable:
      buf = io.StringIO()
      with contextlib.redirect_stdout(buf):
        exit_code = cli.run_path(str(example_path))

      output = buf.getvalue().replace("\r\n", "\n").rstrip()
      expected = expected_path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()

      self.assertEqual(exit_code, 0, f"Example failed: {example_path.name}")
      self.assertEqual(output, expected, f"Output mismatch: {example_path.name}")


if __name__ == "__main__":
  unittest.main()
