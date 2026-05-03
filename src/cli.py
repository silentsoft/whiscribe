import os
import sys
import subprocess

import flet as ft
from main import main


def launch():
    ft.run(main)


def get_version_from_pyproject():
    pyproject_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pyproject.toml")
    with open(pyproject_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("version = "):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def build():
    version = get_version_from_pyproject()
    print(f"Detected version: {version}")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(current_dir, "whiscribe", "version.py")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(f'version = "{version}"\n')
    print(f"Updated {version_file} with version {version}")

    platform_name = sys.platform
    if platform_name.startswith("darwin"):
        cmd = ["flet", "build", "macos", "--verbose"]
    elif platform_name.startswith("win"):
        cmd = ["flet", "build", "windows", "--verbose"]
    else:
        print(f"Unsupported platform: {platform_name}")
        sys.exit(1)

    print(f"Executing: {' '.join(cmd)}")
    try:
        project_root = os.path.dirname(current_dir)
        subprocess.run(cmd, cwd=project_root, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)
