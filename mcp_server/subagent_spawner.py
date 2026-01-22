"""
Subagent Spawner for Vibecoding Stack
======================================

Borrowed from GSD's insight: each feature should run in a fresh subagent
with 200k tokens purely for implementation, zero accumulated garbage.

This module handles:
1. Spawning fresh Claude Code subagents per feature
2. Passing minimal context (just what's needed)
3. Collecting results back to the orchestrator

The key insight: as context accumulates, Claude's quality degrades.
Fresh subagent = fresh context = consistent quality.
"""

import os
import json
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class SubagentConfig:
    """Configuration for subagent spawning."""
    
    # Maximum context to pass to subagent (chars)
    max_context_chars: int = 50_000
    
    # Timeout for subagent execution (seconds)
    timeout_seconds: int = 1800  # 30 minutes
    
    # Whether to use Claude CLI or SDK
    use_cli: bool = True
    
    # Model to use for subagent
    model: str = "claude-sonnet-4-20250514"
    
    # Whether to stream output
    stream_output: bool = True


# =============================================================================
# AGENT TYPE PROMPTS
# =============================================================================

AGENT_TYPE_PROMPTS = {
    # Coding agents
    "feature_agent": """You are a FEATURE IMPLEMENTATION agent. Your job is to:
- Implement the feature according to specifications
- Write clean, production-quality code
- Follow existing code patterns in the codebase
- Create necessary files and update existing ones
When done, output: FEATURE_COMPLETE""",

    "refactor_agent": """You are a REFACTORING agent. Your job is to:
- Improve code architecture without changing behavior
- Apply DRY principles and reduce duplication
- Improve naming and code organization
- Ensure all tests still pass after refactoring
When done, output: FEATURE_COMPLETE""",

    # E2E Testing agents
    "e2e_test_agent": """You are an E2E TESTING agent. Your job is to:
- Write end-to-end tests using Playwright or Cypress
- Test complete user flows from start to finish
- Include setup/teardown for test data
- Test happy paths and error cases
- Output test files in tests/e2e/ or similar
When done, output: FEATURE_COMPLETE""",

    "integration_test_agent": """You are an INTEGRATION TEST agent. Your job is to:
- Write integration tests for API endpoints
- Test service interactions and data flow
- Mock external dependencies appropriately
- Test authentication and authorization flows
- Output test files in tests/integration/
When done, output: FEATURE_COMPLETE""",

    "unit_test_agent": """You are a UNIT TEST agent. Your job is to:
- Write unit tests for individual functions/methods
- Achieve high code coverage for new code
- Test edge cases and error conditions
- Use appropriate mocking for dependencies
- Follow testing conventions in the codebase
When done, output: FEATURE_COMPLETE""",

    "test_runner_agent": """You are a TEST RUNNER agent. Your job is to:
- Run all test suites (unit, integration, e2e)
- Report failures clearly with stack traces
- Suggest fixes for failing tests
- Verify test coverage meets requirements
- Run linting and type checking if available
When done, output: FEATURE_COMPLETE""",

    # Infrastructure agents
    "docker_agent": """You are a DOCKER/CONTAINER agent. Your job is to:
- Create or update Dockerfiles
- Optimize image size and build time
- Set up docker-compose for local development
- Configure multi-stage builds for production
- Add health checks and proper signal handling
When done, output: FEATURE_COMPLETE""",

    "ci_cd_agent": """You are a CI/CD PIPELINE agent. Your job is to:
- Set up GitHub Actions / GitLab CI / Jenkins pipelines
- Configure build, test, and deploy stages
- Add caching for faster builds
- Set up environment-specific deployments
- Add status badges and notifications
When done, output: FEATURE_COMPLETE""",

    "deployment_agent": """You are a DEPLOYMENT agent. Your job is to:
- Create deployment scripts and configurations
- Write Kubernetes manifests or Terraform configs
- Set up staging and production environments
- Configure secrets management
- Add rollback procedures
When done, output: FEATURE_COMPLETE""",

    "monitoring_agent": """You are a MONITORING/OBSERVABILITY agent. Your job is to:
- Set up structured logging (JSON format)
- Add metrics collection (Prometheus/StatsD)
- Configure alerting rules
- Add distributed tracing if applicable
- Create dashboards for key metrics
When done, output: FEATURE_COMPLETE""",

    "security_agent": """You are a SECURITY AUDIT agent. Your job is to:
- Audit code for common vulnerabilities (OWASP Top 10)
- Check for hardcoded secrets and credentials
- Add security headers and CORS configuration
- Review authentication/authorization logic
- Suggest security improvements
When done, output: FEATURE_COMPLETE""",

    # QA agents
    "code_review_agent": """You are a CODE REVIEW agent. Your job is to:
- Review code changes for quality and correctness
- Check for bugs, edge cases, and error handling
- Verify code follows project conventions
- Suggest improvements and optimizations
- Ensure proper documentation exists
When done, output: FEATURE_COMPLETE""",

    "documentation_agent": """You are a DOCUMENTATION agent. Your job is to:
- Write or update README files
- Create API documentation
- Add inline code comments where helpful
- Document configuration options
- Create usage examples
When done, output: FEATURE_COMPLETE""",
}

