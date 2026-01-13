# ==============================================================================
# File: release.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of release automation script.",
    "Implemented automated changelog clearing and archiving.",
    "Implemented token estimation logic.",
    "Added logic to inject --changes CLI argument into target files.",
    "Added logic to detect and auto-fix missing changelog variables with user prompt.",
    "IMPROVEMENT: Enhanced token estimation to compare Current Load vs New Bundle Size.",
    "FIX: Calculated projected bundle size correctly during --dry-run.",
    "FEATURE: Added --preview_notes flag to output generated release notes to console without writing to disk."
]
_REL_CHANGES = [5, 7]
# ------------------------------------------------------------------------------
import os
import sys
import argparse
import re
import datetime
from pathlib import Path
from config_manager import ConfigManager
from version_util import get_python_files, print_version_info, print_change_history

# Regex Patterns for Code Modification
RE_MINOR = re.compile(r"^(_MINOR_VERSION\s*=\s*)(\d+)", re.MULTILINE)
RE_CHANGELOG = re.compile(r"^(_CHANGELOG_ENTRIES\s*=\s*\[)(.*?)(\])", re.DOTALL | re.MULTILINE)
RE_REL_CHANGES = re.compile(r"^(_REL_CHANGES\s*=\s*\[)(.*?)(\])", re.DOTALL | re.MULTILINE)

