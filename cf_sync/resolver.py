import os
import re
import logging

logger = logging.getLogger(__name__)

# Regex to parse filenames: matches optional 'cf' prefix, contest ID (digits), and problem index (letters + optional digits)
# Example matches:
# 1873E.py -> contest="1873", index="E"
# 71_A.cpp -> contest="71", index="A"
# 104128-F2.rs -> contest="104128", index="F2"
FILENAME_PATTERN = re.compile(r'^(?:cf[_-]?)?(?P<contest>\d+)[\s_.-]?(?P<index>[a-zA-Z]+\d*)\.(?P<ext>[a-zA-Z0-9]+)$')

# Map of common programming language suffixes to Codeforces language matches (optional verification)
EXTENSION_TO_LANG = {
    "py": "python",
    "cpp": "c++",
    "cc": "c++",
    "cxx": "c++",
    "c": "c",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "js": "javascript",
    "ts": "typescript",
    "kt": "kotlin",
    "hs": "haskell",
    "pas": "pascal",
    "cs": "c#",
    "rb": "ruby",
    "pl": "perl",
    "sh": "bash",
    "sql": "sql",
}

class SolutionResolver:
    """Scans and resolves local files matching Codeforces problems."""
    def __init__(self, local_dir: str):
        self.local_dir = local_dir
        self.solutions_map = {}
        self.scan_local_dir()

    def scan_local_dir(self):
        """Scan the local directory and build a map of normalized keys to file paths.

        The key is format "{contest_id}_{problem_index}".upper() to ensure uniqueness and simple lookups.
        """
        self.solutions_map.clear()
        if not self.local_dir or not os.path.exists(self.local_dir):
            logger.warning(f"Local solution directory does not exist: {self.local_dir}")
            return

        logger.info(f"Scanning local solutions in {self.local_dir}...")
        for root, _, files in os.walk(self.local_dir):
            for file in files:
                match = FILENAME_PATTERN.match(file)
                if match:
                    contest = match.group("contest")
                    index = match.group("index").upper()
                    ext = match.group("ext").lower()
                    
                    key = f"{contest}_{index}"
                    full_path = os.path.join(root, file)
                    
                    # Store mapping: key -> list of dictionaries (in case user has multiple languages for same problem)
                    if key not in self.solutions_map:
                        self.solutions_map[key] = []
                    
                    self.solutions_map[key].append({
                        "path": full_path,
                        "ext": ext,
                        "filename": file
                    })
        
        logger.info(f"Scanned {len(self.solutions_map)} unique problems from local files.")

    def resolve(self, contest_id: int, problem_index: str, cf_language: str = None) -> str | None:
        """Find the local path for the solution of a specific problem.

        Args:
            contest_id: The Codeforces contest ID.
            problem_index: The problem index (e.g., 'A', 'B2').
            cf_language: Optional language string from Codeforces API to help resolve ambiguities.

        Returns:
            The absolute path of the local file, or None if not found.
        """
        key = f"{contest_id}_{problem_index.upper()}"
        candidates = self.solutions_map.get(key)
        
        if not candidates:
            return None
            
        if len(candidates) == 1:
            return candidates[0]["path"]

        # If there are multiple candidate files (e.g., 1873E.py and 1873E.cpp), try matching by language
        if cf_language:
            cf_lang_lower = cf_language.lower()
            for cand in candidates:
                ext = cand["ext"]
                mapped_lang = EXTENSION_TO_LANG.get(ext, "")
                if mapped_lang and mapped_lang in cf_lang_lower:
                    return cand["path"]
                    
        # Fallback to the first available if no language match found
        return candidates[0]["path"]
