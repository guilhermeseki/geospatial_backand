cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="geospatial_backend",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here if needed
        # "fastapi",
        # "pydantic",
    ],
)
EOF