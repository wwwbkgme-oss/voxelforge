from setuptools import setup, find_packages

setup(
    name             = "voxelforge",
    version          = "1.0.0",
    description      = "AI-Powered Voxel World Builder",
    long_description = open("README.md", encoding="utf-8").read(),
    long_description_content_type = "text/markdown",
    author           = "VoxelForge",
    url              = "https://github.com/wwwbkgme-oss/voxelforge",
    license          = "MIT",
    packages         = find_packages(exclude=["tests*", "examples*"]),
    python_requires  = ">=3.10",
    install_requires = [
        "numpy>=1.24.0",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.29.0",
        "pydantic>=2.0.0",
        "requests>=2.31.0",
    ],
    extras_require   = {
        "ai":  ["openai>=1.20.0"],
        "dev": ["pytest>=8.0.0", "httpx>=0.27.0"],
    },
    entry_points     = {
        "console_scripts": [
            "voxelforge=cli.main:main",
        ],
    },
    classifiers      = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment",
        "Topic :: Multimedia :: Graphics :: 3D Modeling",
    ],
    keywords = "voxel game ai procedural generation MagicaVoxel game-development",
)
