from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='napoleon',
    version='0.1',
    py_modules=['napoleon'],
    install_requires=required,
)
