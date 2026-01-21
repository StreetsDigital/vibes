#!/usr/bin/env python3
"""
Codex Review - Send code to OpenAI for bug analysis
Returns a structured list of issues for Claude to fix
"""

import os
import sys
import json
import subprocess
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "-q"])
    from openai import OpenAI


def get_recent_changes():
    """Get recently changed files from git"""
    try:
        # Get staged + unstaged changes
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5"],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        files = [f for f in result.stdout.strip().split('\n') if f]
        return files[:10]  # Limit to 10 files
    except:
        return []


def read_files(file_paths):
    """Read content of specified files"""
    contents = {}
    for path in file_paths:
        try:
            full_path = Path(path)
            if full_path.exists() and full_path.stat().st_size < 50000:  # Skip large files
                contents[path] = full_path.read_text()
        except:
            pass
    return contents


def analyze_with_openai(files_content, api_key):
    """Send code to OpenAI for analysis"""
    client = OpenAI(api_key=api_key)

    # Build the prompt
    code_sections = []
    for path, content in files_content.items():
        code_sections.append(f"### {path}\n```\n{content[:8000]}\n```")

    code_text = "\n\n".join(code_sections)

    prompt = f"""Analyze the following code for bugs, security issues, and potential problems.

Return a JSON array of issues found. Each issue should have:
- "file": the file path
- "line": approximate line number (or "N/A")
- "severity": "critical", "high", "medium", or "low"
- "type": "bug", "security", "performance", "style", or "logic"
- "description": brief description of the issue
- "fix": suggested fix

Only return the JSON array, no other text.

{code_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a code review expert. Analyze code for bugs and issues. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=4000
    )

    return response.choices[0].message.content


def main():
    # Get API key from environment or argument
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        # Check for key file
        key_file = Path.home() / ".config" / "openai" / "api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()

    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY=your-key")
        sys.exit(1)

    # Get files to analyze
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = get_recent_changes()

    if not files:
        print("No files to analyze. Specify files or make some git changes.")
        sys.exit(0)

    print(f"Analyzing {len(files)} files...")

    # Read file contents
    contents = read_files(files)

    if not contents:
        print("Could not read any files.")
        sys.exit(1)

    # Analyze with OpenAI
    try:
        result = analyze_with_openai(contents, api_key)

        # Try to parse as JSON
        try:
            # Clean up response (remove markdown code blocks if present)
            clean_result = result.strip()
            if clean_result.startswith("```"):
                clean_result = clean_result.split("\n", 1)[1]
            if clean_result.endswith("```"):
                clean_result = clean_result.rsplit("```", 1)[0]

            issues = json.loads(clean_result)

            if not issues:
                print("\n✅ No issues found!")
                return

            print(f"\n🔍 Found {len(issues)} issues:\n")

            for i, issue in enumerate(issues, 1):
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(issue.get("severity", "medium"), "⚪")

                print(f"{i}. {severity_icon} [{issue.get('severity', 'unknown').upper()}] {issue.get('file', 'unknown')}:{issue.get('line', 'N/A')}")
                print(f"   Type: {issue.get('type', 'unknown')}")
                print(f"   Issue: {issue.get('description', 'No description')}")
                print(f"   Fix: {issue.get('fix', 'No suggestion')}")
                print()

            # Output as JSON for programmatic use
            print("\n--- JSON OUTPUT ---")
            print(json.dumps(issues, indent=2))

        except json.JSONDecodeError:
            print("Raw response from OpenAI:")
            print(result)

    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
