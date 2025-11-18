#!/usr/bin/env python3
"""
Advanced script to remove unused imports safely using autoflake
"""

import subprocess
import sys
from pathlib import Path


def main():
    blastdock_dir = Path(__file__).parent / "blastdock"

    print("🔧 Installing autoflake...")
    subprocess.run([sys.executable, "-m", "pip", "install", "autoflake", "--quiet"], check=False)

    print("🧹 Removing unused imports with autoflake...")

    # Run autoflake to remove unused imports
    cmd = [
        sys.executable, "-m", "autoflake",
        "--in-place",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
        "--remove-duplicate-keys",
        "--recursive",
        str(blastdock_dir)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("Warnings:", result.stderr)

    print("\n✅ Cleanup complete!")

    # Run flake8 to check results
    print("\n📊 Running flake8 to verify...")
    flake8_cmd = [
        "flake8", "blastdock/",
        "--max-line-length=127",
        "--extend-ignore=E203,W503,E501",
        "--count",
        "--statistics"
    ]

    flake8_result = subprocess.run(flake8_cmd, capture_output=True, text=True)
    lines = flake8_result.stdout.split('\n')[-10:]
    print('\n'.join(lines))


if __name__ == "__main__":
    main()
