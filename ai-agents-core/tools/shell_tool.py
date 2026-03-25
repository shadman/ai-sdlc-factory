"""CrewAI-compatible shell execution tool."""
import subprocess
from crewai.tools import BaseTool


class ShellExecutionTool(BaseTool):
    name: str = "ShellExecutionTool"
    description: str = (
        "Execute shell commands. Use for running terminal commands like cd, bandit, npm audit, git, etc. "
        "Always cd to the working_dir first if provided. Input: the full command string to run."
    )

    def _run(self, command: str) -> str:
        """Execute a shell command and return stdout/stderr."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",  # force bash — /bin/sh (dash) lacks source, [[, etc.
                capture_output=True,
                text=True,
                timeout=120,
            )
            out = result.stdout or ""
            err = result.stderr or ""
            if result.returncode != 0:
                return f"Exit code {result.returncode}\nstdout:\n{out}\nstderr:\n{err}"
            return out or "(no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out after 120 seconds."
        except Exception as e:
            return f"Error running command: {e}"
