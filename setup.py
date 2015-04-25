# stevedore/example/setup.py
from setuptools import setup, find_packages
import re
from pip.req import parse_requirements
import uuid


requirements = parse_requirements('requirements.txt', session=uuid.uuid1())
install_requires = [str(ir.req) for ir in requirements if not ir.url]

setup(
    name='nekbot.protocols.irc',
    namespace_packages = ['nekbot.protocols'],
    version='0.1',

    description='IRC Protocol for Nekbot, a modular multiprotocol bot.',

    author='Nekmo',
    author_email='contacto@nekmo.com',

    url='https://bitbucket.org/Nekmo/nekbot-irc',

    classifiers=[
        'Natural Language :: Spanish',
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Topic :: Communications :: Conferencing',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    platforms=['linux'],

    scripts=[],

    provides=['nekbot.protocols.irc',
              ],
    
    install_requires=install_requires,

    packages=['nekbot', 'nekbot.protocols', 'nekbot.protocols.irc'],
    include_package_data=True,

    
    entry_points={
        'nekbot.protocols': [
            'irc = nekbot.protocols.irc:MyIRC',
        ],
    },

    zip_safe=False,
)