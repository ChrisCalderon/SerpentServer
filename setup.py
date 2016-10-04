from __future__ import print_function
from setuptools import setup
import os
import json


class SetupError(Exception):
    pass


def is_http(line):
    """Checks if a requirement.txt line is a link."""
    return line.startswith('http://') or line.startswith('https://')


def get_requirement_info():
    """Extracts dependency links and package names from requirements.txt"""
    links, requirements = [], []
    info = {'dependency_links': links, 'install_requires': requirements}
    requirements_path = 'requirements.txt'

    if not os.path.isfile(requirements_path):
        print('requirements.txt not found. Did you forget it?')
        return info

    reqs = filter(None, map(str.strip, open(requirements_path)))
    for line in reqs:
        if is_http(line):
            i = line.find('#egg=')
            if i == -1:
                raise SetupError('Missing \'#egg=\' in requirement link.')
            links.append(line[:i])
            requirements.append(line[i+5:])
        else:
            requirements.append(line)
    return info


def read_metadata():
    """Finds the package to install and returns it's metadata."""
    subdirs = next(os.walk(os.getcwd()))[1]

    for subdir in subdirs:
        if '__init__.py' in os.listdir(subdir):
            print('Found package:', subdir)
            break
    else:
        raise SetupError('No package found! Did you forget an __init__.py?')

    metadata = {'name': subdir, 'packages': [subdir]}
    relevant_keys = {'__version__': 'version',
                     '__author__': 'author',
                     '__email__': 'author_email',
                     '__license__': 'license'}

    m = open(os.path.join(subdir), '__init__.py')
    first_line = next(m)
    metadata['description'] = first_line.strip(). strip('\n "')
    for line in m:
        if len(relevant_keys) == 0:
            break
        for key in relevant_keys:
            if line.startswith(key):
                break
        else:
            continue

        metadatum_name = relevant_keys.pop(key)
        metadata[metadatum_name] = line.split('=', 1)[1].strip('\n\'\" ')

    if relevant_keys:
        print('FYI; You didn\'t put the following info in your __init__.py:')
        print('   ', ', '.join(relevant_keys))
    return metadata


def locate_scripts():
    """Finds scripts in the package."""
    scripts = []
    bin_dir = os.path.join(os.getcwd(), 'bin')
    if not os.path.isdir(bin_dir):
        return scripts
    for item in os.listdir(bin_dir):
        full_path = os.path.join(bin_dir, item)
        if os.path.isfile(full_path):
            with open(full_path) as f:
                first_line = next(f)
            if first_line.startswith('#!'):
                    scripts.append(full_path)
    return scripts

metadata = read_metadata()
metadata.update(get_requirement_info())
metadata['scripts'] = locate_scripts()

print(json.dumps(metadata, indent=2, sort_keys=True))

setup(**metadata)
