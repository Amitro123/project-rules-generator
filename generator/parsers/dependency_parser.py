"""Parse dependency files from multiple ecosystems."""

import json
import logging
import re
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Use tomllib (3.11+) or tomli as fallback
_tomllib: Optional[types.ModuleType] = None
try:
    import tomllib as _tomllib_impl

    _tomllib = _tomllib_impl
except ModuleNotFoundError:
    try:
        import tomli as _tomllib_impl2

        _tomllib = _tomllib_impl2
    except ModuleNotFoundError:
        _tomllib = None
tomllib = _tomllib


class DependencyParser:
    """Parse dependency files: requirements.txt, pyproject.toml, package.json."""

    @staticmethod
    def parse_requirements_txt(file_path: Path) -> List[Dict[str, str]]:
        """
        Parse requirements.txt into structured dependency list.

        Handles:
        - package==version, package>=version, package~=version
        - -e git+... (editable installs)
        - -r other-file (recursive includes - skipped)
        - Comments and blank lines

        Returns:
            List of dicts: [{'name': 'fastapi', 'version': '0.100.0', 'constraint': '==', 'raw': 'fastapi==0.100.0'}]
        """
        deps: List[Dict[str, str]] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return deps

        for line in content.splitlines():
            line = line.strip()

            # Skip blanks, comments, options, recursive includes
            if not line or line.startswith("#") or line.startswith("-r") or line.startswith("--"):
                continue

            # Editable installs
            if line.startswith("-e"):
                raw = line[2:].strip()
                # Extract package name from git URL
                match = re.search(r"#egg=(.+)", raw)
                name = match.group(1) if match else raw
                deps.append(
                    {
                        "name": name.lower(),
                        "version": "",
                        "constraint": "editable",
                        "raw": line,
                    }
                )
                continue

            # Standard: package[extras]>=version
            match = re.match(
                r"^([a-zA-Z0-9_.-]+)"  # package name
                r"(?:\[([^\]]+)\])?"  # optional extras
                r"(?:(==|>=|<=|~=|!=|>|<)"  # constraint operator
                r"([a-zA-Z0-9._*-]+))?"  # version
                r"(.*)$",  # remainder (env markers etc.)
                line,
            )
            if match:
                name = match.group(1).lower().replace("_", "-")
                extras = match.group(2) or ""
                constraint = match.group(3) or ""
                version = match.group(4) or ""
                deps.append(
                    {
                        "name": name,
                        "version": version,
                        "constraint": constraint,
                        "extras": extras,
                        "raw": line,
                    }
                )
            else:
                # Fallback: treat entire line as package name
                deps.append(
                    {
                        "name": line.lower().split("[")[0].split(";")[0].strip(),
                        "version": "",
                        "constraint": "",
                        "raw": line,
                    }
                )

        return deps

    @staticmethod
    def parse_pyproject_toml(file_path: Path) -> Dict:
        """
        Parse pyproject.toml for dependencies and project metadata.

        Returns:
            {
                'project_name': str,
                'python_requires': str,
                'dependencies': [{'name': ..., 'version': ..., 'raw': ...}],
                'dev_dependencies': [...],
                'build_system': str,
            }
        """
        result: Dict[str, Any] = {
            "project_name": "",
            "python_requires": "",
            "dependencies": [],
            "dev_dependencies": [],
            "build_system": "",
        }

        if tomllib is None:
            logger.warning("tomli/tomllib not available - cannot parse pyproject.toml")
            # Fallback: basic regex extraction
            return DependencyParser._parse_pyproject_fallback(file_path)

        try:
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return result

        # Project metadata
        project = data.get("project", {})
        result["project_name"] = project.get("name", "")
        result["python_requires"] = project.get("requires-python", "")

        # Main dependencies
        for dep_str in project.get("dependencies", []):
            parsed = DependencyParser._parse_pep508(dep_str)
            if parsed:
                result["dependencies"].append(parsed)

        # Optional/dev dependencies
        optional = project.get("optional-dependencies", {})
        for group_name, group_deps in optional.items():
            for dep_str in group_deps:
                parsed = DependencyParser._parse_pep508(dep_str)
                if parsed:
                    parsed["group"] = group_name
                    result["dev_dependencies"].append(parsed)

        # Poetry-style dependencies
        poetry = data.get("tool", {}).get("poetry", {})
        if poetry:
            for name, spec in poetry.get("dependencies", {}).items():
                if name.lower() == "python":
                    result["python_requires"] = spec if isinstance(spec, str) else str(spec)
                    continue
                version = spec if isinstance(spec, str) else spec.get("version", "") if isinstance(spec, dict) else ""
                result["dependencies"].append(
                    {
                        "name": name.lower(),
                        "version": version.lstrip("^~>=<! "),
                        "constraint": "",
                        "raw": f"{name} = {spec}",
                    }
                )
            for name, spec in poetry.get("group", {}).get("dev", {}).get("dependencies", {}).items():
                version = spec if isinstance(spec, str) else spec.get("version", "") if isinstance(spec, dict) else ""
                result["dev_dependencies"].append(
                    {
                        "name": name.lower(),
                        "version": version.lstrip("^~>=<! "),
                        "constraint": "",
                        "raw": f"{name} = {spec}",
                    }
                )

        # Build system
        build = data.get("build-system", {})
        result["build_system"] = build.get("build-backend", "")

        return result

    @staticmethod
    def _parse_pyproject_fallback(file_path: Path) -> Dict:
        """Fallback parsing when tomllib is not available."""
        result: Dict[str, Any] = {
            "project_name": "",
            "python_requires": "",
            "dependencies": [],
            "dev_dependencies": [],
            "build_system": "",
        }
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            # Extract name
            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                result["project_name"] = match.group(1)

            # Extract dependencies from dependencies = [...] block
            dep_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if dep_match:
                dep_block = dep_match.group(1)
                for dep_str in re.findall(r'["\']([^"\']+)["\']', dep_block):
                    parsed = DependencyParser._parse_pep508(dep_str)
                    if parsed:
                        result["dependencies"].append(parsed)
        except OSError as e:
            logger.warning(f"Fallback pyproject.toml parsing failed: {e}")

        return result

    @staticmethod
    def parse_package_json(file_path: Path) -> Dict:
        """
        Parse package.json for Node.js dependencies.

        Returns:
            {
                'project_name': str,
                'dependencies': [{'name': ..., 'version': ...}],
                'dev_dependencies': [{'name': ..., 'version': ...}],
                'scripts': dict,
                'engines': dict,
            }
        """
        result: Dict[str, Any] = {
            "project_name": "",
            "dependencies": [],
            "dev_dependencies": [],
            "scripts": {},
            "engines": {},
        }

        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return result

        result["project_name"] = data.get("name", "")
        result["scripts"] = data.get("scripts", {})
        result["engines"] = data.get("engines", {})

        for name, version in data.get("dependencies", {}).items():
            result["dependencies"].append(
                {
                    "name": name.lower(),
                    "version": version.lstrip("^~>=<! "),
                    "constraint": "",
                    "raw": f'"{name}": "{version}"',
                }
            )

        for name, version in data.get("devDependencies", {}).items():
            result["dev_dependencies"].append(
                {
                    "name": name.lower(),
                    "version": version.lstrip("^~>=<! "),
                    "constraint": "",
                    "raw": f'"{name}": "{version}"',
                }
            )

        return result

    @staticmethod
    def _parse_pep508(dep_str: str) -> Optional[Dict[str, str]]:
        """Parse a PEP 508 dependency string."""
        if not dep_str.strip():
            return None

        try:
            from packaging.requirements import Requirement

            req = Requirement(dep_str)

            # Extract extras
            extras = ",".join(sorted(req.extras)) if req.extras else ""

            # Extract version/specifier
            # packaging stores it as SpecifierSet, convert to string
            version = str(req.specifier) if req.specifier else ""

            # Extract marker
            marker = str(req.marker) if req.marker else ""

            # Extract URL if present
            url = req.url if hasattr(req, "url") and req.url else ""

            return {
                "name": req.name.lower().replace("_", "-"),
                "version": version,
                "constraint": "",  # Kept for compatibility, mostly empty or part of version
                "extras": extras,
                "marker": marker,
                "url": url,
                "raw": dep_str.strip(),
            }
        except (ValueError, TypeError):
            # Fallback for simple cases if packaging fails or is missing
            # logger.debug(f"packaging parse failed for {dep_str}: {e}")
            match = re.match(
                r"^([a-zA-Z0-9_.-]+)" r"(?:\[([^\]]+)\])?" r"\s*(?:(==|>=|<=|~=|!=|>|<)\s*([a-zA-Z0-9._*-]+))?",
                dep_str.strip(),
            )
            if match:
                return {
                    "name": match.group(1).lower().replace("_", "-"),
                    "version": match.group(4) or "",
                    "constraint": match.group(3) or "",
                    "extras": match.group(2) or "",
                    "raw": dep_str.strip(),
                }
            return None

    @staticmethod
    def parse_readme_pip_install(readme_path: Path) -> List[Dict[str, str]]:
        """Extract dependencies from `pip install ...` commands in README.

        Fallback for projects with no requirements.txt / pyproject.toml.
        Parses lines like:
            pip install fastapi uvicorn openai gitpython websockets
            pip3 install -r requirements.txt  (skipped — file reference)
            pip install fastapi[all]>=0.100.0
        """
        deps: List[Dict[str, str]] = []
        try:
            content = readme_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return deps

        # Match pip/pip3 install commands (may be inside code blocks)
        for match in re.finditer(
            r"(?:pip3?|python -m pip)\s+install\s+(.+)",
            content,
        ):
            args_str = match.group(1).strip()
            # Skip file/url references
            if args_str.startswith(("-r ", "--requirement", "git+", "http")):
                continue

            for token in args_str.split():
                # Skip flags
                if token.startswith("-"):
                    continue
                # Parse: package[extras]>=version
                pkg_match = re.match(
                    r"^([a-zA-Z0-9_.-]+)" r"(?:\[([^\]]+)\])?" r"(?:(==|>=|<=|~=|!=|>|<)([a-zA-Z0-9._*-]+))?",
                    token,
                )
                if pkg_match:
                    deps.append(
                        {
                            "name": pkg_match.group(1).lower().replace("_", "-"),
                            "version": pkg_match.group(4) or "",
                            "constraint": pkg_match.group(3) or "",
                            "raw": token,
                            "source": "readme",
                        }
                    )

        return deps

    @staticmethod
    def detect_system_dependencies(project_path: Path) -> List[str]:
        """Detect system-level dependencies from code and docs."""
        system_deps = []
        system_markers = {
            "ffmpeg": [r"\bffmpeg\b", r"subprocess.*ffmpeg", r"import ffmpeg"],
            "imagemagick": [r"\bconvert\b.*image", r"imagemagick"],
            "graphviz": [r"\bgraphviz\b", r"import graphviz"],
            "tesseract": [r"\btesseract\b", r"pytesseract"],
            "redis-server": [r"redis://", r"redis\.Redis"],
            "postgresql": [r"postgresql://", r"psycopg"],
            "mysql": [r"mysql://", r"pymysql"],
        }

        # Scan Python files and README
        scan_files: set = set()
        scan_files.update(project_path.glob("*.py"))
        scan_files.update(project_path.glob("README*"))

        # Add recursive scan, but the set will handle duplicates if logic changes
        # Previously: glob("*.py") AND glob("**/*.py") caused root files to be double counted
        # The glob("**/*.py") includes root files !!
        # So we just need the recursive glob.
        scan_files = set(project_path.glob("**/*.py"))
        scan_files.update(project_path.glob("README*"))

        # Limit scanning to avoid performance issues
        # Sort to ensure deterministic behavior for tests/limiting
        scan_files_list = sorted(list(scan_files))[:50]

        combined_content = ""
        for f in scan_files_list:
            try:
                combined_content += f.read_text(encoding="utf-8", errors="replace")[:2000]
            except OSError:
                continue

        content_lower = combined_content.lower()
        for dep_name, patterns in system_markers.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    system_deps.append(dep_name)
                    break

        return list(set(system_deps))
