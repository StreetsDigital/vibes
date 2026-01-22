"""
Task Decomposer
================

Breaks down large tasks into small, atomic subtasks that can be
completed in a single focused session.

Inspired by autocoder's brilliant task decomposition approach:
- Each subtask should be specific and actionable
- Clear acceptance criteria
- Proper ordering/dependencies
- Small enough to verify quickly
"""

import json
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Subtask:
    """A decomposed subtask."""
    name: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    test_cases: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # IDs of tasks this depends on
    order: int = 0
    estimated_complexity: str = "small"  # small, medium, large

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DECOMPOSITION_PROMPT = '''You are a senior software architect who excels at breaking down complex tasks into small, atomic subtasks.

## YOUR TASK
Decompose the following task into small, specific subtasks that can each be completed in a single focused coding session (15-30 minutes).

## TASK TO DECOMPOSE
Title: {task_name}
Description: {task_description}
Context: {context}

## RULES FOR DECOMPOSITION
1. Each subtask should be ATOMIC - one clear thing to do
2. Each subtask should be TESTABLE - clear acceptance criteria
3. Each subtask should be SMALL - completable in 15-30 mins
4. Order subtasks logically - dependencies first
5. Include setup/scaffolding tasks before implementation
6. Include test tasks after implementation
7. Be SPECIFIC - "Add user login" is too vague, "Create POST /auth/login endpoint that validates credentials and returns JWT" is good

## GOOD SUBTASK EXAMPLES
- "Create User model with email, password_hash, created_at fields"
- "Add password hashing utility using bcrypt"
- "Create POST /auth/register endpoint with email/password validation"
- "Write unit tests for User model validation"
- "Add rate limiting middleware to auth endpoints"

## BAD SUBTASK EXAMPLES (too vague)
- "Implement authentication" (too big)
- "Add tests" (not specific)
- "Fix bugs" (not actionable)
- "Improve code" (no clear outcome)

## OUTPUT FORMAT
Return a JSON array of subtasks. Each subtask must have:
- name: Short, specific title (start with verb)
- description: 1-2 sentences explaining what to do
- acceptance_criteria: List of specific, testable criteria
- test_cases: List of test scenarios (can be empty for non-code tasks)
- dependencies: List of subtask names this depends on (empty if none)
- order: Integer for sequencing (1, 2, 3...)
- estimated_complexity: "small" (15min), "medium" (30min), or "large" (45min+, should be rare)

Return ONLY the JSON array, no other text.

## DECOMPOSE NOW
'''


