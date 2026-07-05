import os
import sys
import argparse
import json
import logging
from datetime import datetime

from cf_sync.cf_api import CodeforcesAPIClient, StateManager, CodeforcesAPIError
from cf_sync.resolver import SolutionResolver
from cf_sync.repo_builder import RepositoryBuilder
from cf_sync.git_manager import GitManager

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cf_sync")

CONFIG_FILE_NAME = "cf_sync_config.json"

def load_config(repo_dir: str) -> dict:
    """Load configuration from cf_sync_config.json if it exists."""
    config_path = os.path.join(repo_dir, CONFIG_FILE_NAME)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                logger.info(f"Loaded configuration from {config_path}")
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read config file at {config_path}: {e}")
    return {}

def save_config(repo_dir: str, config: dict):
    """Save configuration to cf_sync_config.json."""
    config_path = os.path.join(repo_dir, CONFIG_FILE_NAME)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration template saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config file: {e}")

def run_sync(args):
    """Run the synchronization process."""
    repo_dir = os.path.abspath(args.repo_dir)
    config = load_config(repo_dir)

    # Resolve arguments (command line overrides config)
    handle = args.handle or config.get("handle")
    local_dir = args.local_dir or config.get("local_dir")
    git_sync = args.git_sync if args.git_sync is not None else config.get("git_sync", False)
    count = args.count or config.get("count", 100)

    if not handle:
        logger.error("Error: Codeforces handle must be specified via --handle or in cf_sync_config.json")
        sys.exit(1)

    if not local_dir:
        logger.error("Error: Local solutions directory must be specified via --local-dir or in cf_sync_config.json")
        sys.exit(1)

    local_dir = os.path.abspath(local_dir)
    if not os.path.exists(local_dir):
        logger.error(f"Error: Local solutions directory '{local_dir}' does not exist.")
        sys.exit(1)

    logger.info("Initializing CF-Sync process...")
    logger.info(f"Codeforces Handle: {handle}")
    logger.info(f"Local Directory:   {local_dir}")
    logger.info(f"Output Repo:       {repo_dir}")

    # 1. Load Sync State
    state_file = os.path.join(repo_dir, "cf_sync_state.json")
    state_manager = StateManager(state_file)
    last_id = state_manager.last_processed_id
    logger.info(f"Last processed submission ID: {last_id}")

    # 2. Fetch Submissions from Codeforces
    api_client = CodeforcesAPIClient()
    try:
        submissions = api_client.get_user_status(handle, count=count)
    except CodeforcesAPIError as e:
        logger.error(f"Failed to query Codeforces API: {e}")
        sys.exit(1)

    # 3. Filter and Sort Submissions
    # Keep only Accepted (OK) submissions that are newer than last_processed_id
    new_accepted_subs = []
    for sub in submissions:
        sub_id = sub.get("id")
        verdict = sub.get("verdict")
        
        if verdict == "OK" and sub_id > last_id:
            new_accepted_subs.append(sub)

    # Process chronologically (oldest first)
    new_accepted_subs.sort(key=lambda x: x.get("id", 0))
    logger.info(f"Found {len(new_accepted_subs)} new accepted submissions to process since last run.")

    if not new_accepted_subs:
        logger.info("Everything is up to date!")
        # Rebuild dashboard anyway to ensure stats are fresh and links work
        repo_builder = RepositoryBuilder(repo_dir)
        repo_builder.generate_dashboard(state_manager.synced_submissions)
        sys.exit(0)

    # 4. Resolve Local Solutions & Write to Repo
    resolver = SolutionResolver(local_dir)
    repo_builder = RepositoryBuilder(repo_dir)
    
    synced_problems_in_run = []
    skipped_problems = []

    for sub in new_accepted_subs:
        sub_id = sub["id"]
        prob = sub["problem"]
        contest_id = prob.get("contestId")
        index = prob.get("index")
        name = prob.get("name", "Unknown")
        lang = sub.get("programmingLanguage")

        if not contest_id or not index:
            logger.warning(f"Submission {sub_id} missing contestId or index. Skipping.")
            continue

        # Try to resolve local code file
        local_path = resolver.resolve(contest_id, index, lang)
        if not local_path:
            skipped_problems.append(f"{contest_id}{index} - {name} ({lang})")
            continue

        # Format solved date
        creation_time = sub.get("creationTimeSeconds", 0)
        solved_date = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")

        # Compile metadata
        metadata = {
            "submissionId": sub_id,
            "contestId": contest_id,
            "problemIndex": index,
            "problemName": name,
            "rating": prob.get("rating"),
            "tags": prob.get("tags", []),
            "language": lang,
            "solvedDate": solved_date,
            "creationTimeSeconds": creation_time,
            "timeConsumedMillis": sub.get("timeConsumedMillis", 0),
            "memoryConsumedBytes": sub.get("memoryConsumedBytes", 0)
        }

        try:
            # Sync files inside repo
            rel_solution_path = repo_builder.sync_submission(metadata, local_path)
            metadata["relativeSolutionPath"] = rel_solution_path
            
            # Save to state
            state_manager.add_synced_submission(sub_id, metadata)
            synced_problems_in_run.append(metadata)
            logger.info(f"Successfully synced: {contest_id}{index} - {name}")
        except Exception as e:
            logger.error(f"Failed to sync submission {sub_id}: {e}")

    # 5. Log Summary of Syncing
    logger.info("\n=== SYNC SUMMARY ===")
    logger.info(f"Successfully Synced: {len(synced_problems_in_run)} problems")
    if skipped_problems:
        logger.warning(f"Skipped {len(skipped_problems)} problems (could not find local code files):")
        for p in skipped_problems:
            logger.warning(f"  - {p}")
        logger.warning("Ensure your local files follow name conventions like: contestId + problemIndex (e.g. 1873E.py or 71A.cpp)")

    # Save state if any new files were synced
    if synced_problems_in_run:
        state_manager.save_state()

    # 6. Rebuild Stats Dashboard
    repo_builder.generate_dashboard(state_manager.synced_submissions)

    # 7. Git Commit & Push
    if git_sync and synced_problems_in_run:
        git_manager = GitManager(repo_dir)
        git_manager.commit_and_push(synced_problems_in_run)

