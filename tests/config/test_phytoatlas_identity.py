########## 0. imports ##########
import subprocess
import unittest
from pathlib import Path

########## 1. constants ##########
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PREFIXES = (
    "docs/superpowers/plans/",
    "docs/superpowers/specs/",
)
RETIRED_TOKENS = (
    "plant" + "genewiki",
    "astro" + ".config",
    "@" + "astrojs",
)

########## 2. helpers ##########
def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    for value in result.stdout.decode("utf-8").split("\0"):
        if value and not value.startswith(EXCLUDED_PREFIXES):
            yield value

def retired_matches(path_value):
    matches = []
    lowered_path = path_value.lower()
    for token in RETIRED_TOKENS:
        if token in lowered_path:
            matches.append(f"{path_value}: path contains {token}")
    path = PROJECT_ROOT / path_value
    try:
        text = path.read_text(encoding="utf-8").lower()
    except (UnicodeDecodeError, OSError):
        return matches
    for token in RETIRED_TOKENS:
        if token in text:
            matches.append(f"{path_value}: content contains {token}")
    return matches

########## 3. tests ##########
class PhytoAtlasIdentityTest(unittest.TestCase):
    def test_tracked_active_tree_uses_phytoatlas_identity(self):
        matches = [match for path in tracked_files() for match in retired_matches(path)]
        self.assertEqual(matches, [], "\n".join(matches))
