import logging
import time
import requests

logger = logging.getLogger(__name__)

class CodeforcesAPIError(Exception):
    """Exception raised for errors in the Codeforces API."""
    pass

class CodeforcesAPIClient:
    """Client for interacting with the Codeforces API."""
    BASE_URL = "https://codeforces.com/api"

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._last_request_time = 0.0

    def _throttle(self):
        """Throttle requests to respect Codeforces API guidelines."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def get_user_status(self, handle: str, count: int = 100) -> list:
        """Fetch submissions of a user.

        Args:
            handle: The Codeforces user handle.
            count: Number of recent submissions to fetch.

        Returns:
            A list of submission objects if successful.
        """
        self._throttle()
        url = f"{self.BASE_URL}/user.status"
        params = {
            "handle": handle,
            "from": 1,
            "count": count
        }
        
        try:
            logger.info(f"Fetching recent submissions for user {handle}...")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") != "OK":
                raise CodeforcesAPIError(f"API Error: {data.get('comment', 'Unknown error')}")
            
            return data.get("result", [])
        except requests.RequestException as e:
            raise CodeforcesAPIError(f"Network error communicating with Codeforces: {e}")
        except ValueError as e:
            raise CodeforcesAPIError(f"Invalid JSON response from Codeforces: {e}")

class StateManager:
    """Manages the sync state stored locally in the repo."""
    def __init__(self, state_file_path: str):
        self.state_file_path = state_file_path
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Load state from the JSON file."""
        import json
        import os
        if not os.path.exists(self.state_file_path):
            return {
                "last_processed_submission_id": 0,
                "synced_submissions": {}
            }
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load state file {self.state_file_path}: {e}. Starting fresh.")
            return {
                "last_processed_submission_id": 0,
                "synced_submissions": {}
            }

    def save_state(self):
        """Save the current state to the JSON file."""
        import json
        import os
        dir_name = os.path.dirname(self.state_file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            logger.info(f"State saved to {self.state_file_path}")
        except Exception as e:
            logger.error(f"Failed to save state to {self.state_file_path}: {e}")

    @property
    def last_processed_id(self) -> int:
        return self.state.get("last_processed_submission_id", 0)

    @last_processed_id.setter
    def last_processed_id(self, val: int):
        self.state["last_processed_submission_id"] = val

    @property
    def synced_submissions(self) -> dict:
        return self.state.setdefault("synced_submissions", {})

    def add_synced_submission(self, submission_id: int, metadata: dict):
        """Add a submission to the synced registry."""
        self.synced_submissions[str(submission_id)] = metadata
        # Update last_processed_id if this is higher
        if submission_id > self.last_processed_id:
            self.last_processed_id = submission_id
