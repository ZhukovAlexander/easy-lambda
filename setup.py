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
      url='https://github.com/ZhukovAlexander/lambdify',
      cmdclass=versioneer.get_cmdclass(),
      keywords='aws lambda task queue distributed computing',
      classifiers=['Development Status :: 3 - Alpha',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Apache Software License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: System :: Distributed Computing',
                   'Topic :: Utilities']
      )
