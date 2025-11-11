import subprocess
import sys
import os

script_path = os.path.join(os.path.dirname(__file__), "main.py")
subprocess.call([sys.executable, script_path])
