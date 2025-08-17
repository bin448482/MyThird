from setuptools import setup, find_packages

setup(
    name="resume-auto-submitter",
    version="1.0.0",
    description="自动投递简历工具",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "selenium>=4.15.0",
        "langchain>=0.1.0",
        "openai>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.0.0",
        "pytest>=7.0.0",
        "webdriver-manager>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "resume-submitter=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)