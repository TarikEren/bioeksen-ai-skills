"""Minting a change identifier, through the kit's wrapper of the skill's script."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from change_id import CHANGE_ID, mint, software_id


class MintTest(unittest.TestCase):
    def test_timestamp_is_utc_plus_three(self):
        minted = mint("auth-service", datetime(2026, 10, 5, 9, 0, 0, tzinfo=timezone.utc))
        self.assertTrue(minted.startswith("auth-service-20261005T120000-"), minted)

    def test_timestamp_rolls_over_to_the_next_day(self):
        minted = mint("auth-service", datetime(2026, 10, 5, 22, 30, 0, tzinfo=timezone.utc))
        self.assertTrue(minted.startswith("auth-service-20261006T013000-"), minted)

    def test_minted_identifier_matches_the_format_and_carries_no_z(self):
        minted = mint("auth-service")
        parsed = CHANGE_ID.match(minted)
        self.assertIsNotNone(parsed, minted)
        self.assertFalse(parsed["timestamp"].endswith("Z"), minted)

    def test_two_identifiers_minted_together_differ(self):
        moment = datetime(2026, 10, 5, 9, 0, 0, tzinfo=timezone.utc)
        self.assertNotEqual(mint("x", moment), mint("x", moment))


class FormatTest(unittest.TestCase):
    def test_identifier_minted_before_utc_plus_three_is_still_accepted(self):
        self.assertIsNotNone(CHANGE_ID.match("bioeksen-sds-20260929T132418Z-e830"))

    def test_explicit_offset_is_rejected(self):
        self.assertIsNone(CHANGE_ID.match("bioeksen-sds-20261005T120000+0300-ab12"))

    def test_short_random_tail_is_rejected(self):
        self.assertIsNone(CHANGE_ID.match("bioeksen-sds-20261005T120000-ab1"))


class SoftwareIdTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / ".bioeksen").mkdir()
        self.file = self.root / ".bioeksen" / "software-id"

    def test_reads_the_stored_id_ignoring_surrounding_whitespace_and_crlf(self):
        self.file.write_bytes(b"bio-kys\r\n")
        self.assertEqual(software_id(self.root), "bio-kys")

    def test_missing_file_refuses_to_guess(self):
        self.file.parent.rmdir()
        with self.assertRaises(SystemExit) as raised:
            software_id(self.root)
        self.assertIn("never guessed", str(raised.exception))

    def test_empty_file_refuses_to_guess(self):
        self.file.write_text("\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            software_id(self.root)

    def test_malformed_id_is_refused(self):
        self.file.write_text("Bio KYS\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            software_id(self.root)
        self.assertIn("not a software id", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
