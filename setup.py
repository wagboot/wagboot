from setuptools import setup, find_packages

from version import get_git_version

setup(name='wagboot',
      author='Dmitry Ulupov',
      author_email='dima@ulupov.com',
      url='https://github.com/wagboot/wagboot',
      version=get_git_version(),
      packages=find_packages(),
      include_package_data=True,
      install_requires=['wagtail>=1.3.1', 'django>=1.8.0', 'libsass==0.10.1', 'six', 'django-ace==1.0.2'])
