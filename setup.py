from setuptools import setup, find_packages

setup(
    name="cuddly-potato",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Click",
        "rich",
        "customtkinter",
    ],
    entry_points={
        "console_scripts": [
            "cuddly-potato = cuddly_potato.cli:cli",
        ],
    },
)
