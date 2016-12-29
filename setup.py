from setuptools import setup, find_packages
import catools

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='CA Tools',
    version=catools.__version__,
    packages=find_packages(exclude=('tests', 'docs')),
    url='https://github.com/jsarver/catools',
    license=license,
    install_requires=['pyyaml', 'suds-jurko'],
    author='Josh Sarver',
    author_email='josh.sarver@gmail.com',
    description='Helper Library for CA Service Desk Soap API',
    long_description=readme
)
