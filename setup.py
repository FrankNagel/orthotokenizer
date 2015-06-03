# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


requires = [
    'regex',
    'docopt',
    'six',
]

tests_require = [
    'mock',
]

docs_extras = [
    'Sphinx',
    'docutils',
]

testing_extras = tests_require + [
    'nose',
    'coverage',
]


def read(fname):
    with open(fname) as fp:
        content = fp.read()
    return content


setup(
    name='orthotokenizer',
    version="0.1.0",
    description='',
    long_description=read("README.rst"),
    author='Steven Moran',
    author_email='steven.moran@uzh.ch',
    url='https://github.com/lingpy/orthotokenizer',
    install_requires=requires,
    license=read("LICENSE"),
    zip_safe=False,
    keywords='tokenizer',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    packages=find_packages(),
    include_package_data=True,
    extras_require={'testing': testing_extras, 'docs': docs_extras},
    tests_require=tests_require,
    test_suite="orthotokenizer.tests",
    entry_points={
        'console_scripts': [
            "create_profiles = orthotokenizer.scripts.create_profiles:main",
            "tokenize = orthotokenizer.scripts.tokenize:main",
            "context_tokenizer = orthotokenizer.scripts.context_tokenizer:main",
        ]
    },
)
