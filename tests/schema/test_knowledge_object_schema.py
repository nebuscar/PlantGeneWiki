import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class KnowledgeObjectSchemaTests(unittest.TestCase):
    def test_schema_allows_sequence_record_objects(self):
        schema = json.loads((PROJECT_ROOT / "schemas" / "knowledge_object.schema.json").read_text(encoding="utf-8"))
        object_types = schema["properties"]["object_type"]["enum"]
        self.assertIn("SequenceRecord", object_types)


if __name__ == "__main__":
    unittest.main()
