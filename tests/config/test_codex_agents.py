########## 0. imports ##########
import unittest
from pathlib import Path
import tomllib

########## 1. params ##########
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".codex" / "config.toml"
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
    def test_registry_uses_stable_multi_agent_limits(self):
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(config["features"]), {"multi_agent"})
        self.assertTrue(config["features"]["multi_agent"])
        agents = config["agents"]
        self.assertEqual(agents["max_threads"], 4)
        self.assertEqual(agents["max_depth"], 1)
        self.assertEqual(agents["job_max_runtime_seconds"], 1800)
        self.assertEqual(set(agents) - AGENT_LIMIT_KEYS, set(EXPECTED_ROLES))

    def test_all_roles_have_safe_focused_config(self):
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for role_name, sandbox_mode in EXPECTED_ROLES.items():
            role = config["agents"][role_name]
            role_path = CONFIG_PATH.parent / role["config_file"]
            self.assertTrue(role["description"])
            self.assertTrue(role_path.is_file())
            role_text = role_path.read_text(encoding="utf-8")
            role_config = tomllib.loads(role_text)
            self.assertEqual(role_config["sandbox_mode"], sandbox_mode)
            self.assertGreater(len(role_config["developer_instructions"]), 200)
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, role_text.casefold())


if __name__ == "__main__":
    unittest.main()
