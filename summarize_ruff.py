import re
from collections import defaultdict
from pathlib import Path


def summarize_ruff_errors(input_file: str, output_file: str):
    content = Path(input_file).read_text(encoding="utf-8")
    lines = content.splitlines()

    error_pattern = re.compile(r"^([A-Z]+\d+)\s+(.+)$")
    file_pattern = re.compile(r"^\s+-->\s+(.+):\d+:\d+")

    errors_by_code = defaultdict(int)
    errors_by_file = defaultdict(int)
    error_descriptions = {}

    current_code = None

    for line in lines:
        code_match = error_pattern.match(line)
        if code_match:
            current_code = code_match.group(1)
            desc = code_match.group(2)
            errors_by_code[current_code] += 1
            if current_code not in error_descriptions:
                error_descriptions[current_code] = desc
            continue

        file_match = file_pattern.match(line)
        if file_match and current_code:
            file_path = file_match.group(1)
            errors_by_file[file_path] += 1

    # Generate Markdown
    md = ["# 🛡️ Ruff Code Quality Report\n"]
    md.append(f"**Total Errors:** {sum(errors_by_code.values())}\n")

    md.append("## 📊 Errors by Type\n")
    md.append("| Code | Count | Description |")
    md.append("|---|---|---|")

    sorted_codes = sorted(errors_by_code.items(), key=lambda x: x[1], reverse=True)
    for code, count in sorted_codes:
        desc = error_descriptions.get(code, "Unknown error")
        # Truncate long descriptions
        if len(desc) > 60:
            desc = desc[:57] + "..."
        md.append(f"| **{code}** | {count} | {desc} |")

    md.append("\n## 📁 Top 10 Affected Files\n")
    md.append("| File | Errors |")
    md.append("|---|---|")

    sorted_files = sorted(errors_by_file.items(), key=lambda x: x[1], reverse=True)
    for file_path, count in sorted_files[:10]:
        md.append(f"| `{file_path}` | {count} |")

    md.append("\n## 🔍 Analysis & Recommendations\n")

    top_codes = [c[0] for c in sorted_codes[:3]]
    if "F401" in top_codes:
        md.append(
            "- **F401 (Unused Imports)**: High frequency. Run `ruff check . --fix` to safely remove most of these automatically."
        )
    if "F841" in top_codes:
        md.append(
            "- **F841 (Unused Variables)**: Review these. If strictly for unpacking, prepend with `_`. Otherwise remove."
        )
    if "F541" in top_codes:
        md.append(
            "- **F541 (F-string missing placeholders)**: Trivial fix. Run auto-fix."
        )

    Path(output_file).write_text("\n".join(md), encoding="utf-8")
    print(f"Summary generated at {output_file}")


if __name__ == "__main__":
    summarize_ruff_errors("ruff_errors.txt", "ruff_summary.md")
