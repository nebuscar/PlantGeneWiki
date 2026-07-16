########## 0. imports ##########
import unittest
from pathlib import Path
import tomllib

########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".codex" / "config.toml"
CODEX_DIR = CONFIG_PATH.parent.resolve()
EXPECTED_ROLES = {
    "data-curator": "workspace-write",
    "vector-engineer": "workspace-write",
    "graph-engineer": "workspace-write",
    "application-engineer": "workspace-write",
    "reviewer": "read-only",
}
AGENT_LIMIT_KEYS = {
    "max_threads",
    "max_depth",
    "job_max_runtime_seconds",
}
FORBIDDEN_TEXT = (
    "api_key",
    "password",
    "secret",
    "bearer",
    "token",
    ".env",
    "/home",
    "/data",
)

########## 2. tests ##########
class CodexAgentConfigTest(unittest.TestCase):
    def assert_no_forbidden_text(self, text, excluded_text=()):
        normalized_text = text.casefold()
        for excluded in excluded_text:
            normalized_text = normalized_text.replace(excluded.casefold(), "")
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, normalized_text)

    def test_registry_uses_stable_multi_agent_limits(self):
        config_text = CONFIG_PATH.read_text(encoding="utf-8")
        config = tomllib.loads(config_text)
        self.assertEqual(set(config["features"]), {"multi_agent"})
        self.assertTrue(config["features"]["multi_agent"])
        agents = config["agents"]
        self.assertEqual(agents["max_threads"], 4)
        self.assertEqual(agents["max_depth"], 1)
        self.assertEqual(agents["job_max_runtime_seconds"], 1800)
        self.assertEqual(set(agents) - AGENT_LIMIT_KEYS, set(EXPECTED_ROLES))
        self.assert_no_forbidden_text(
            config_text,
            (role["config_file"] for role in agents.values() if isinstance(role, dict)),
        )

    def test_all_roles_have_safe_focused_config(self):
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for role_name, sandbox_mode in EXPECTED_ROLES.items():
            role = config["agents"][role_name]
            config_file = Path(role["config_file"])
            self.assertFalse(config_file.is_absolute())
            role_path = (CONFIG_PATH.parent / config_file).resolve()
            self.assertTrue(role_path.is_relative_to(CODEX_DIR))
            self.assertTrue(role["description"])
            self.assertTrue(role_path.is_file())
            role_text = role_path.read_text(encoding="utf-8")
            self.assert_no_forbidden_text(role_text)
            role_config = tomllib.loads(role_text)
            self.assertEqual(role_config["sandbox_mode"], sandbox_mode)
            self.assertGreater(len(role_config["developer_instructions"]), 200)


if __name__ == "__main__":
    unittest.main()
