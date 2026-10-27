"""Turn a NeetCode / LeetCode problem URL (or a bare slug) into the problem slug.

  https://neetcode.io/problems/two-integer-sum/question?list=neetcode150  -> two-integer-sum
  https://leetcode.com/problems/two-sum/description/                      -> two-sum
  two-integer-sum                                                           -> two-integer-sum

Usage: uv run python slug_from_url.py <url-or-slug> [...]
Tests: uv run python -m unittest tests.test_slug_from_url
"""
import re
import sys
from urllib.parse import urlparse

_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def slug_from_url(value: str) -> str:
    """Return the slug for a NeetCode/LeetCode URL or pass a bare slug through. Raises ValueError otherwise."""
    if value is None:
        raise ValueError("empty value")
    s = value.strip().strip("<>\"'")
    if not s:
        raise ValueError("empty value")
    if "://" not in s and "/" not in s and "?" not in s:
        if _SLUG.match(s):
            return s
        raise ValueError(f"not a slug: {value!r}")
    if "://" not in s:
        s = "https://" + s
    path = urlparse(s).path  # drops query string and fragment
    parts = [p for p in path.split("/") if p]
    if "problems" in parts:
        i = parts.index("problems")
        if i + 1 < len(parts) and _SLUG.match(parts[i + 1]):
            return parts[i + 1]
    raise ValueError(f"no /problems/<slug> in {value!r}")


def slugs_from_args(values):
    """Convert a list of URLs/slugs; de-duplicate while keeping order."""
    out = []
    for v in values or []:
        s = slug_from_url(v)
        if s not in out:
            out.append(s)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for v in sys.argv[1:]:
        print(slug_from_url(v))
