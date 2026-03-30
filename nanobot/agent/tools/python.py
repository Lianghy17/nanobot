"""Python code execution tool with Jupyter notebook persistence."""

import asyncio
import base64
import json
import os
import re
import sys
import traceback
from io import StringIO
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


class PythonExecTool(Tool):
    """Tool to execute Python code and persist to Jupyter notebook."""

    def __init__(
        self,
        workspace: Path,
        timeout: int = 120,
        session_manager: Any = None,
    ):
        self.workspace = workspace
        self.timeout = timeout
        self.session_manager = session_manager
        self._session_outputs: dict[str, list[dict]] = {}
        self._plot_counters: dict[str, int] = {}
        # Current session context (set by agent loop)
        self._current_session: str | None = None

    def set_session(self, session_id: str) -> None:
        """Set current session context."""
        self._current_session = session_id

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return """Execute Python code with full access to data analysis libraries.
        Supports pandas, numpy, matplotlib, seaborn, plotly, etc.
        
        CHART OUTPUT:
        - When plt.show() is called, charts are saved as PNG files
        - This tool returns Markdown image syntax: ![Chart N](url)
        - You MUST include these image URLs in your final response for the user to see them
        
        Example:
            import matplotlib.pyplot as plt
            plt.plot([1,2,3], [4,5,6])
            plt.show()  # Returns: ![Chart 1](/plots/session/plot_000.png)"""

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute. Must call plt.show() to display charts."
                }
            },
            "required": ["code"]
        }

    async def execute(self, code: str, **kwargs: Any) -> str:
        """Execute Python code and return results with plot URLs."""
        # Get session from context or use default
        session_id = self._current_session or "api_default"
        safe_session_id = session_id.replace(":", "_")

        # Create directories
        plots_dir = self.workspace / "plots" / safe_session_id
        plots_dir.mkdir(parents=True, exist_ok=True)
        
        notebook_dir = self.workspace / "notebooks" / safe_session_id
        notebook_dir.mkdir(parents=True, exist_ok=True)

        notebook_path = notebook_dir / "analysis.ipynb"

        # Initialize plot counter for this session
        if safe_session_id not in self._plot_counters:
            # Count existing plots
            existing = len(list(plots_dir.glob("plot_*.png")))
            self._plot_counters[safe_session_id] = existing

        logger.info(f"Python exec: session={session_id}, plots_dir={plots_dir}")

        # Execute the code
        result = await self._execute_code(code, plots_dir, safe_session_id)

        # Save to notebook
        await self._save_to_notebook(code, result, notebook_path, plots_dir)

        return result

    async def _execute_code(self, code: str, plots_dir: Path, safe_session_id: str) -> str:
        """Execute Python code in isolated environment and return results with plot URLs."""
        import subprocess
        import tempfile

        # Get current plot counter
        plot_counter = self._plot_counters.get(safe_session_id, 0)

        # Create a Python script that captures output and plots
        script_content = self._generate_execution_script(code, plots_dir, plot_counter)

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_script = f.name

            # Execute in subprocess for isolation
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace),
                env={**os.environ, "MPLBACKEND": "Agg"}  # Use non-interactive backend
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: Code execution timed out after {self.timeout} seconds"

            finally:
                os.unlink(temp_script)

            # Parse the JSON output
            try:
                output = json.loads(stdout.decode('utf-8', errors='replace'))
            except json.JSONDecodeError:
                output = {
                    "success": False,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "plots": []
                }

            # Update plot counter
            new_plot_count = output.get("plot_count", 0)
            self._plot_counters[safe_session_id] = plot_counter + new_plot_count

            # Format the result
            result_parts = []

            if output.get("stdout"):
                result_parts.append(output["stdout"])

            if output.get("stderr"):
                result_parts.append(f"STDERR:\n{output['stderr']}")

            if output.get("error"):
                result_parts.append(f"Error:\n{output['error']}")

            # Include plot URLs (this is the key change!)
            plot_filenames = output.get("plots", [])
            if plot_filenames:
                result_parts.append(f"\n📊 Generated {len(plot_filenames)} chart(s):")
                for i, plot_filename in enumerate(plot_filenames, 1):
                    # Generate URL instead of file path
                    plot_url = f"/plots/{safe_session_id}/{plot_filename}"
                    result_parts.append(f"  ![Chart {i}]({plot_url})")
                    logger.info(f"Plot saved: {plots_dir / plot_filename} -> URL: {plot_url}")

            if not result_parts:
                return "(no output)"

            return "\n".join(result_parts)

        except Exception as e:
            logger.error(f"Python execution error: {e}")
            return f"Error executing code: {str(e)}\n{traceback.format_exc()}"

    def _generate_execution_script(self, code: str, plots_dir: Path, plot_counter: int) -> str:
        """Generate the execution script with output capture and plot saving."""
        return f'''
import sys
import json
import io
import os
from pathlib import Path

# Plot directory
plots_dir = Path(r"{plots_dir}")
plots_dir.mkdir(parents=True, exist_ok=True)

# Track plots (use counter from parent)
plot_counter = {plot_counter}
plot_filenames = []

# Patch matplotlib if available
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    original_show = plt.show
    
    def patched_show(*args, **kwargs):
        global plot_counter, plot_filenames
        # Save figure to file
        filename = f"plot_{{plot_counter:03d}}.png"
        plot_path = plots_dir / filename
        plt.savefig(str(plot_path), format='png', dpi=100, bbox_inches='tight')
        plot_filenames.append(filename)
        plot_counter += 1
        print(f"[PLOT_SAVED] {{filename}}")
        plt.close('all')
    
    plt.show = patched_show
    
except ImportError:
    pass

# Capture output
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()
original_stdout = sys.stdout
original_stderr = sys.stderr

sys.stdout = stdout_capture
sys.stderr = stderr_capture

error = None

try:
    # Execute the code
    exec_globals = {{"__name__": "__main__"}}
    exec(r"""
{code}
""", exec_globals)
    
    # Close any remaining figures
    try:
        import matplotlib.pyplot as plt
        if plt.get_fignums():
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                filename = f"plot_{{plot_counter:03d}}.png"
                plot_path = plots_dir / filename
                fig.savefig(str(plot_path), format='png', dpi=100, bbox_inches='tight')
                plot_filenames.append(filename)
                plot_counter += 1
                print(f"[PLOT_SAVED] {{filename}}")
            plt.close('all')
    except:
        pass

except Exception as e:
    error = str(e)
    import traceback
    error += "\\n" + traceback.format_exc()

finally:
    sys.stdout = original_stdout
    sys.stderr = original_stderr

# Build output
output = {{
    "success": error is None,
    "stdout": stdout_capture.getvalue(),
    "stderr": stderr_capture.getvalue(),
    "error": error,
    "plots": plot_filenames,
    "plot_count": len(plot_filenames)
}}

print(json.dumps(output, ensure_ascii=False))
'''

    async def _save_to_notebook(self, code: str, result: str, notebook_path: Path, plots_dir: Path):
        """Save code and results to Jupyter notebook."""
        try:
            # Load existing notebook or create new
            if notebook_path.exists():
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)
            else:
                notebook = {
                    "cells": [],
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Python 3",
                            "language": "python",
                            "name": "python3"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 4
                }

            # Add code cell
            code_cell = {
                "cell_type": "code",
                "execution_count": len([c for c in notebook["cells"] if c.get("cell_type") == "code"]) + 1,
                "metadata": {},
                "outputs": [],
                "source": code.split('\n')
            }

            # Add plot outputs (read from plots_dir)
            for plot_file in sorted(plots_dir.glob("plot_*.png")):
                if plot_file.exists():
                    with open(plot_file, 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    code_cell["outputs"].append({
                        "output_type": "display_data",
                        "data": {
                            "image/png": img_data,
                            "text/plain": [f"<plot: {plot_file.name}>"]
                        },
                        "metadata": {}
                    })

            # Add text output (clean result without plot URLs)
            if result.strip():
                # Remove plot URL lines from notebook output
                clean_result = re.sub(r'\n📊 Generated \d+ chart\(s\):.*', '', result, flags=re.DOTALL)
                if clean_result.strip():
                    code_cell["outputs"].append({
                        "output_type": "stream",
                        "name": "stdout",
                        "text": clean_result.split('\n')
                    })

            notebook["cells"].append(code_cell)

            # Add markdown cell for timestamp
            from datetime import datetime
            markdown_cell = {
                "cell_type": "markdown",
                "metadata": {},
                "source": [f"---\n*Executed at: {datetime.now().isoformat()}*"]
            }
            notebook["cells"].append(markdown_cell)

            # Save notebook
            with open(notebook_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, ensure_ascii=False, indent=2)

            logger.debug(f"Notebook saved: {notebook_path}")

        except Exception as e:
            logger.warning(f"Failed to save notebook: {e}")


class FileUploadTool(Tool):
    """Tool to handle file uploads for analysis."""

    def __init__(self, workspace: Path, allowed_extensions: list[str] | None = None):
        self.workspace = workspace
        self.allowed_extensions = allowed_extensions or [
            '.csv', '.xlsx', '.xls', '.json', '.txt', '.md',
            '.py', '.ipynb', '.pdf', '.png', '.jpg', '.jpeg'
        ]

    @property
    def name(self) -> str:
        return "upload_file"

    @property
    def description(self) -> str:
        return """Upload a file for analysis. Returns the file path and basic info.
        Supported formats: CSV, Excel, JSON, text files, images, etc."""

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path where the file should be saved"
                },
                "content_base64": {
                    "type": "string",
                    "description": "Base64 encoded file content"
                }
            },
            "required": ["file_path", "content_base64"]
        }

    async def execute(self, file_path: str, content_base64: str, **kwargs: Any) -> str:
        """Save uploaded file to workspace."""
        try:
            # Validate extension
            ext = Path(file_path).suffix.lower()
            if ext not in self.allowed_extensions:
                return f"Error: File extension '{ext}' not allowed. Allowed: {', '.join(self.allowed_extensions)}"

            # Resolve path within workspace
            full_path = self.workspace / "uploads" / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Decode and save
            content = base64.b64decode(content_base64)
            full_path.write_bytes(content)

            # Get file info
            file_size = len(content)
            size_str = f"{file_size} bytes"
            if file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            result = f"✅ File uploaded successfully\n"
            result += f"Path: {full_path}\n"
            result += f"Size: {size_str}\n"

            # Preview for data files
            if ext in ['.csv', '.json']:
                try:
                    if ext == '.csv':
                        import pandas as pd
                        df = pd.read_csv(full_path, nrows=5)
                        result += f"\nPreview (first 5 rows):\n{df.to_string()}"
                        result += f"\n\nColumns: {list(df.columns)}"
                    elif ext == '.json':
                        with open(full_path, 'r') as f:
                            data = json.load(f)
                            result += f"\nPreview:\n{json.dumps(data, indent=2)[:500]}"
                except Exception as e:
                    result += f"\n(Could not generate preview: {e})"

            return result

        except Exception as e:
            return f"Error uploading file: {str(e)}"
