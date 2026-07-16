########## 0. imports ##########
import unittest

########## 1. tests ##########
class PackageImportTest(unittest.TestCase):
    def test_normalizers_import_from_phytoatlas(self):
        from phytoatlas.normalize.fasta import normalize_fasta_dataset
        from phytoatlas.normalize.gff import normalize_gff3_dataset

        self.assertTrue(callable(normalize_fasta_dataset))
        self.assertTrue(callable(normalize_gff3_dataset))

if __name__ == "__main__":
    unittest.main()
