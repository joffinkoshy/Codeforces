import unittest
import os
import tempfile
import shutil
from cf_sync.resolver import SolutionResolver

class TestSolutionResolver(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for local solver files
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after tests
        shutil.rmtree(self.test_dir)

    def touch_file(self, filename):
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w') as f:
            f.write("# Dummy Codeforces Solution")
        return path

    def test_filename_parsing(self):
        # Create various solution files matching CF problem naming patterns
        self.touch_file("1873E.py")
        self.touch_file("71A.cpp")
        self.touch_file("104128_B2.java")
        self.touch_file("cf-1234-A.cpp")
        self.touch_file("random_file.txt") # should not match

        resolver = SolutionResolver(self.test_dir)

        # Verify correct matching
        self.assertIsNotNone(resolver.resolve(1873, "E"))
        self.assertIsNotNone(resolver.resolve(71, "A"))
        self.assertIsNotNone(resolver.resolve(104128, "B2"))
        self.assertIsNotNone(resolver.resolve(1234, "A"))
        
        # Verify non-matching
        self.assertIsNone(resolver.resolve(999, "F"))

    def test_extension_matching(self):
        # Multiple files for the same contest/index in different languages
        p_py = self.touch_file("1873E.py")
        p_cpp = self.touch_file("1873E.cpp")

        resolver = SolutionResolver(self.test_dir)

        # Match Python
        res_py = resolver.resolve(1873, "E", "Python 3")
        self.assertEqual(res_py, p_py)

        # Match C++
        res_cpp = resolver.resolve(1873, "E", "GNU C++20 (64bit)")
        self.assertEqual(res_cpp, p_cpp)

if __name__ == '__main__':
    unittest.main()
