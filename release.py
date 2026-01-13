# ==============================================================================
# File: release.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of release automation script."
]
# ------------------------------------------------------------------------------
import os
import sys
import argparse
import re
import datetime
from pathlib import Path
from config_manager import ConfigManager
from version_util import get_python_files

# Regex Patterns for Safe Replacement
# Matches: _MINOR_VERSION = 123
RE_MINOR = re.compile(r"^(_MINOR_VERSION\s*=\s*)(\d+)", re.MULTILINE)
# Matches: _CHANGELOG_ENTRIES = [ ... ] (across multiple lines)
RE_CHANGELOG = re.compile(r"^(_CHANGELOG_ENTRIES\s*=\s*\[)(.*?)(\])", re.DOTALL | re.MULTILINE)
# Matches: _REL_CHANGES = [ ... ] OR detects if it's missing
RE_REL_CHANGES = re.compile(r"^(_REL_CHANGES\s*=\s*\[)(.*?)(\])", re.DOTALL | re.MULTILINE)

class ReleaseManager:
    def __init__(self, dry_run=False, current_tokens=0):
        self.root = Path(__file__).parent.resolve()
        self.config = ConfigManager(self.root / 'organizer_config.json')
        self.dry_run = dry_run
        self.current_tokens = current_tokens
        
        self.target_minor = self.config.PROJECT_VERSION[1]
        self.release_ver_str = f"0.{self.target_minor}.0"
        self.release_notes_dir = self.root / "release_notes"
        
        self.total_chars_removed = 0
        self.files_processed = 0

    def run(self):
        print(f"\n🚀 STARTING RELEASE PROCESS (Target: v{self.release_ver_str})")
        print(f"   Mode: {'DRY RUN (No changes)' if self.dry_run else 'LIVE (Writing files)'}")
        print("-" * 60)

        # 1. Prepare Release Notes File
        notes_content = f"# Release v{self.release_ver_str}\n"
        notes_content += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 2. Process Files
        for py_file in get_python_files(self.root):
            if py_file.name == "release.py": continue # Self-preservation

            processed_content, log_entry, chars_saved = self.process_file(py_file)
            
            if log_entry:
                notes_content += log_entry
                self.total_chars_removed += chars_saved
                self.files_processed += 1
                
                if not self.dry_run:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(processed_content)
                    print(f"✅ Updated: {py_file.name}")
                else:
                    print(f"🔎 Would Update: {py_file.name} (Saved {chars_saved} chars)")

        # 3. Save Release Notes
        if not self.dry_run:
            self.release_notes_dir.mkdir(exist_ok=True)
            notes_path = self.release_notes_dir / f"RELEASE_v{self.release_ver_str}.md"
            with open(notes_path, 'w', encoding='utf-8') as f:
                f.write(notes_content)
            print(f"\n📝 Release Notes saved to: {notes_path}")

        # 4. Generate Clean Bundle
        self.create_bundle()

        # 5. Stats
        print("-" * 60)
        print(f"Files Processed: {self.files_processed}")
        print(f"Characters Removed: {self.total_chars_removed}")
        
        # Token Estimate (Approx 4 chars per token)
        est_tokens = self.total_chars_removed / 4
        print(f"Estimated Context Savings: ~{int(est_tokens)} tokens")
        
        if self.current_tokens > 0:
            print(f"Current Load: {self.current_tokens}")
            print(f"Projected New Load: {int(self.current_tokens - est_tokens)}")

    def process_file(self, filepath: Path):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract Changelog Content for Notes
        match_log = RE_CHANGELOG.search(content)
        if not match_log:
            return content, None, 0
            
        raw_log_entries = match_log.group(2)
        # Parse roughly to count entries. 
        # We assume entries are comma-separated strings.
        # A simple approximation is counting lines or quotes.
        # Let's rely on standard eval for parsing the list literal to get exact count
        try:
            # Safe eval of the list part
            entries_list = eval(f"[{raw_log_entries}]")
            count = len(entries_list)
        except:
            print(f"⚠️  Warning: Could not parse changelog in {filepath.name}, assuming 0.")
            count = 0
            entries_list = []

        if count == 0:
            return content, None, 0

        # Formatted log entry for Release Notes
        log_txt = f"## {filepath.name}\n"
        for item in entries_list:
            log_txt += f"- {item}\n"
        log_txt += "\n"

        # --- MODIFICATIONS ---

        # 1. Update Minor Version
        new_content = RE_MINOR.sub(f"\\g<1>{self.target_minor}", content)

        # 2. Update _REL_CHANGES
        # If it exists, append. If not, insert it before Changelog.
        match_rel = RE_REL_CHANGES.search(new_content)
        if match_rel:
            # Existing list found
            existing_list_str = match_rel.group(2)
            try:
                # We need to construct the new list string.
                # "1, 5" -> "1, 5, {count}"
                # We do this textually to preserve formatting if possible, but simple replacement is safer
                existing_list = eval(f"[{existing_list_str}]")
                existing_list.append(count)
                new_list_str = str(existing_list) # e.g. "[1, 5, 3]"
                # Replace the whole block
                new_content = RE_REL_CHANGES.sub(f"_REL_CHANGES = {new_list_str}", new_content)
            except:
                print(f"⚠️  Failed to update _REL_CHANGES in {filepath.name}")
        else:
            # Insert new variable before _CHANGELOG_ENTRIES
            # We look for the start of the changelog match in the *modified* content
            # Re-search because indices shifted
            m_log_new = RE_CHANGELOG.search(new_content)
            if m_log_new:
                start = m_log_new.start()
                insertion = f"_REL_CHANGES = [{count}]\n"
                new_content = new_content[:start] + insertion + new_content[start:]

        # 3. Clear Changelog
        # Re-search again just to be safe with indices
        new_content = RE_CHANGELOG.sub(
            f'_CHANGELOG_ENTRIES = [\n    "Released as v{self.release_ver_str}"\n]', 
            new_content
        )

        chars_saved = len(content) - len(new_content)
        return new_content, log_txt, chars_saved

    def create_bundle(self):
        bundle_path = self.root / "clean_project_bundle.txt"
        if self.dry_run:
            print(f"🔎 Would create bundle: {bundle_path.name}")
            return

        print(f"📦 Packaging clean source to: {bundle_path.name}")
        # Use bundle_project.py logic or simple walk
        # Using simple walk here to ensure it uses the *in-memory* state if we wanted, 
        # but since we wrote files to disk, we can read them back.
        
        # Ignoring patterns
        ignore = {'.git', 'venv', '__pycache__', 'test_output', 'organized_media_output', 'test_assets'}
        
        with open(bundle_path, 'w', encoding='utf-8') as outfile:
            outfile.write(f"# CLEAN PROJECT BUNDLE v{self.release_ver_str}\n")
            outfile.write(f"# Generated: {datetime.datetime.now()}\n\n")
            
            for f in get_python_files(self.root):
                # Also include HTML/CSS/JSON/MD
                # Actually, get_python_files only gets .py. Let's expand slightly for the bundle.
                pass 
            
            # Re-implement simple walk for bundle to catch non-py files
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in ignore]
                for filename in filenames:
                    if filename in ['clean_project_bundle.txt', 'project_bundle.txt', 'test_run.log', 'test_run.log.txt']: continue
                    if filename.endswith(('.pyc', '.sqlite')): continue
                    
                    filepath = Path(dirpath) / filename
                    rel_path = filepath.relative_to(self.root)
                    
                    outfile.write(f"\n{'='*60}\n")
                    outfile.write(f"FILE: {rel_path}\n")
                    outfile.write(f"{'='*60}\n")
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"# Error reading file: {e}")
                    outfile.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help="Simulate the release without changing files.")
    parser.add_argument('--tokens', type=int, default=0, help="Current token usage for estimate calculation.")
    args = parser.parse_args()
    
    manager = ReleaseManager(dry_run=args.dry_run, current_tokens=args.tokens)
    manager.run()