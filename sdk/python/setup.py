from setuptools import setup, find_packages

setup(
    name="cost-aware-llm",
    version="1.0.0",
    description="Official Python SDK for cost-aware-llm",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0"
    ],
    python_requires=">=3.8",
)
