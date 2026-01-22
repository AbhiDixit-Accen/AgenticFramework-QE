from setuptools import setup, find_packages

setup(
    name="quality_engineering_agentic_framework",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "quality_engineering_agentic_framework.utils.rag": ["data/requirements/*"],
    },
    install_requires=[
        "openai>=1.0.0",
        "google-generativeai>=0.3.0",
        "pyyaml>=6.0",
        "selenium>=4.10.0",
        "webdriver-manager>=4.0.0",
        "pytest>=7.0.0",
        "click>=8.0.0",
        "pandas>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "qeaf=quality_engineering_agentic_framework.cli.cli:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Quality Engineering Agentic Framework for automated test generation using LLMs",
    keywords="testing, automation, llm, ai, agents",
    python_requires=">=3.8",
)