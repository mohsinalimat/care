from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in care/__init__.py
from care import __version__ as version

setup(
	name='care',
	version=version,
	description='Auto perform pos invoice',
	author='RF',
	author_email='sales@resourcesfactor.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
