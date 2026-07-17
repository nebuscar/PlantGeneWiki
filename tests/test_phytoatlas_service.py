########## 0. imports ##########
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SOURCE = REPO_ROOT / "scripts" / "services" / "phytoatlas.sh"

########## 1. helpers ##########
def process_is_running(pid: int) -> bool:
    stat_path = Path(f"/proc/{pid}/stat")
    if not stat_path.exists():
        return False
    return stat_path.read_text(encoding="utf-8").split()[2] != "Z"

def wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()

########## 2. tests ##########
class PhytoAtlasServiceScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for relative in ("apps/api", "apps/web", "scripts/services"):
            (self.root / relative).mkdir(parents=True)
        self.script = self.root / "scripts" / "services" / "phytoatlas.sh"
        shutil.copy2(SCRIPT_SOURCE, self.script)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        runner = self.bin_dir / "fake-service"
        runner.write_text(
            "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\"\nsleep 300 &\nwait\n",
            encoding="utf-8",
        )
        runner.chmod(0o755)
        self.fake_python = self.bin_dir / "fake-python"
        self.fake_npm = self.bin_dir / "npm"
        shutil.copy2(runner, self.fake_python)
        shutil.copy2(runner, self.fake_npm)
        self.env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "PYTHON_BIN": str(self.fake_python),
            "PHYTOATLAS_API_PORT": "8002",
            "PHYTOATLAS_WEB_PORT": "4323",
        }
        self.tracked_pids: set[int] = set()

    def tearDown(self) -> None:
        for pid in self.tracked_pids:
            if not process_is_running(pid):
                continue
            try:
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.temp_dir.cleanup()

    def start_services(self) -> tuple[int, int]:
        subprocess.run(
            [self.script, "start"],
            cwd=self.root,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        api_pid = int((self.root / "tmp" / "phytoatlas" / "api.pid").read_text())
        web_pid = int((self.root / "tmp" / "phytoatlas" / "web.pid").read_text())
        self.tracked_pids.update((api_pid, web_pid))
        return api_pid, web_pid

    def child_pid(self, parent_pid: int) -> int:
        children_path = Path(f"/proc/{parent_pid}/task/{parent_pid}/children")
        self.assertTrue(wait_until(lambda: bool(children_path.read_text().strip())))
        child = int(children_path.read_text().split()[0])
        self.tracked_pids.add(child)
        return child

    def stop_services(self) -> None:
        subprocess.run(
            [self.script, "stop"],
            cwd=self.root,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_stop_terminates_service_descendants(self) -> None:
        api_pid, web_pid = self.start_services()
        descendants = (self.child_pid(api_pid), self.child_pid(web_pid))

        self.stop_services()

        self.assertTrue(wait_until(lambda: all(not process_is_running(pid) for pid in descendants)))

    def test_web_start_requires_the_requested_port(self) -> None:
        self.start_services()
        web_log = self.root / "logs" / "phytoatlas-web.log"
        self.assertTrue(wait_until(lambda: "--strictPort" in web_log.read_text(encoding="utf-8")))

        self.stop_services()

if __name__ == "__main__":
    unittest.main()
