import random
import unittest

from greyalien.lexer import LexError, tokenize
from greyalien.parser import Parser, ParseError


class ParserFuzzTests(unittest.TestCase):
    def test_random_inputs_do_not_crash(self):
        rng = random.Random(0)
        alphabet = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789{}[]()_,.;:+-*/<>!=\" \n"
        )

        for _ in range(200):
            length = rng.randint(0, 200)
            source = "".join(rng.choice(alphabet) for _ in range(length))
            try:
                tokens = tokenize(source)
                Parser(tokens).parse_program()
            except (LexError, ParseError):
                continue
            except Exception as exc:
                self.fail(f"Unexpected exception: {exc}")


if __name__ == "__main__":
    unittest.main()