class ReleaseManager:
    def __init__(self, dry_run=False, current_tokens=0, preview_notes=False):
        self.root = Path(__file__).parent.resolve()
        self.config = ConfigManager(self.root / 'organizer_config.json')
        self.dry_run = dry_run
        self.preview_notes = preview_notes
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
            if py_file.name == "release.py": continue 

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

        # 3. Preview Notes (New Feature)
        if self.preview_notes:
            print("\n" + "="*60)
            print("📄 PREVIEW RELEASE NOTES")
            print("="*60)
            print(notes_content.strip())
            print("="*60 + "\n")

        # 4. Save Release Notes
        if not self.dry_run:
            self.release_notes_dir.mkdir(exist_ok=True)
            notes_path = self.release_notes_dir / f"RELEASE_v{self.release_ver_str}.md"
            with open(notes_path, 'w', encoding='utf-8') as f:
                f.write(notes_content)
            print(f"\n📝 Release Notes saved to: {notes_path}")

        # 5. Generate Clean Bundle (Calculates size in dry-run too)
        bundle_size = self.create_bundle()

        # 6. Token Statistics
        self.print_token_stats(bundle_size)

    def print_token_stats(self, bundle_size_bytes):
        print("-" * 60)
        print("TOKEN & EFFICIENCY REPORT")
        print("-" * 60)
        
        # Heuristic: 1 Token ~= 4 Characters
        tokens_saved = int(self.total_chars_removed / 4)
        new_start_tokens = int(bundle_size_bytes / 4)
        
        print(f"Files Processed:      {self.files_processed}")
        print(f"Changelog Cleaned:    {tokens_saved:,} tokens (removed from source)")
        print(f"New Bundle Size:      {new_start_tokens:,} tokens (estimated)")
        
        if self.current_tokens > 0:
            print(f"\n[Current Session]")
            print(f"Current Usage:        {self.current_tokens:,} tokens")
            
            print(f"\n[Next Session (Fresh Start)]")
            print(f"Project Codebase:     {new_start_tokens:,} tokens")
            
            savings = self.current_tokens - new_start_tokens
            if savings > 0:
                print(f"Potential Savings:    {savings:,} tokens if you restart now.")
        else:
            print("\n(Pass --tokens [count] to see comparison against current session)")
            
        print("-" * 60)

    def inject_missing_cli(self, content, filename):
        """Injects --changes argument and handler if missing."""
        
        # 1. Inject Argument Definition
        if "parser.add_argument" in content and "'--changes'" not in content:
            if not self.dry_run:
                sub_pattern = r"(parser\.add_argument\('-v'.*?\))"
                replacement = r"\1\n    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')"
                content = re.sub(sub_pattern, replacement, content, count=1)
                print(f"   + Injected --changes flag definition into {filename}")

        # 2. Inject Argument Handler
        if "if args.version:" in content and "args.changes" not in content:
            if not self.dry_run:
                handler_code = (
                    "\n    if hasattr(args, 'changes') and args.changes:\n"
                    "        from version_util import print_change_history\n"
                    "        print_change_history(__file__, args.changes)\n"
                    "        sys.exit(0)\n"
                )
                content = content.replace("if args.version:", handler_code + "    if args.version:")
                print(f"   + Injected --changes handler logic into {filename}")
                
        return content

    def process_file(self, filepath: Path):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # --- STEP A: Auto-Conversion Check ---
        if "_CHANGELOG_ENTRIES" not in content:
            print(f"\n⚠️  File {filepath.name} is missing changelog structure.")
            if not self.dry_run:
                resp = input(f"   Auto-convert {filepath.name} to standard format? [y/N]: ").strip().lower()
                if resp == 'y':
                    insertion = (
                        "\n# VERSIONING\n"
                        "_MAJOR_VERSION = 0\n"
                        "_MINOR_VERSION = 1\n"
                        "_CHANGELOG_ENTRIES = [\"Automatically initialized by release script.\"]\n"
                        "_REL_CHANGES = []\n"
                    )
                    header_end = content.find("import")
                    if header_end == -1: header_end = 0
                    content = insertion + content
                    print(f"   + Initialized changelog in {filepath.name}")
                else:
                    return content, None, 0
            else:
                 print(f"   [Dry Run] Would prompt to auto-convert {filepath.name}")
                 return content, None, 0

        # --- STEP B: CLI Injection ---
        content = self.inject_missing_cli(content, filepath.name)

        # --- STEP C: Release Logic ---
        match_log = RE_CHANGELOG.search(content)
        if not match_log: return content, None, 0
            
        raw_log_entries = match_log.group(2)
        try:
            entries_list = eval(f"[{raw_log_entries}]")
            count = len(entries_list)
        except:
            count = 0
            entries_list = []

        if count == 0: return content, None, 0

        log_txt = f"## {filepath.name}\n"
        for item in entries_list:
            log_txt += f"- {item}\n"
        log_txt += "\n"

        # 1. Update Minor Version
        new_content = RE_MINOR.sub(f"\\g<1>{self.target_minor}", content)

        # 2. Update _REL_CHANGES
        match_rel = RE_REL_CHANGES.search(new_content)
        if match_rel:
            existing_list_str = match_rel.group(2)
            try:
                existing_list = eval(f"[{existing_list_str}]")
                existing_list.append(count)
                new_content = RE_REL_CHANGES.sub(f"_REL_CHANGES = {str(existing_list)}", new_content)
            except: pass
        else:
            m_log_new = RE_CHANGELOG.search(new_content)
            if m_log_new:
                start = m_log_new.start()
                insertion = f"_REL_CHANGES = [{count}]\n"
                new_content = new_content[:start] + insertion + new_content[start:]

        # 3. Clear Changelog
        new_content = RE_CHANGELOG.sub(
            f'_CHANGELOG_ENTRIES = [\n    "Released as v{self.release_ver_str}"\n]', 
            new_content
        )

        chars_saved = len(content) - len(new_content)
        return new_content, log_txt, chars_saved

    def create_bundle(self):
        bundle_path = self.root / "clean_project_bundle.txt"
        ignore = {'.git', 'venv', '__pycache__', 'test_output', 'organized_media_output', 'test_assets', 'release_notes'}
        
        total_size = 0
        
        if not self.dry_run:
            # LIVE MODE: Write the file and then get its size
            with open(bundle_path, 'w', encoding='utf-8') as outfile:
                outfile.write(f"# CLEAN PROJECT BUNDLE v{self.release_ver_str}\n")
                outfile.write(f"# Generated: {datetime.datetime.now()}\n\n")
                
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
            return os.path.getsize(bundle_path)
            
        else:
            # DRY RUN MODE: Estimate based on current disk size
            print(f"🔎 Would create bundle: {bundle_path.name}")
            
            # Header overhead
            total_size += 100 
            
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in ignore]
                for filename in filenames:
                    if filename in ['clean_project_bundle.txt', 'project_bundle.txt', 'test_run.log', 'test_run.log.txt']: continue
                    if filename.endswith(('.pyc', '.sqlite')): continue
                    
                    filepath = Path(dirpath) / filename
                    
                    # Add current file size
                    total_size += os.path.getsize(filepath)
                    # Add separator overhead (~80 chars)
                    total_size += 80
            
            # Subtract what we plan to delete
            return total_size - self.total_chars_removed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Release Manager")
    parser.add_argument('--dry-run', action='store_true', help="Simulate the release.")
    parser.add_argument('--preview_notes', action='store_true', help="Print generated release notes to console.")
    parser.add_argument('--tokens', type=int, default=0, help="Current token usage for estimate.")
    # Standard compliance
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all')
    
    args = parser.parse_args()
    
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Release Manager")
        sys.exit(0)
        
    if args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    
    manager = ReleaseManager(dry_run=args.dry_run, current_tokens=args.tokens, preview_notes=args.preview_notes)
    manager.run()