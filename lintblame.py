#!/usr/bin/python

"""lintblame"""

import os
import sys
import re
import subprocess

colors = {
    'header': '\033[95m',
    'blue': '\033[94m',
    'green': '\033[92m',
    'warn': '\033[93m',
    'fail': '\033[91m',
    'bold': '\033[1m',
    'endc': '\033[0m',
}

pylint_colors = {
    'C': 'bold',
    'F': 'fail',
    'E': 'fail',
}

def color(key, text):
    if not key:
        return text
    return colors[key] + text + colors['endc']

def get_name():
    path = os.path.expanduser('~/.gitconfig')
    if os.path.isfile(path):
        with open(path, 'r') as f:
            contents = f.read()
            match = re.search(r'name = (.+)$', contents, re.MULTILINE)
            if match:
                return match.group(1).strip()
    return None       

def validate_file():
    if len(sys.argv) < 2:
        sys.exit("Please provide an argument")

    target = os.path.join(os.getcwd(), sys.argv[1])
    if not target.endswith('.py'):
        sys.exit("{} is not a python file".format(target))
    return target

def blame():
    try:
        blame_results = subprocess.check_output(['git', 'blame', target])
    except subprocess.CalledProcessError:
        sys.exit("Unable to blame file")
    return blame_results

def lint():
    p = subprocess.Popen(
        ['pylint', '--output-format=text', target],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = p.communicate()
    return out
    
def report(lint_results, blame_results, my_name):
    lint_lines = lint_results.splitlines()
    blame_lines = blame_results.splitlines()
    
    blame_name_rex = re.compile(r'\(([\w\s]+)\d{4}')
    
    lints = re.findall(
        r'^(\w):\s+(\d+),\s*\d+:\s(.+)$',
        lint_results,
        re.MULTILINE
    )
    
    for i, lint in enumerate(lints):
        lint_code = lint[0]
        color_key = pylint_colors.get(lint_code)
        name_match = blame_name_rex.search(blame_lines[i])
        if name_match:
            name = name_match.group(1).strip()
        else:
            name = '???'
 
        if name == my_name:
            name = color('header', name)

        print('{lineno}: [{code}] {message} [{name}]'.format(
            code=color(color_key, lint_code),
            lineno=lint[1],
            message=color(color_key, lint[2]),
            name=name
        ))

if __name__ == '__main__':
    target = validate_file()
    name = get_name()
    blame_results = blame()
    lint_results = lint()
    report(lint_results, blame_results, name)



