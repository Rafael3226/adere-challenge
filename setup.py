"""Setup script for Adere Challenge."""

from setuptools import setup, find_packages

setup(
    name="adere-challenge",
    version="1.0.0",
    description="A solver for the Adere Star Wars & Pokémon Challenge",
    author="Adere Challenge Solver",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv",
        "urllib3",
        "colorama",
    ],
    entry_points={
        "console_scripts": [
            "adere=adere_challenge.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 