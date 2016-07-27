from setuptools import setup, find_packages

from version import get_git_version

setup(name='wagboot',
      author='UDIO Systems',
      author_email='development@udiosystems.com',
      url='https://udiosystems.com',
      version=get_git_version(),
      packages=find_packages(),
      include_package_data=True,
      install_requires=['wagtail>=1.5.2',
                        'django>=1.8.0,<1.10',
                        'libsass==0.10.1',
                        'six',
                        'django-ace==1.0.2',
                        'django-crispy-forms>=1.6,<1.7'])
