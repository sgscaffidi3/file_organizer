import os
from pathlib import Path

# Files to include
EXTENSIONS = {'.py', '.html', '.css', '.js', '.json', '.md', '.txt'}
# Folders to ignore
IGNORE_DIRS = {'venv', '__pycache__', '.git', '.idea', 'test_output', 'organized_media_output'}
# Files to ignore
IGNORE_FILES = {'package-lock.json', 'project_bundle.txt'}

def bundle():
    root = Path.cwd()
    output_file = root / "project_bundle.txt"
    
    print(f"Bundling project from: {root}")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write Header
        outfile.write(f"# FULL PROJECT SOURCE CODE\n")
        outfile.write(f"# Generated: {os.path.basename(root)}\n\n")
        
        for dirpath, dirnames, filenames in os.walk(root):
            # Modify dirnames in-place to skip ignored directories
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            
            for f in filenames:
                if f in IGNORE_FILES: continue
                
                path = Path(dirpath) / f
                if path.suffix.lower() in EXTENSIONS:
                    try:
                        # Write File Header
                        rel_path = path.relative_to(root)
                        outfile.write(f"\n{'='*60}\n")
                        outfile.write(f"FILE: {rel_path}\n")
                        outfile.write(f"{'='*60}\n")
                        
                        # Write Content
                        with open(path, 'r', encoding='utf-8', errors='ignore') as infile:
                            outfile.write(infile.read())
                        outfile.write("\n")
                        print(f"Added: {rel_path}")
                    except Exception as e:
                        print(f"Skipping {f}: {e}")

    print(f"\n✅ Bundle complete: {output_file}")

if __name__ == "__main__":
    bundle()