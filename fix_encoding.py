from pathlib import Path
import os
import sys

# Add generator to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from generator.utils.encoding import normalize_mojibake

def clean_file(path_str):
    path = Path(path_str)
    if not path.exists():
        print(f"Skipping {path}: Not found")
        return

    try:
        content = path.read_text(encoding='utf-8')
        original_len = len(content)
        
        # Apply targeted mojibake fixes (preserves legitimate Hebrew/Unicode)
        new_content = normalize_mojibake(content)
        
        if len(new_content) != original_len:
            path.write_text(new_content, encoding='utf-8')
            print(f"Fixed {path}: Replaced {original_len - len(new_content)} mojibake artifacts")
        else:
            print(f"Checked {path}: No artifacts found")
            
    except Exception as e:
        print(f"Error processing {path}: {e}")

# Target files
files_to_clean = [
    ".clinerules/rules.md",
    "project-rules-generator-rules.md"
]

for f in files_to_clean:
    clean_file(f)
