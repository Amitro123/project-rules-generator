"""Infrastructure TechProfile entries."""

from typing import List

from generator.tech.profile import TechProfile

INFRASTRUCTURE: List[TechProfile] = [
    TechProfile(
        name="docker",
        display_name="Docker",
        category="infrastructure",
        skill_name="docker-deployment",
        packages=["docker"],
        readme_keywords=["docker", "dockerfile"],
        tools=["docker", "docker-compose"],
        detection_files=["Dockerfile", "Dockerfile.dev", "Dockerfile.prod"],
        rules={
            "high": [
                "Use multi-stage builds to minimize image size",
                "Don't run containers as root (use USER directive)",
                "Pin specific versions in base images (not :latest)",
            ],
            "medium": [
                "Use .dockerignore to exclude unnecessary files",
                "Set health checks with HEALTHCHECK directive",
                "Use docker-compose for multi-container setups",
            ],
        },
    ),
    TechProfile(
        name="docker-compose",
        display_name="Docker Compose",
        category="infrastructure",
        skill_name="",
        packages=[],
        readme_keywords=["docker-compose"],
        detection_files=["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"],
    ),
    TechProfile(
        name="github-actions",
        display_name="GitHub Actions",
        category="infrastructure",
        skill_name="",
        packages=[],
        readme_keywords=["github actions"],
        detection_dirs=[".github/workflows"],
    ),
    TechProfile(
        name="kubernetes",
        display_name="Kubernetes",
        category="infrastructure",
        skill_name="",
        packages=[],
        readme_keywords=["kubernetes", "k8s"],
        tools=["kubectl", "helm"],
        detection_dirs=["k8s", "kubernetes"],
    ),
    TechProfile(
        name="uvicorn",
        display_name="Uvicorn",
        category="infrastructure",
        skill_name="uvicorn-server",
        packages=["uvicorn"],
        readme_keywords=["uvicorn"],
    ),
    TechProfile(
        name="git",
        display_name="Git",
        category="infrastructure",
        skill_name="",
        packages=[],
        readme_keywords=["git"],
        tools=["git"],
    ),
]
