from setuptools import setup, find_packages

setup(
    name="ssh-ws-tunnel",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "websockets>=10.4",
        "pyyaml>=6.0",
        "python-dotenv>=0.21.0",
    ],
    entry_points={
        "console_scripts": [
            "ssh-ws-tunnel=src.main:main",
        ],
    },
    author="Your Name",
    description="SSH over WebSocket proxy with Cloudflare SSL and auto-update",
    python_requires=">=3.8",
)
