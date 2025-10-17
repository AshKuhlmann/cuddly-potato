from setuptools import setup, find_packages

setup(
    name="cuddly-potato",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Click",
        "rich",
        "customtkinter",
        "openpyxl",
    ],
    entry_points={
        "console_scripts": [
            "cuddly-potato=cuddly_potato.cli:cli",
        ],
    },
    author="Your Name",
    author_email="you@example.com",
    description="A CLI and GUI tool for logging and managing data entries",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
)
