import os
import sys
import shutil
import unittest
from unittest.mock import patch
from datetime import datetime

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cf_sync.cf_api import StateManager
from cf_sync.repo_builder import RepositoryBuilder
from cf_sync.resolver import SolutionResolver
import cf_sync.cli as cli

class TestIntegrationSync(unittest.TestCase):
    def setUp(self):
        # Create temp dirs for local solutions and repo output
        self.temp_root = os.path.abspath("./temp_integration_test")
        self.local_dir = os.path.join(self.temp_root, "local_solutions")
        self.repo_dir = os.path.join(self.temp_root, "output_repo")
        
        os.makedirs(self.local_dir, exist_ok=True)
        os.makedirs(self.repo_dir, exist_ok=True)
        
        # Create dummy solution files in local_solutions
        with open(os.path.join(self.local_dir, "1873E.py"), "w") as f:
            f.write("print('Aquarium Solution')")
            
        with open(os.path.join(self.local_dir, "71A.cpp"), "w") as f:
            f.write("#include <iostream>\nint main() { return 0; }")

    def tearDown(self):
        # Clean up temp directories
        if os.path.exists(self.temp_root):
            shutil.rmtree(self.temp_root)

    @patch('requests.get')
    def test_end_to_end_sync(self, mock_get):
        # Mock the Codeforces API response for user.status
        mock_response = mock_get.return_return = unittest.mock.Mock()
        mock_response.status_code = 200
        
        # Current Unix timestamp for creationTimeSeconds
        now_ts = 1782250000
        
        mock_response.json.return_value = {
            "status": "OK",
            "result": [
                {
                    "id": 200001,
                    "contestId": 1873,
                    "creationTimeSeconds": now_ts,
                    "relativeTimeSeconds": 2147483647,
                    "problem": {
                        "contestId": 1873,
                        "index": "E",
                        "name": "Building an Aquarium",
                        "type": "PROGRAMMING",
                        "rating": 1200,
                        "tags": ["binary search", "greedy"]
                    },
                    "author": {"members": [{"handle": "test_coder"}]},
                    "programmingLanguage": "Python 3",
                    "verdict": "OK",
                    "passedTestCount": 50,
                    "timeConsumedMillis": 45,
                    "memoryConsumedBytes": 256000
                },
                {
                    "id": 200002,
                    "contestId": 71,
                    "creationTimeSeconds": now_ts + 3600,
                    "relativeTimeSeconds": 2147483647,
                    "problem": {
                        "contestId": 71,
                        "index": "A",
                        "name": "Way Too Long Words",
                        "type": "PROGRAMMING",
                        "rating": 800,
                        "tags": ["strings"]
                    },
                    "author": {"members": [{"handle": "test_coder"}]},
                    "programmingLanguage": "GNU C++17",
                    "verdict": "OK",
                    "passedTestCount": 20,
                    "timeConsumedMillis": 15,
                    "memoryConsumedBytes": 128000
                },
                {
                    "id": 200003,
                    "contestId": 1000,
                    "creationTimeSeconds": now_ts + 7200,
                    "relativeTimeSeconds": 2147483647,
                    "problem": {
                        "contestId": 1000,
                        "index": "B",
                        "name": "Light It Up",
                        "type": "PROGRAMMING",
                        "rating": 1600,
                        "tags": ["greedy", "math"]
                    },
                    "author": {"members": [{"handle": "test_coder"}]},
                    "programmingLanguage": "Python 3",
                    "verdict": "OK",
                    "passedTestCount": 42,
                    "timeConsumedMillis": 80,
                    "memoryConsumedBytes": 512000
                }
            ]
        }
        mock_get.return_value = mock_response

        # Build CLI arguments mock
        class Args:
            command = "sync"
            handle = "test_coder"
            local_dir = self.local_dir
            repo_dir = self.repo_dir
            count = 100
            git_sync = False  # Avoid running Git commands in integration tests

        # Run sync command
        cli.run_sync(Args())

        # Verify target repo folders are created for synced files
        # 1873E (rating 1200)
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "1200", "1873E", "solution.py")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "1200", "1873E", "README.md")))
        
        # 71A (rating 800)
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "800", "71A", "solution.cpp")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, "800", "71A", "README.md")))

        # 1000B (rating 1600) should be skipped because no local solution was found
        self.assertFalse(os.path.exists(os.path.join(self.repo_dir, "1600", "1000B")))

        # Verify state file was saved
        state_file_path = os.path.join(self.repo_dir, "cf_sync_state.json")
        self.assertTrue(os.path.exists(state_file_path))
        
        state_manager = StateManager(state_file_path)
        # The last processed id should be the highest synced one (which is 200002, since 200003 was skipped)
        self.assertEqual(state_manager.last_processed_id, 200002)
        self.assertIn("200001", state_manager.synced_submissions)
        self.assertIn("200002", state_manager.synced_submissions)
        self.assertNotIn("200003", state_manager.synced_submissions)

        # Verify root dashboard README.md
        root_readme_path = os.path.join(self.repo_dir, "README.md")
        self.assertTrue(os.path.exists(root_readme_path))
        with open(root_readme_path, "r") as f:
            content = f.read()
            self.assertIn("Solved Problems", content)
            self.assertIn("Building an Aquarium", content)
            self.assertIn("Way Too Long Words", content)
            self.assertNotIn("Light It Up", content) # Skipped

if __name__ == "__main__":
    unittest.main()
