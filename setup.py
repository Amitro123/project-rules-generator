from setuptools import find_packages, setup

setup(
    name="project-rules-generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "pydantic>=2.0.0",
        "tqdm>=4.66.0",
        "google-generativeai>=0.8.6",
        "groq>=0.4.0",
        "python-dotenv>=1.0.0",
        "gitpython>=3.1.0",
        "rich>=13.0.0",
        "opik>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "prg=main:main",
        ],
    },
    author="Codeium User",
    description="A tool to generate Clinerules and Agent Skills from project context.",
    python_requires=">=3.8",
)
