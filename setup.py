from setuptools import setup
import os

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as requirements:
    install_requires = requirements.readlines()

setup(name='lambdify',
      install_requires=install_requires,
      setup_requires=['setuptools_scm'],
      use_scm_version=True,
      author='Alexander Zhukov',
      author_email='zhukovaa90@gmail.com',
      url='https://github.com/ZhukovAlexander/lambdify',
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
