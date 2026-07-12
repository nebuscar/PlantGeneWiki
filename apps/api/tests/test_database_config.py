import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from plantgenewiki_api.database.config import DatabaseSettings

class DatabaseSeetingsTest(unittest.TestCase):
    def test_loads_settings_and_builds_sqlalchemy_url(self):
        # 使用临时目录模拟apps/api/.env, 避免读取真实账号和密码
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "DB_HOST=127.0.0.1",
                        "DB_PORT=3306",
                        "DB_NAME=pgw_dev",
                        "DB_USER=nizhu"
                        # 特意包含@和:，验证密码不会破坏数据库URL
                        'DB_PASSWORD="p@ss:word"'
                    ]
                ),
                encoding="utf-8"
            )
            
            # 清空当前进程的环境变量，防止真实 DB_* 配置干扰测试。
            with patch.dict(os.environ, {}, clear=True):
                settings = DatabaseSettings.from_env(env_path)

        # 验证字符串和端口是否被正确读取、转换。
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 3306)
        self.assertEqual(settings.database, "pgw_dev")
        self.assertEqual(settings.user, "nizhu")

        # 验证 SQLAlchemy URL 的驱动、密码和数据库名称。
        url = settings.sqlalchemy_url
        self.assertEqual(url.drivername, "mysql+pymysql")
        self.assertEqual(url.password, "p@ss:word")
        self.assertEqual(url.database, "pgw_dev")


if __name__ == "__main__":
    unittest.main()