def run_stats(args):
    """Regenerate stats dashboard from existing local state file without querying API."""
    repo_dir = os.path.abspath(args.repo_dir)
    state_file = os.path.join(repo_dir, "cf_sync_state.json")
    
    if not os.path.exists(state_file):
        logger.error(f"Error: State file not found at {state_file}. Run a sync first.")
        sys.exit(1)
        
    state_manager = StateManager(state_file)
    repo_builder = RepositoryBuilder(repo_dir)
    logger.info("Regenerating stats dashboard from state file...")
    repo_builder.generate_dashboard(state_manager.synced_submissions)
    logger.info("Done!")

def run_init(args):
    """Initialize a configuration template."""
    repo_dir = os.path.abspath(args.repo_dir)
    template = {
        "handle": "your_codeforces_handle",
        "local_dir": "./solutions",
        "git_sync": False,
        "count": 100
    }
    
    config_path = os.path.join(repo_dir, CONFIG_FILE_NAME)
    if os.path.exists(config_path):
        logger.error(f"Configuration file already exists at {config_path}")
        sys.exit(1)
        
    save_config(repo_dir, template)
    print(f"Created config template at {config_path}. Edit this file with your handle and path.")

def main():
    parser = argparse.ArgumentParser(description="Sync Codeforces submissions to GitHub repo.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sync Subparser
    sync_parser = subparsers.add_parser("sync", help="Synchronize submissions from Codeforces API.")
    sync_parser.add_argument("--handle", help="Codeforces user handle (e.g., MikeMirzayanov)")
    sync_parser.add_argument("--local-dir", help="Path to local folder containing your solved solution source codes")
    sync_parser.add_argument("--repo-dir", default=".", help="Path to target directory (repository root) to save files")
    sync_parser.add_argument("--count", type=int, help="Number of recent submissions to inspect (default 100)")
    sync_parser.add_argument("--git-sync", action="store_true", default=None, help="Automatically commit and push changes to Git")
    sync_parser.add_argument("--no-git-sync", action="store_false", dest="git_sync", help="Disable Git commit and push")

    # Stats Subparser
    stats_parser = subparsers.add_parser("stats", help="Regenerate the repository stats dashboard README from local state.")
    stats_parser.add_argument("--repo-dir", default=".", help="Path to target repository directory")

    # Init Subparser
    init_parser = subparsers.add_parser("init", help="Create a configuration template file.")
    init_parser.add_argument("--repo-dir", default=".", help="Path to target repository directory")

    args = parser.parse_args()

    if args.command == "sync":
        run_sync(args)
    elif args.command == "stats":
        run_stats(args)
    elif args.command == "init":
        run_init(args)

if __name__ == "__main__":
    main()
