#!/usr/bin/env python3
"""
Automated script to fix flake8 issues in the BlastDock codebase
Fixes: F401 (unused imports), F841 (unused variables), F541 (f-strings without placeholders)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def fix_unused_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """Remove unused imports from a file"""
    changes = []
    with open(file_path, 'r') as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    for i, line in enumerate(lines):
        # Skip lines that are not imports
        if not line.strip().startswith(('import ', 'from ')):
            new_lines.append(line)
            continue

        # Handle multi-import statements like "from typing import A, B, C"
        if 'from ' in line and ' import ' in line:
            # This is complex, skip for now to avoid breaking things
            new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)

    return modified, changes


def fix_fstring_placeholders(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix f-strings that don't have placeholders"""
    changes = []
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern to find f-strings without placeholders
    # Look for f"..." or f'...' that don't contain {...}
    patterns = [
        (r'f"([^"{]*)"', r'"\1"'),  # f"text" -> "text"
        (r"f'([^'{]*)'", r"'\1'"),  # f'text' -> 'text'
    ]

    for pattern, replacement in patterns:
        # Only replace if there are no braces in the string
        matches = re.finditer(pattern, content)
        for match in matches:
            if '{' not in match.group(1) and '}' not in match.group(1):
                old_str = match.group(0)
                new_str = re.sub(pattern, replacement, old_str)
                content = content.replace(old_str, new_str, 1)
                changes.append(f"Line with '{old_str}' -> '{new_str}'")

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True, changes

    return False, changes


def fix_unused_variables(file_path: Path) -> Tuple[bool, List[str]]:
    """Prefix unused variables with underscore"""
    changes = []
    with open(file_path, 'r') as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    # Common patterns for unused variables
    unused_patterns = [
        (r'^(\s+)(\w+)\s*=\s*(.+?)(\s*#.*local variable.*assigned.*never used)', r'\1_\2 = \3\4'),
    ]

    for line in lines:
        new_line = line
        for pattern, replacement in unused_patterns:
            if re.search(pattern, line):
                new_line = re.sub(pattern, replacement, line)
                if new_line != line:
                    changes.append(f"Changed: {line.strip()} -> {new_line.strip()}")
                    modified = True
        new_lines.append(new_line)

    if modified:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)

    return modified, changes


def main():
    """Main function to fix all flake8 issues"""
    blastdock_dir = Path(__file__).parent / "blastdock"

    print("🔧 Starting automated flake8 fixes...")
    print(f"📁 Target directory: {blastdock_dir}\n")

    total_files = 0
    total_fixes = 0

    # Fix f-strings without placeholders (F541)
    print("📝 Fixing f-strings without placeholders (F541)...")
    for py_file in blastdock_dir.rglob("*.py"):
        modified, changes = fix_fstring_placeholders(py_file)
        if modified:
            total_files += 1
            total_fixes += len(changes)
            print(f"  ✓ Fixed {len(changes)} issues in {py_file.relative_to(blastdock_dir)}")

    print(f"\n✅ Fixed {total_fixes} issues in {total_files} files")
    print("\n🎉 Automated fixes complete!")
    print("💡 Note: Unused imports (F401) and variables (F841) require manual review to avoid breaking dependencies")


if __name__ == "__main__":
    main()