def decompose_task(
    task_name: str,
    task_description: str,
    context: str = "",
    project_dir: str = None,
    max_subtasks: int = 15
) -> List[Subtask]:
    """
    Decompose a large task into atomic subtasks using Claude.

    Args:
        task_name: Name of the task to decompose
        task_description: Full description of what needs to be done
        context: Optional context about the codebase/project
        project_dir: Project directory for running Claude
        max_subtasks: Maximum number of subtasks to generate

    Returns:
        List of Subtask objects
    """
    prompt = DECOMPOSITION_PROMPT.format(
        task_name=task_name,
        task_description=task_description,
        context=context or "No additional context provided."
    )

    # Run Claude to get decomposition
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        os.chmod(prompt_file, 0o644)

        cwd = project_dir or os.getcwd()
        mcp_config = "/home/vibes/.claude/settings.json"

        cmd = f'runuser -u vibes -- bash -c \'cd "{cwd}" && claude --print --dangerously-skip-permissions --mcp-config {mcp_config} -p "$(cat {prompt_file})"\''

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            cwd=cwd,
            env={**os.environ, "HOME": "/home/vibes"},
            timeout=120
        )

        os.unlink(prompt_file)

        if result.returncode != 0:
            print(f"[decomposer] Claude error: {result.stderr}")
            return []

        # Parse JSON from output
        output = result.stdout.strip()

        # Find JSON array in output (Claude might add extra text)
        start_idx = output.find('[')
        end_idx = output.rfind(']') + 1

        if start_idx == -1 or end_idx == 0:
            print(f"[decomposer] No JSON array found in output")
            return []

        json_str = output[start_idx:end_idx]
        subtasks_data = json.loads(json_str)

        # Convert to Subtask objects
        subtasks = []
        for i, data in enumerate(subtasks_data[:max_subtasks]):
            subtask = Subtask(
                name=data.get('name', f'Subtask {i+1}'),
                description=data.get('description', ''),
                acceptance_criteria=data.get('acceptance_criteria', []),
                test_cases=data.get('test_cases', []),
                dependencies=data.get('dependencies', []),
                order=data.get('order', i + 1),
                estimated_complexity=data.get('estimated_complexity', 'small')
            )
            subtasks.append(subtask)

        # Sort by order
        subtasks.sort(key=lambda x: x.order)

        return subtasks

    except subprocess.TimeoutExpired:
        print("[decomposer] Claude timed out")
        return []
    except json.JSONDecodeError as e:
        print(f"[decomposer] JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"[decomposer] Error: {e}")
        return []


def quick_decompose(task_description: str) -> List[Dict[str, str]]:
    """
    Quick heuristic-based decomposition without Claude.

    Useful as a fallback or for simple tasks.
    """
    subtasks = []

    # Common patterns to look for
    keywords = {
        'api': ['Define API schema/types', 'Create endpoint handler', 'Add validation', 'Write API tests'],
        'database': ['Design schema', 'Create migration', 'Add model', 'Write model tests'],
        'ui': ['Create component structure', 'Add styling', 'Implement logic', 'Add component tests'],
        'auth': ['Add auth middleware', 'Create login endpoint', 'Create register endpoint', 'Add token validation'],
        'test': ['Write unit tests', 'Write integration tests', 'Add test fixtures'],
        'refactor': ['Identify code to change', 'Extract common logic', 'Update usages', 'Verify no regressions'],
    }

    desc_lower = task_description.lower()

    # Find matching patterns
    matched = False
    for keyword, tasks in keywords.items():
        if keyword in desc_lower:
            for i, task in enumerate(tasks):
                subtasks.append({
                    'name': task,
                    'description': f'{task} for: {task_description[:50]}...',
                    'order': i + 1
                })
            matched = True
            break

    # Default decomposition if no patterns matched
    if not matched:
        subtasks = [
            {'name': 'Analyze requirements', 'description': 'Understand what needs to be built', 'order': 1},
            {'name': 'Design solution', 'description': 'Plan the implementation approach', 'order': 2},
            {'name': 'Implement core logic', 'description': 'Build the main functionality', 'order': 3},
            {'name': 'Add error handling', 'description': 'Handle edge cases and errors', 'order': 4},
            {'name': 'Write tests', 'description': 'Add tests for the new code', 'order': 5},
            {'name': 'Review and refine', 'description': 'Clean up and verify', 'order': 6},
        ]

    return subtasks


def estimate_task_size(description: str) -> str:
    """
    Estimate if a task needs decomposition based on description.

    Returns: 'atomic', 'decompose', or 'epic'
    """
    # Word count heuristic
    words = len(description.split())

    # Complexity indicators
    complexity_words = [
        'and', 'also', 'plus', 'with', 'including', 'as well as',
        'multiple', 'several', 'various', 'different', 'all',
        'system', 'module', 'feature', 'integration', 'migration'
    ]

    complexity_score = sum(1 for word in complexity_words if word in description.lower())

    if words < 15 and complexity_score < 2:
        return 'atomic'
    elif words < 50 and complexity_score < 4:
        return 'decompose'
    else:
        return 'epic'


def format_subtasks_as_markdown(subtasks: List[Subtask]) -> str:
    """Format subtasks as a markdown checklist."""
    lines = ["## Subtasks\n"]

    for task in subtasks:
        # Main task
        lines.append(f"### {task.order}. {task.name}")
        lines.append(f"{task.description}\n")

        # Acceptance criteria
        if task.acceptance_criteria:
            lines.append("**Acceptance Criteria:**")
            for criterion in task.acceptance_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

        # Test cases
        if task.test_cases:
            lines.append("**Test Cases:**")
            for test in task.test_cases:
                lines.append(f"- {test}")
            lines.append("")

        # Dependencies
        if task.dependencies:
            lines.append(f"**Depends on:** {', '.join(task.dependencies)}\n")

        lines.append(f"*Complexity: {task.estimated_complexity}*\n")
        lines.append("---\n")

    return "\n".join(lines)
