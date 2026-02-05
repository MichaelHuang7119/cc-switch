from setuptools import setup, find_packages

setup(
    name="cc-switch",
    version="0.1.0",
    packages=find_packages(),
    package_dir={"": "backend"},
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "python-multipart>=0.0.6",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt>=4.0.0",
        "httpx>=0.25.0",
        "aiosqlite>=0.19.0",
        "cryptography>=41.0.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.8",
)

# For pytest, add this to allow running tests from backend directory
if __name__ == "__main__":
    pass