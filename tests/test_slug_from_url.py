import unittest
from slug_from_url import slug_from_url, slugs_from_args


class TestSlugFromUrl(unittest.TestCase):
    def test_neetcode_question(self):
        self.assertEqual(slug_from_url("https://neetcode.io/problems/two-integer-sum/question"), "two-integer-sum")

    def test_neetcode_with_query(self):
        self.assertEqual(slug_from_url("https://neetcode.io/problems/is-palindrome/question?list=neetcode150"), "is-palindrome")
        self.assertEqual(slug_from_url("https://neetcode.io/problems/reverse-string/question?list=companyTagged&company=Google"), "reverse-string")

    def test_neetcode_other_tabs(self):
        for tail in ("solution", "history", "", "/"):
            self.assertEqual(slug_from_url(f"https://neetcode.io/problems/lru-cache/{tail}"), "lru-cache")

    def test_leetcode(self):
        self.assertEqual(slug_from_url("https://leetcode.com/problems/two-sum/description/"), "two-sum")
        self.assertEqual(slug_from_url("https://leetcode.com/problems/two-sum/"), "two-sum")
        self.assertEqual(slug_from_url("https://leetcode.com/problems/two-sum/submissions/123/"), "two-sum")
        self.assertEqual(slug_from_url("leetcode.com/problems/3sum/?envType=daily"), "3sum")

    def test_bare_slug(self):
        self.assertEqual(slug_from_url("two-integer-sum"), "two-integer-sum")
        self.assertEqual(slug_from_url("  binarySearchTree "), "binarySearchTree")

    def test_angle_brackets_and_quotes(self):
        self.assertEqual(slug_from_url("<https://neetcode.io/problems/path-sum/question>"), "path-sum")
        self.assertEqual(slug_from_url("'coin-change'"), "coin-change")

    def test_invalid(self):
        for bad in ("", "   ", "https://neetcode.io/practice", "https://neetcode.io/problems/", "not a slug!", None):
            with self.assertRaises(ValueError):
                slug_from_url(bad)

    def test_slugs_from_args_dedup(self):
        self.assertEqual(
            slugs_from_args(["https://neetcode.io/problems/path-sum/question", "path-sum", "lru-cache"]),
            ["path-sum", "lru-cache"],
        )


if __name__ == "__main__":
    unittest.main()
