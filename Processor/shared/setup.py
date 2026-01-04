from setuptools import setup, find_packages

setup(
    name="neuroclima-shared",
    version="7.0.0",
    description="Shared libraries for NeuroClima microservices",
    author="NeuroClima Team",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "httpx>=0.24.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.9",
)
