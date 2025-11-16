"""
Setup script for CryptoScan - Professional Crypto Payment Monitoring Library
"""

from setuptools import setup, find_packages
import os


def read_file(filename):
    """Read file contents."""
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()


def read_requirements():
    """Read requirements from requirements.txt."""
    try:
        return read_file('requirements.txt').strip().split('\n')
    except FileNotFoundError:
        return ['httpx[http2]>=0.24.0,<1.0.0']


setup(
    name="pycryptoscan",
    version="2.0.0",
    author="DedInc.",
    author_email="visitanimation@gmail.com",
    description="Professional Real-Time Crypto Payment Monitoring Library for Python",
    long_description=read_file('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/DedInc/cryptoscan",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Office/Business :: Financial",
        "Topic :: Security :: Cryptography",
    ],
    license="MIT",
    python_requires=">=3.8",
    install_requires=read_requirements(),
    keywords=[
        "cryptocurrency", "crypto", "payment", "monitoring", "blockchain",
        "solana", "ethereum", "bitcoin", "async", "httpx", "http2", "fintech"
    ],
    project_urls={
        "Bug Reports": "https://github.com/DedInc/cryptoscan/issues",
        "Source": "https://github.com/DedInc/cryptoscan"
    },
    include_package_data=True,
    zip_safe=False,
)
