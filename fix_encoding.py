
from pathlib import Path
import os

def clean_file(path_str):
    path = Path(path_str)
    if not path.exists():
        print(f"Skipping {path}: Not found")
        return

    try:
        content = path.read_text(encoding='utf-8')
        original_len = len(content)
        
        # Apply fixes
        new_content = content.replace('ג€”', '—').replace('ג', '')
        
        if len(new_content) != original_len:
            path.write_text(new_content, encoding='utf-8')
            print(f"Fixed {path}: Replaced {original_len - len(new_content)} characters/artifacts")
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
