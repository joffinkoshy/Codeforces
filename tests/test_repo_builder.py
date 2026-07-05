import unittest
import os
import tempfile
import shutil
from cf_sync.repo_builder import RepositoryBuilder

class TestRepositoryBuilder(unittest.TestCase):
    def setUp(self):
        self.repo_dir = tempfile.mkdtemp()
        self.local_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.repo_dir)
        shutil.rmtree(self.local_dir)

    def test_sync_submission(self):
        # Create a mock source code file
        src_file = os.path.join(self.local_dir, "1873E.py")
        with open(src_file, "w") as f:
            f.write("print('Hello World')")

        meta = {
            "contestId": 1873,
            "problemIndex": "E",
            "problemName": "Building an Aquarium",
            "rating": 1200,
            "tags": ["binary search", "greedy"],
            "language": "Python 3",
            "solvedDate": "2026-07-05 12:00:00",
            "timeConsumedMillis": 150,
            "memoryConsumedBytes": 1024 * 1024
        }

        builder = RepositoryBuilder(self.repo_dir)
        rel_path = builder.sync_submission(meta, src_file)

        # Check path structure: {repo_dir}/1200/1873E/solution.py
        expected_rel_path = os.path.join("1200", "1873E", "solution.py")
        self.assertEqual(rel_path, expected_rel_path)

        expected_abs_path = os.path.join(self.repo_dir, expected_rel_path)
        self.assertTrue(os.path.exists(expected_abs_path))
        
        # Verify copied content
        with open(expected_abs_path, "r") as f:
            self.assertEqual(f.read(), "print('Hello World')")

        # Verify problem README exists
        problem_readme = os.path.join(self.repo_dir, "1200", "1873E", "README.md")
        self.assertTrue(os.path.exists(problem_readme))
        with open(problem_readme, "r") as f:
            readme_content = f.read()
            self.assertIn("Building an Aquarium", readme_content)
            self.assertIn("1200", readme_content)
            self.assertIn("binary search", readme_content)

    def test_generate_dashboard(self):
        builder = RepositoryBuilder(self.repo_dir)
        
        # Mock synced submissions state
        synced_subs = {
            "1111111": {
                "contestId": 1873,
                "problemIndex": "E",
                "problemName": "Building an Aquarium",
                "rating": 1200,
                "tags": ["binary search", "greedy"],
                "language": "Python 3",
                "solvedDate": "2026-07-05 12:00:00",
                "creationTimeSeconds": 1782250000
            },
            "2222222": {
                "contestId": 71,
                "problemIndex": "A",
                "problemName": "Way Too Long Words",
                "rating": 800,
                "tags": ["strings"],
                "language": "GNU C++17",
                "solvedDate": "2026-07-04 11:00:00",
                "creationTimeSeconds": 1782240000
            }
        }

        builder.generate_dashboard(synced_subs)
        
        # Check root README.md
        root_readme = os.path.join(self.repo_dir, "README.md")
        self.assertTrue(os.path.exists(root_readme))
        
        with open(root_readme, "r") as f:
            content = f.read()
            self.assertIn("Building an Aquarium", content)
            self.assertIn("Way Too Long Words", content)
            self.assertIn("800", content)
            self.assertIn("1200", content)
            self.assertIn("Python", content)
            self.assertIn("C++", content)

if __name__ == '__main__':
    unittest.main()
