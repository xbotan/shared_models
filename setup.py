from setuptools import setup, find_packages

setup(
    name="shared_models",
    version="0.1.18",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
    ],
)
