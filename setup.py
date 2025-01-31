from setuptools import setup, find_packages

setup(
    name="shared_models",
    version="0.1.16",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
    ],
)
