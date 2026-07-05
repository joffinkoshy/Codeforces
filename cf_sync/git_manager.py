import os
import logging
from git import Repo, exc

logger = logging.getLogger(__name__)

class GitManager:
    """Automates Git tasks like commit and push for the solutions repository."""
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
        self.repo = self._get_repo()

    def _get_repo(self) -> Repo | None:
        """Get the Repo object, initializing if necessary."""
        try:
            if not os.path.exists(os.path.join(self.repo_dir, ".git")):
                logger.info(f"Initializing new git repository at {self.repo_dir}...")
                return Repo.init(self.repo_dir)
            return Repo(self.repo_dir)
        except Exception as e:
            logger.error(f"Failed to access git repository at {self.repo_dir}: {e}")
            return None

    def has_changes(self) -> bool:
        """Check if there are any uncommitted changes in the repository."""
        if not self.repo:
            return False
        return self.repo.is_dirty(untracked_files=True)

    def commit_and_push(self, new_problems: list) -> bool:
        """Stages all changes, commits, and pushes to remote.

        Args:
            new_problems: A list of dicts/strings describing the new problems solved.

        Returns:
            True if commit and push succeeded, False otherwise.
        """
        if not self.repo:
            logger.warning("Git repository is not initialized. Skipping Git sync.")
            return False

        if not self.has_changes():
            logger.info("No changes to commit.")
            return True

        try:
            # Stage all changes (including untracked files)
            self.repo.git.add(A=True)
            
            # Construct commit message
            if len(new_problems) == 1:
                p = new_problems[0]
                commit_title = f"cf-sync: Add solution for {p['contestId']}{p['problemIndex']} - {p['problemName']}"
            else:
                commit_title = f"cf-sync: Sync {len(new_problems)} new solutions"
            
            commit_body = "Synced problems:\n" + "\n".join(
                [f"- {p['contestId']}{p['problemIndex']}: {p['problemName']} ({p['language']})" for p in new_problems]
            )
            commit_message = f"{commit_title}\n\n{commit_body}"
            
            # Commit
            self.repo.index.commit(commit_message)
            logger.info(f"Committed changes with message: '{commit_title}'")
            
            # Push changes to remote
            # We check if remote exists
            if not self.repo.remotes:
                logger.warning("No Git remotes configured. Changes committed locally, but cannot push.")
                return True
                
            origin = self.repo.remote(name="origin")
            logger.info("Pushing changes to remote repository...")
            origin.push()
            logger.info("Successfully pushed changes to remote!")
            return True
        except exc.GitCommandError as e:
            logger.error(f"Git command failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Git operations: {e}")
            return False
