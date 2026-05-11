"""Setup script for YouTube Reaction Pipeline."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ytb-pipeline",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A multi-stage pipeline for processing YouTube videos to identify and extract reactive segments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ytb-pipeline",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[r for r in requirements if not r.startswith("pytest") and not r.startswith("black") and not r.startswith("flake8")],
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=23.0.0", "flake8>=6.0.0"],
    },
    entry_points={
        "console_scripts": [
            "ytb-pipeline=ytb_pipeline.cli:main",
        ],
    },
)
