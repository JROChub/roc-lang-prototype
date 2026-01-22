import unittest

import greyalien


class VersionTests(unittest.TestCase):
    def test_resolve_version_fallback(self):
        original_version = greyalien.version
        try:

            def _raise(_name: str) -> str:
                raise greyalien.PackageNotFoundError

            greyalien.version = _raise
            self.assertEqual(greyalien._resolve_version(), "0.0.0+local")
        finally:
            greyalien.version = original_version

    def test_resolve_version_success(self):
        original_version = greyalien.version
        try:
            greyalien.version = lambda _name: "1.2.3"
            self.assertEqual(greyalien._resolve_version(), "1.2.3")
        finally:
            greyalien.version = original_version


if __name__ == "__main__":
    unittest.main()
