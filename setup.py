from distutils.core import setup
import os

import versioneer

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as requirements:
    install_requires = requirements.readlines()

setup(name='lambdify',
      version=versioneer.get_version(),
      install_requires=install_requires,
      author='Alexander Zhukov',
      author_email='zhukovaa90@gmail.com',
      cmdclass=versioneer.get_cmdclass(), )
