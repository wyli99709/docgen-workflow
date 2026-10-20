"""Tests for tolerant JSON extraction."""

from __future__ import annotations

import unittest

from docgen.utils.jsonx import extract_json_object, truncate


class JsonExtractionTest(unittest.TestCase):
    def test_plain_object(self) -> None:
        self.assertEqual(extract_json_object('{"a": 1}'), {"a": 1})

    def test_fenced_object(self) -> None:
        text = '先说明一下：\n```json\n{"a": 1}\n```\n'
        self.assertEqual(extract_json_object(text), {"a": 1})

    def test_surrounding_prose(self) -> None:
        text = '结果如下：{"a": {"b": "}"}} 谢谢'
        self.assertEqual(extract_json_object(text), {"a": {"b": "}"}})

    def test_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_json_object("没有 JSON")
        with self.assertRaises(ValueError):
            extract_json_object("")

    def test_truncate(self) -> None:
        self.assertEqual(truncate("abc", 10), "abc")
        self.assertIn("已截断", truncate("abcdef", 3))


if __name__ == "__main__":
    unittest.main()
