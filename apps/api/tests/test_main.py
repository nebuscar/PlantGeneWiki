########## 0. imports ##########
import unittest

from phytoatlas_api.main import app, health

########## 1. tests ##########
class ApiIdentityTest(unittest.TestCase):
    def test_api_uses_phytoatlas_identity(self):
        self.assertEqual(app.title, "PhytoAtlas API")
        self.assertEqual(health(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
