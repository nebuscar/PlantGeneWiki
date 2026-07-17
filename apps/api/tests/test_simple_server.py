########## 0. imports ##########
import unittest

from phytoatlas_api.simple_server import neighbor_query_options

########## 1. tests ##########
class NeighborQueryOptionsTest(unittest.TestCase):
    def test_preserves_repeated_exclusion_parameters(self):
        options = neighbor_query_options(
            {
                "direction": ["both"],
                "predicate": ["belongs_to_species"],
                "exclude_predicate": ["has_sequence", "contains_gene"],
                "limit": ["125"],
            }
        )
        self.assertEqual(
            options,
            {
                "direction": "both",
                "predicate": "belongs_to_species",
                "exclude_predicates": ("has_sequence", "contains_gene"),
                "limit": 125,
            },
        )

if __name__ == "__main__":
    unittest.main()
