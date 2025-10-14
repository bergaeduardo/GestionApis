from setuptools import setup, find_packages

setup(
    name="GestionAPI",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'pywin32',
        # Agrega aquí otras dependencias necesarias
    ],
    author="Eduardo Berga",
    description="Sistema de gestión de APIs y servicios",
    python_requires=">=3.8",
)