DEFAULT_AGENT_TYPE = "feature_agent"


# =============================================================================
# CONTEXT BUILDER
# =============================================================================

class FeatureContextBuilder:
    """
    Builds minimal, focused context for a feature subagent.
    
    The key is giving the subagent ONLY what it needs:
    - Feature spec and test cases
    - Relevant code snippets (from Aleph search)
    - Key decisions from planning files
    - Nothing else
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        
    def build_context(
        self,
        feature: Dict[str, Any],
        relevant_code: List[Dict[str, Any]] = None,
        decisions: List[str] = None
    ) -> str:
        """
        Build focused context for a feature.
        
        Args:
            feature: Feature dict with name, description, test_cases
            relevant_code: Code snippets from Aleph search
            decisions: Key decisions from task_plan.md
            
        Returns:
            Formatted context string
        """
        parts = []
        
        # Header
        parts.append("=" * 60)
        parts.append("FEATURE IMPLEMENTATION CONTEXT")
        parts.append("=" * 60)
        parts.append("")
        
        # Feature spec
        parts.append("## YOUR TASK")
        parts.append("")
        parts.append(f"**Feature:** {feature.get('name', 'Unknown')}")
        parts.append("")
        if feature.get('description'):
            parts.append(f"**Description:** {feature['description']}")
            parts.append("")
        
        # Test cases
        test_cases = feature.get('test_cases', [])
        if test_cases:
            parts.append("**Success Criteria (Tests to Pass):**")
            for i, tc in enumerate(test_cases, 1):
                if isinstance(tc, dict):
                    parts.append(f"  {i}. {tc.get('name', tc)}")
                    if tc.get('steps'):
                        parts.append(f"     Steps: {tc['steps']}")
                    if tc.get('expected'):
                        parts.append(f"     Expected: {tc['expected']}")
                else:
                    parts.append(f"  {i}. {tc}")
            parts.append("")
        
        # Key decisions
        if decisions:
            parts.append("## KEY DECISIONS (from task_plan.md)")
            parts.append("")
            for d in decisions[:10]:  # Limit to 10 most relevant
                parts.append(f"- {d}")
            parts.append("")
        
        # Relevant code
        if relevant_code:
            parts.append("## RELEVANT EXISTING CODE")
            parts.append("")
            for snippet in relevant_code[:5]:  # Limit to 5 snippets
                parts.append(f"### {snippet.get('file', 'Unknown file')}")
                parts.append(f"Lines {snippet.get('start', '?')}-{snippet.get('end', '?')}")
                parts.append("```")
                parts.append(snippet.get('content', ''))
                parts.append("```")
                parts.append("")
        
        # Instructions
        parts.append("## INSTRUCTIONS")
        parts.append("")
        parts.append("1. Implement the feature to pass all test cases")
        parts.append("2. Follow existing code patterns and conventions")
        parts.append("3. Write clean, maintainable code")
        parts.append("4. Run tests to verify your implementation")
        parts.append("5. Commit your changes with a descriptive message")
        parts.append("")
        parts.append("When complete, output: FEATURE_COMPLETE")
        parts.append("If blocked, output: FEATURE_BLOCKED: <reason>")
        parts.append("")
        
        return "\n".join(parts)
    
    def extract_decisions(self) -> List[str]:
        """Extract key decisions from task_plan.md."""
        task_plan = self.project_dir / "task_plan.md"
        
        if not task_plan.exists():
            return []
        
        content = task_plan.read_text()
        decisions = []
        
        # Look for decisions table or section
        in_decisions = False
        for line in content.splitlines():
            if "Decision" in line and "|" in line:
                in_decisions = True
                continue
            if in_decisions:
                if line.startswith("|") and "---" not in line:
                    # Parse table row
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if parts and parts[0]:
                        decisions.append(parts[0])
                elif not line.startswith("|"):
                    in_decisions = False
        
        return decisions


# =============================================================================
# SUBAGENT SPAWNER
# =============================================================================

class SubagentSpawner:
    """
    Spawns fresh Claude subagents for feature implementation.
    
    Each feature gets its own subagent with:
    - Fresh 200k token context
    - Only the context it needs
    - Isolated execution
    """
    
    def __init__(
        self, 
        project_dir: Path, 
        config: Optional[SubagentConfig] = None
    ):
        self.project_dir = Path(project_dir)
        self.config = config or SubagentConfig()
        self.context_builder = FeatureContextBuilder(project_dir)
        self._active_process: Optional[subprocess.Popen] = None
        
    def spawn_for_feature(
        self,
        feature: Dict[str, Any],
        relevant_code: List[Dict[str, Any]] = None,
        on_output: callable = None,
        agent_type: str = None
    ) -> Dict[str, Any]:
        """
        Spawn a fresh subagent to implement a feature.

        Args:
            feature: Feature dict with name, description, test_cases
            relevant_code: Code snippets from Aleph search
            on_output: Callback for streaming output
            agent_type: Type of agent (e2e_test_agent, docker_agent, etc.)

        Returns:
            Result dict with status, output, duration
        """
        start_time = time.time()

        # Get agent type prompt
        agent_type = agent_type or DEFAULT_AGENT_TYPE
        agent_prompt = AGENT_TYPE_PROMPTS.get(agent_type, AGENT_TYPE_PROMPTS[DEFAULT_AGENT_TYPE])

        # Build focused context
        decisions = self.context_builder.extract_decisions()
        context = self.context_builder.build_context(
            feature=feature,
            relevant_code=relevant_code,
            decisions=decisions
        )

        # Prepend agent type prompt to context
        context = f"## AGENT ROLE\n{agent_prompt}\n\n{context}"

        # Check context size
        if len(context) > self.config.max_context_chars:
            # Truncate relevant code first
            context = self.context_builder.build_context(
                feature=feature,
                relevant_code=relevant_code[:2] if relevant_code else None,
                decisions=decisions[:5]
            )
            context = f"## AGENT ROLE\n{agent_prompt}\n\n{context}"

        # Spawn subagent
        if self.config.use_cli:
            result = self._spawn_cli_subagent(context, on_output)
        else:
            result = self._spawn_sdk_subagent(context, on_output)
        
        result['duration_seconds'] = time.time() - start_time
        result['feature_id'] = feature.get('id')
        result['feature_name'] = feature.get('name')
        
        return result
    
    def _spawn_cli_subagent(
        self, 
        context: str, 
        on_output: callable = None
    ) -> Dict[str, Any]:
        """Spawn subagent using Claude CLI."""
        
        # Write context to temp file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.md', 
            delete=False
        ) as f:
            f.write(context)
            context_file = f.name
        
        try:
            # Build command
            cmd = [
                "claude",
                "--print",  # Non-interactive mode
                "--dangerously-skip-permissions",  # Auto-approve tool use
                "-p", f"Read the context file at {context_file} and implement the feature as specified."
            ]
            
            # Add working directory
            env = os.environ.copy()
            
            # Spawn process
            process = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            self._active_process = process
            
            # Collect output
            output_lines = []
            status = "running"
            
            try:
                # Stream output if callback provided
                if on_output and self.config.stream_output:
                    for line in iter(process.stdout.readline, ''):
                        output_lines.append(line)
                        on_output(line)
                        
                        # Check for completion markers
                        if "FEATURE_COMPLETE" in line:
                            status = "complete"
                        elif "FEATURE_BLOCKED" in line:
                            status = "blocked"
                    
                    process.wait(timeout=self.config.timeout_seconds)
                else:
                    stdout, stderr = process.communicate(
                        timeout=self.config.timeout_seconds
                    )
                    output_lines = stdout.splitlines()
                    
                    if "FEATURE_COMPLETE" in stdout:
                        status = "complete"
                    elif "FEATURE_BLOCKED" in stdout:
                        status = "blocked"
                    elif process.returncode != 0:
                        status = "error"
                        output_lines.extend(stderr.splitlines())
                    else:
                        status = "complete"  # Assume complete if no error
                        
            except subprocess.TimeoutExpired:
                process.kill()
                status = "timeout"
                
            return {
                "status": status,
                "output": "\n".join(output_lines),
                "return_code": process.returncode
            }
            
        finally:
            # Cleanup temp file
            os.unlink(context_file)
            self._active_process = None
    
    def _spawn_sdk_subagent(
        self, 
        context: str, 
        on_output: callable = None
    ) -> Dict[str, Any]:
        """Spawn subagent using Claude SDK (for programmatic control)."""
        
        try:
            from claude_agent_sdk import ClaudeSDKClient
            
            # Create client with fresh context
            client = ClaudeSDKClient(
                model=self.config.model,
                max_tokens=4096
            )
            
            # Run with context
            response = client.run(
                message=context,
                working_directory=str(self.project_dir)
            )
            
            output = response.get('output', '')
            
            if "FEATURE_COMPLETE" in output:
                status = "complete"
            elif "FEATURE_BLOCKED" in output:
                status = "blocked"
            else:
                status = "complete"
            
            return {
                "status": status,
                "output": output,
                "return_code": 0
            }
            
        except ImportError:
            return {
                "status": "error",
                "output": "Claude SDK not installed",
                "return_code": 1
            }
        except Exception as e:
            return {
                "status": "error",
                "output": str(e),
                "return_code": 1
            }
    
    def cancel(self) -> bool:
        """Cancel the active subagent if running."""
        if self._active_process:
            self._active_process.terminate()
            self._active_process = None
            return True
        return False


# =============================================================================
# PRE-PLANNING PHASE (borrowed from GSD)
# =============================================================================

class PrePlanningPhase:
    """
    Pre-planning phase before feature implementation.
    
    Borrowed from GSD's insight: think before doing.
    
    Commands:
    - discuss_feature: Gather context, clarify requirements
    - research_feature: Deep dive into ecosystem/patterns
    - list_assumptions: Surface what Claude assumes
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self._discussions: Dict[int, List[Dict]] = {}
        self._assumptions: Dict[int, List[str]] = {}
        self._research: Dict[int, Dict] = {}
        
    def discuss_feature(
        self, 
        feature: Dict[str, Any],
        questions: List[str] = None
    ) -> Dict[str, Any]:
        """
        Start a discussion about a feature before implementing.
        
        This surfaces:
        - Unclear requirements
        - Edge cases
        - Dependencies
        - Potential blockers
        
        Args:
            feature: Feature dict
            questions: Specific questions to explore
            
        Returns:
            Discussion summary with questions and considerations
        """
        feature_id = feature.get('id', 0)
        
        # Generate discussion points
        discussion = {
            "feature": feature.get('name'),
            "timestamp": datetime.now().isoformat(),
            "questions": [],
            "considerations": [],
            "dependencies": [],
            "edge_cases": []
        }
        
        # Analyze feature for discussion points
        name = feature.get('name', '').lower()
        desc = feature.get('description', '').lower()
        
        # Common patterns that need clarification
        if any(word in name + desc for word in ['auth', 'login', 'user']):
            discussion['questions'].extend([
                "What authentication method? (JWT, session, OAuth)",
                "Password requirements?",
                "Session timeout behavior?"
            ])
            discussion['considerations'].append(
                "Security: rate limiting, password hashing, token expiry"
            )
        
        if any(word in name + desc for word in ['api', 'endpoint', 'route']):
            discussion['questions'].extend([
                "Request/response format?",
                "Error response structure?",
                "Rate limiting requirements?"
            ])
            
        if any(word in name + desc for word in ['database', 'store', 'save', 'persist']):
            discussion['questions'].extend([
                "Data model/schema?",
                "Validation rules?",
                "Cascade delete behavior?"
            ])
            discussion['dependencies'].append("Database schema must exist")
            
        if any(word in name + desc for word in ['ui', 'component', 'page', 'form']):
            discussion['questions'].extend([
                "Responsive design requirements?",
                "Accessibility requirements?",
                "Loading/error states?"
            ])
            discussion['edge_cases'].extend([
                "Empty state",
                "Error state", 
                "Loading state"
            ])
        
        # Add custom questions
        if questions:
            discussion['questions'].extend(questions)
        
        # Store for later reference
        if feature_id not in self._discussions:
            self._discussions[feature_id] = []
        self._discussions[feature_id].append(discussion)
        
        return discussion
    
    def list_assumptions(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surface what Claude would assume about this feature.
        
        This helps catch misalignments BEFORE implementation.
        
        Args:
            feature: Feature dict
            
        Returns:
            List of assumptions that should be validated
        """
        feature_id = feature.get('id', 0)
        
        assumptions = []
        name = feature.get('name', '').lower()
        desc = feature.get('description', '').lower()
        test_cases = feature.get('test_cases', [])
        
        # Tech stack assumptions
        assumptions.append({
            "category": "Tech Stack",
            "assumptions": [
                "Using the existing framework/language in the project",
                "Following existing code style and patterns",
                "Using existing dependencies where possible"
            ]
        })
        
        # Architecture assumptions
        assumptions.append({
            "category": "Architecture",
            "assumptions": [
                "New code goes in standard locations (src/, lib/, etc.)",
                "Following existing module/component patterns",
                "Using existing utility functions"
            ]
        })
        
        # Feature-specific assumptions
        feature_assumptions = []
        
        if 'auth' in name + desc:
            feature_assumptions.extend([
                "JWT-based authentication (unless specified otherwise)",
                "Passwords hashed with bcrypt",
                "HttpOnly cookies for token storage"
            ])
        
        if 'api' in name + desc:
            feature_assumptions.extend([
                "RESTful conventions (unless GraphQL exists)",
                "JSON request/response bodies",
                "Standard HTTP status codes"
            ])
            
        if 'test' in name + desc or test_cases:
            feature_assumptions.extend([
                "Using existing test framework",
                "Unit tests alongside implementation",
                "Mocking external dependencies"
            ])
            
        if feature_assumptions:
            assumptions.append({
                "category": "Feature-Specific",
                "assumptions": feature_assumptions
            })
        
        # Store
        self._assumptions[feature_id] = assumptions
        
        return {
            "feature": feature.get('name'),
            "assumptions": assumptions,
            "action_required": "Review and correct any wrong assumptions before /execute"
        }
    
    def research_feature(
        self, 
        feature: Dict[str, Any],
        topics: List[str] = None
    ) -> Dict[str, Any]:
        """
        Deep research phase for complex/unfamiliar features.
        
        Now integrated with Context7 MCP for up-to-date library docs.
        
        Args:
            feature: Feature dict
            topics: Specific topics to research
            
        Returns:
            Research findings with libraries to fetch docs for
        """
        feature_id = feature.get('id', 0)
        
        research = {
            "feature": feature.get('name'),
            "timestamp": datetime.now().isoformat(),
            "topics_to_research": [],
            "libraries_to_fetch": [],  # For Context7
            "recommended_approach": None,
            "resources": []
        }
        
        name = feature.get('name', '').lower()
        desc = feature.get('description', '').lower()
        
        # Identify research topics AND libraries for Context7
        if any(word in name + desc for word in ['oauth', 'sso', 'saml']):
            research['topics_to_research'].append("OAuth 2.0 / OIDC flow specifics")
            research['libraries_to_fetch'].extend([
                {"name": "next-auth", "topic": "oauth providers"},
                {"name": "passport", "topic": "oauth strategy"}
            ])
            
        if any(word in name + desc for word in ['stripe', 'payment', 'checkout']):
            research['topics_to_research'].append("Payment provider SDK integration")
            research['libraries_to_fetch'].append(
                {"name": "stripe", "topic": "checkout sessions"}
            )
            
        if any(word in name + desc for word in ['websocket', 'realtime', 'live']):
            research['topics_to_research'].append("WebSocket implementation patterns")
            research['libraries_to_fetch'].extend([
                {"name": "socket.io", "topic": "server setup"},
                {"name": "ws", "topic": "websocket server"}
            ])
            
        if any(word in name + desc for word in ['s3', 'upload', 'storage', 'file']):
            research['topics_to_research'].append("File upload best practices")
            research['libraries_to_fetch'].append(
                {"name": "aws-sdk", "topic": "s3 upload"}
            )
            
        if any(word in name + desc for word in ['next', 'nextjs', 'next.js']):
            research['libraries_to_fetch'].append(
                {"name": "next.js", "topic": None}  # General docs
            )
            
        if any(word in name + desc for word in ['react', 'component', 'hook']):
            research['libraries_to_fetch'].append(
                {"name": "react", "topic": "hooks"}
            )
            
        if any(word in name + desc for word in ['prisma', 'database', 'orm']):
            research['libraries_to_fetch'].append(
                {"name": "prisma", "topic": "crud operations"}
            )
            
        if any(word in name + desc for word in ['tailwind', 'css', 'styling']):
            research['libraries_to_fetch'].append(
                {"name": "tailwindcss", "topic": None}
            )
            
        if any(word in name + desc for word in ['zod', 'validation', 'schema']):
            research['libraries_to_fetch'].append(
                {"name": "zod", "topic": "schema validation"}
            )
        
        # Add custom topics
        if topics:
            research['topics_to_research'].extend(topics)
        
        # Add Context7 usage instructions
        if research['libraries_to_fetch']:
            research['context7_instructions'] = (
                "Use Context7 MCP tools to fetch docs:\n"
                "1. resolve-library-id(name) → Get library ID\n"
                "2. get-library-docs(id, topic) → Fetch current docs\n"
                "Libraries to fetch: " + 
                ", ".join(lib['name'] for lib in research['libraries_to_fetch'])
            )
        
        # Store
        self._research[feature_id] = research
        
        return research
    
    def get_pre_planning_summary(self, feature_id: int) -> Dict[str, Any]:
        """Get all pre-planning info for a feature."""
        return {
            "discussions": self._discussions.get(feature_id, []),
            "assumptions": self._assumptions.get(feature_id, []),
            "research": self._research.get(feature_id, {})
        }


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

# Global instances
_spawner: Optional[SubagentSpawner] = None
_pre_planner: Optional[PrePlanningPhase] = None


def init_subagent_system(project_dir: str) -> Dict[str, Any]:
    """Initialize the subagent system."""
    global _spawner, _pre_planner
    
    path = Path(project_dir)
    _spawner = SubagentSpawner(path)
    _pre_planner = PrePlanningPhase(path)
    
    return {
        "success": True,
        "project_dir": project_dir,
        "subagent_ready": True,
        "pre_planner_ready": True
    }


def spawn_feature_subagent(
    feature: Dict[str, Any],
    relevant_code: List[Dict[str, Any]] = None,
    agent_type: str = None
) -> Dict[str, Any]:
    """
    Spawn a fresh subagent to implement a feature.

    This gives the feature a fresh 200k context window,
    preventing quality degradation from accumulated context.

    Args:
        feature: Feature dict
        relevant_code: Code snippets from Aleph search
        agent_type: Type of agent (e2e_test_agent, docker_agent, etc.)
    """
    if _spawner is None:
        return {"error": "Subagent system not initialized"}

    return _spawner.spawn_for_feature(feature, relevant_code, agent_type=agent_type)


def discuss_feature(
    feature: Dict[str, Any],
    questions: List[str] = None
) -> Dict[str, Any]:
    """
    Start a pre-planning discussion about a feature.
    
    Use this BEFORE implementation to:
    - Surface unclear requirements
    - Identify edge cases
    - Find dependencies
    """
    if _pre_planner is None:
        return {"error": "Pre-planner not initialized"}
    
    return _pre_planner.discuss_feature(feature, questions)


def list_feature_assumptions(feature: Dict[str, Any]) -> Dict[str, Any]:
    """
    List what Claude would assume about this feature.
    
    Review and correct assumptions BEFORE implementation
    to avoid wasted work.
    """
    if _pre_planner is None:
        return {"error": "Pre-planner not initialized"}
    
    return _pre_planner.list_assumptions(feature)


def research_feature(
    feature: Dict[str, Any],
    topics: List[str] = None
) -> Dict[str, Any]:
    """
    Deep research phase for complex features.
    
    Use for features involving:
    - Unfamiliar APIs/SDKs
    - Complex integrations
    - Niche domains
    """
    if _pre_planner is None:
        return {"error": "Pre-planner not initialized"}
    
    return _pre_planner.research_feature(feature, topics)


def get_subagent_tools() -> List[Dict[str, Any]]:
    """Get tool definitions for MCP registration."""
    agent_types_desc = ", ".join(AGENT_TYPE_PROMPTS.keys())
    return [
        {
            "name": "subagent_spawn",
            "description": f"Spawn a specialized subagent with 200k context. Agent types: {agent_types_desc}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "object",
                        "description": "Feature dict with id, name, description, test_cases"
                    },
                    "relevant_code": {
                        "type": "array",
                        "description": "Code snippets from Aleph search"
                    },
                    "agent_type": {
                        "type": "string",
                        "description": "Type of agent to spawn",
                        "enum": list(AGENT_TYPE_PROMPTS.keys())
                    }
                },
                "required": ["feature"]
            }
        },
        {
            "name": "feature_discuss",
            "description": "Pre-planning discussion. Surface unclear requirements, edge cases, dependencies BEFORE implementing.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "object",
                        "description": "Feature dict"
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific questions to explore"
                    }
                },
                "required": ["feature"]
            }
        },
        {
            "name": "feature_assumptions",
            "description": "List what Claude assumes about this feature. Review and correct BEFORE implementation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "object",
                        "description": "Feature dict"
                    }
                },
                "required": ["feature"]
            }
        },
        {
            "name": "feature_research",
            "description": "Deep research for complex features. Use for unfamiliar APIs, integrations, niche domains.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature": {
                        "type": "object",
                        "description": "Feature dict"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific topics to research"
                    }
                },
                "required": ["feature"]
            }
        }
    ]


def handle_subagent_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a subagent/pre-planning tool call."""
    handlers = {
        "subagent_spawn": lambda args: spawn_feature_subagent(
            args["feature"],
            args.get("relevant_code"),
            args.get("agent_type")
        ),
        "feature_discuss": lambda args: discuss_feature(
            args["feature"],
            args.get("questions")
        ),
        "feature_assumptions": lambda args: list_feature_assumptions(
            args["feature"]
        ),
        "feature_research": lambda args: research_feature(
            args["feature"],
            args.get("topics")
        )
    }
    
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    
    try:
        return handler(arguments)
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Test pre-planning
    test_feature = {
        "id": 1,
        "name": "User Authentication",
        "description": "Implement JWT-based user authentication with login/logout",
        "test_cases": [
            "Valid credentials return token",
            "Invalid credentials return 401",
            "Expired token rejected"
        ]
    }
    
    init_subagent_system(".")
    
    print("=== DISCUSS ===")
    print(json.dumps(discuss_feature(test_feature), indent=2))
    
    print("\n=== ASSUMPTIONS ===")
    print(json.dumps(list_feature_assumptions(test_feature), indent=2))
    
    print("\n=== RESEARCH ===")
    print(json.dumps(research_feature(test_feature), indent=2))
