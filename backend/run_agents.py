import subprocess
import shlex
import os
import re
import sys


def run_multi_agent_and_get_itinerary(user_request: str, timeout: int = 5000) -> str:
    """
    Runs the multi-agent script as a subprocess, provides the user_request to its stdin,
    captures stdout, and extracts the itinerary block.


    Assumes `multi_agent_script.py` is in the repository root.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'Travel_agent_framework', 'travel_multi_agent.py')
    script_path = os.path.abspath(script_path)


    # Use python executable from current environment
    cmd = [sys.executable, script_path]


    # Run the script and provide the user_request as stdin plus newline
    proc = subprocess.run(cmd, input=user_request + "\n", capture_output=True, text=True, timeout=timeout)


    if proc.returncode != 0:
        # include stderr for debugging
        raise RuntimeError(f"Script failed (code={proc.returncode}): {proc.stderr}")


    stdout = proc.stdout
    with open(r"C:\Users\Peter.Marriott\Documents\final-project-peter-griffin\backend\log.txt", "w") as fp:
        fp.write(stdout)

    # Extract itinerary starting at the marker if present
    marker = '_________________________TRAVEL ITINERARY_________________________'
    if marker in stdout:
        itinerary = stdout.split(marker, 1)[1].strip()
        # Prepend marker for clarity
        return marker + "\n\n" + itinerary


    # If marker not present, return full stdout
    return stdout