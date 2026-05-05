import os
import sys
import subprocess
import json

import flet as ft

from main import prepare_environment
from main import main


def launch():
    prepare_environment()
    ft.run(main)


def get_version_from_pyproject():
    pyproject_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pyproject.toml")
    with open(pyproject_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("version = "):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def update_version():
    version = get_version_from_pyproject()
    print(f"Detected version: {version}")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(current_dir, "whiscribe", "version.py")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(f'version = "{version}"\n')
    print(f"Updated {version_file} with version {version}")


def generate_notice():
    print("Generating NOTICE.md...")
    try:
        # Run pip-licenses to get dependency info including license files
        result = subprocess.run(
            ["pip-licenses", "--format=json", "--with-urls", "--from=mixed", "--with-license-file"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)

        # Determine the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        notice_path = os.path.join(project_root, "NOTICE.md")

        summary_lines = []
        detail_lines = []

        summary_lines.append("# Whiscribe")
        summary_lines.append("Copyright (c) silentsoft.org. All rights reserved.\n")

        for dep in data:
            name = dep.get("Name")
            version = dep.get("Version")
            url = dep.get("URL", "UNKNOWN")
            license_str = dep.get("License", "UNKNOWN")
            license_text = dep.get("LicenseText", "")

            # Skip the project itself
            if name in ["whiscribe"]:
                continue

            # Get the license name (first line only)
            license_name = license_str.split("\n")[0].strip()
            if license_name == "UNKNOWN":
                license_name = "License"
            
            # Generate a slug for the anchor link
            slug = f"{name}-{version}-{license_name}".lower()
            slug = "".join(c if c.isalnum() else "-" for c in slug)
            slug = "-".join(filter(None, slug.split("-"))) # cleanup multiple hyphens

            # Check if we have valid license text
            has_detail = license_text and license_text != "UNKNOWN"

            if has_detail:
                # Add to summary with a link
                summary_lines.append(f"__{name} {version}__")
                if url != "UNKNOWN":
                    summary_lines.append(f" * {url}")
                summary_lines.append(f" * [{license_name}](#{slug})\n")

                # Add to details section
                detail_lines.append("______\n")
                detail_lines.append(f"<a name=\"{slug}\"></a>")
                detail_lines.append(f"__{name} {version} ({license_name})__\n")
                detail_lines.append("```\n" + license_text.strip() + "\n```\n")
            else:
                # Add to summary without a link, skip details section
                summary_lines.append(f"__{name} {version}__")
                if url != "UNKNOWN":
                    summary_lines.append(f" * {url}")
                summary_lines.append(f" * {license_name}\n")

        # Combine and write the NOTICE.md file
        with open(notice_path, "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))
            f.write("\n")
            f.write("\n".join(detail_lines))
        
        print(f"Successfully generated {notice_path}")
    except FileNotFoundError:
        print("Warning: pip-licenses not found. Please run 'poetry install' first.")
    except Exception as e:
        print(f"Warning: Failed to generate NOTICE.md: {e}")


def package():
    update_version()
    generate_notice()

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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        subprocess.run(cmd, cwd=project_root, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)
