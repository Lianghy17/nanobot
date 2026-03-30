"""Plot server - Manages chart generation and serving for the web interface."""

import base64
import json
import os
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class PlotServer:
    """
    Server for generating and serving matplotlib charts.
    
    Features:
    - Execute Python code and capture matplotlib plots
    - Save plots as PNG files
    - Provide URLs for frontend display
    - Persist to Jupyter notebooks
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.plots_dir = workspace / "plots"
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.notebooks_dir = workspace / "notebooks"
        self.notebooks_dir.mkdir(parents=True, exist_ok=True)
        
    def get_session_plot_dir(self, session_id: str) -> Path:
        """Get the plot directory for a session."""
        safe_id = session_id.replace(":", "_")
        plot_dir = self.plots_dir / safe_id
        plot_dir.mkdir(parents=True, exist_ok=True)
        return plot_dir
    
    def get_plot_url(self, session_id: str, plot_name: str) -> str:
        """Get the URL for a plot."""
        safe_id = session_id.replace(":", "_")
        return f"/plots/{safe_id}/{plot_name}"
    
    async def execute_python(self, code: str, session_id: str, timeout: int = 120) -> dict:
        """
        Execute Python code and capture any generated plots.
        
        Returns:
            dict with keys:
                - success: bool
                - output: str (stdout/stderr)
                - plots: list of plot URLs
                - error: str (if any)
        """
        plot_dir = self.get_session_plot_dir(session_id)
        notebook_dir = self.notebooks_dir / session_id.replace(":", "_")
        notebook_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Executing Python code for session {session_id}")
        logger.debug(f"Plot dir: {plot_dir}")
        
        # Generate execution script
        script = self._generate_script(code, plot_dir)
        
        try:
            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            # Execute in subprocess
            process = await __import__('asyncio').create_subprocess_exec(
                sys.executable, script_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.workspace),
                env={**os.environ, "MPLBACKEND": "Agg"}
            )
            
            try:
                stdout, stderr = await __import__('asyncio').wait_for(
                    process.communicate(), timeout=timeout
                )
            except __import__('asyncio').TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "output": f"Error: Execution timed out after {timeout} seconds",
                    "plots": [],
                    "error": "Timeout"
                }
            finally:
                os.unlink(script_path)
            
            # Parse output
            try:
                result = json.loads(stdout.decode('utf-8', errors='replace'))
            except json.JSONDecodeError:
                result = {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "plots": []
                }
            
            # Get generated plot files
            plot_files = list(plot_dir.glob("*.png"))
            plot_urls = []
            for plot_file in sorted(plot_files):
                # Get relative name
                plot_name = plot_file.name
                url = self.get_plot_url(session_id, plot_name)
                plot_urls.append(url)
                logger.debug(f"Generated plot: {plot_file} -> {url}")
            
            # Build output message
            output_parts = []
            if result.get("stdout"):
                output_parts.append(result["stdout"])
            if result.get("stderr"):
                output_parts.append(f"STDERR:\n{result['stderr']}")
            
            output = "\n".join(output_parts) if output_parts else "(no output)"
            
            # Save to notebook
            await self._save_to_notebook(code, output, plot_files, notebook_dir)
            
            return {
                "success": True,
                "output": output,
                "plots": plot_urls,
                "plot_files": [str(f) for f in plot_files],
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Python execution error: {e}")
            return {
                "success": False,
                "output": f"Error: {str(e)}",
                "plots": [],
                "error": traceback.format_exc()
            }
    
    def _generate_script(self, code: str, plot_dir: Path) -> str:
        """Generate the Python execution script."""
        return f'''#!/usr/bin/env python3
import sys
import json
import io
import base64
import os
from pathlib import Path

# Plot directory
plot_dir = Path(r"{plot_dir}")
plot_dir.mkdir(parents=True, exist_ok=True)

# Track plots
plot_count = len(list(plot_dir.glob("plot_*.png")))
plot_files = []

# Patch matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Must be before importing pyplot
    import matplotlib.pyplot as plt
    
    original_show = plt.show
    
    def patched_show(*args, **kwargs):
        global plot_count
        # Save figure
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        
        # Save to file
        plot_path = plot_dir / f"plot_{{plot_count:03d}}.png"
        plot_path.write_bytes(buf.read())
        plot_files.append(str(plot_path))
        plot_count += 1
        
        plt.close('all')
        print(f"[PLOT_SAVED] {{plot_path}}")
    
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

error_msg = None

try:
    # Execute user code
    exec_globals = {{}}
    exec(r"""
{code}
""", exec_globals)
    
except Exception as e:
    error_msg = str(e)
    import traceback
    traceback.print_exc()

finally:
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    
    # Close any remaining figures
    try:
        import matplotlib.pyplot as plt
        if plt.get_fignums():
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                
                global plot_count
                plot_path = plot_dir / f"plot_{{plot_count:03d}}.png"
                plot_path.write_bytes(buf.read())
                plot_files.append(str(plot_path))
                plot_count += 1
                print(f"[PLOT_SAVED] {{plot_path}}")
            plt.close('all')
    except:
        pass

# Output result
result = {{
    "success": error_msg is None,
    "stdout": stdout_capture.getvalue(),
    "stderr": stderr_capture.getvalue(),
    "error": error_msg,
    "plots": plot_files
}}

print(json.dumps(result))
'''
    
    async def _save_to_notebook(self, code: str, output: str, plot_files: list[Path], notebook_dir: Path):
        """Save execution results to a Jupyter notebook."""
        try:
            notebook_path = notebook_dir / "analysis.ipynb"
            
            # Load or create notebook
            if notebook_path.exists():
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)
            else:
                notebook = {
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Python 3",
                            "language": "python",
                            "name": "python3"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 4,
                    "cells": []
                }
            
            # Add code cell
            code_cell = {
                "cell_type": "code",
                "execution_count": len([c for c in notebook["cells"] if c.get("cell_type") == "code"]) + 1,
                "metadata": {},
                "source": code.split('\n'),
                "outputs": []
            }
            
            # Add text output
            if output.strip():
                code_cell["outputs"].append({
                    "output_type": "stream",
                    "name": "stdout",
                    "text": output.split('\n')
                })
            
            # Add plot outputs
            for plot_file in plot_files:
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
            
            notebook["cells"].append(code_cell)
            
            # Add timestamp cell
            notebook["cells"].append({
                "cell_type": "markdown",
                "metadata": {},
                "source": [f"---\n*Executed at: {datetime.now().isoformat()}*"]
            })
            
            # Save notebook
            with open(notebook_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Notebook saved: {notebook_path}")
            
        except Exception as e:
            logger.error(f"Failed to save notebook: {e}")
    
    def get_plot_path(self, session_id: str, plot_name: str) -> Path | None:
        """Get the full path to a plot file."""
        safe_id = session_id.replace(":", "_")
        plot_path = self.plots_dir / safe_id / plot_name
        
        if plot_path.exists() and plot_path.is_file():
            return plot_path
        return None
    
    def list_session_plots(self, session_id: str) -> list[dict]:
        """List all plots for a session."""
        plot_dir = self.get_session_plot_dir(session_id)
        
        plots = []
        for plot_file in sorted(plot_dir.glob("*.png")):
            stat = plot_file.stat()
            plots.append({
                "name": plot_file.name,
                "url": self.get_plot_url(session_id, plot_file.name),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return plots
    
    def clear_session_plots(self, session_id: str):
        """Clear all plots for a session."""
        plot_dir = self.get_session_plot_dir(session_id)
        
        if plot_dir.exists():
            for plot_file in plot_dir.glob("*.png"):
                plot_file.unlink()
            logger.info(f"Cleared plots for session {session_id}")
