#!/usr/bin/python

"""lintblame"""

import os
import sys
import re
import time
import subprocess
from collections import namedtuple

COLORS = {
    'header': '\033[95m',
    'blue': '\033[94m',
    'green': '\033[92m',
    'warn': '\033[93m',
    'fail': '\033[91m',
    'bold': '\033[1m',
    'white': '\033[37m',
    'endc': '\033[0m',
}

PYLINT_COLORS = {
    'C': 'bold',
    'F': 'fail',
    'E': 'fail',
    'W': 'white',
}

REXES = {
    'pep8': re.compile(r'\w+:(\d+):(\d+):\s(\w+)\s(.+)$', re.MULTILINE),
    'pylint': re.compile(r'^(\w):\s+(\d+),\s*\d+:\s(.+)$', re.MULTILINE),
}

Problem = namedtuple('Problem', ['line', 'column', 'code', 'message'])

def color(key, text):
    """Returns text wrapped with color."""
    if not key:
        return text
    return COLORS[key] + text + COLORS['endc']

def get_name():
    """Returns name from .gitconfig or None."""
    path = os.path.expanduser('~/.gitconfig')
    if os.path.isfile(path):
        with open(path, 'r') as open_f:
            contents = open_f.read()
            match = re.search(r'name = (.+)$', contents, re.MULTILINE)
            if match:
                return match.group(1).strip()
    return None

def validate_file_arg():
    """Returns file path if there's a valid file argument. Exits otherwise."""
    if len(sys.argv) < 2:
        sys.exit("Please provide an argument")

    target_file = os.path.join(os.getcwd(), sys.argv[1])
    if not target_file.endswith('.py'):
        sys.exit("{} is not a python file".format(target_file))
    return target_file


def blame(target_file):
    """Returns git blame results."""
    try:
        results = subprocess.check_output(['git', 'blame', target_file])
    except subprocess.CalledProcessError:
        sys.exit("Unable to blame file")
    return results


def pylint(target_file):
    """Returns pylint results."""
    proc = subprocess.Popen(
        ['pylint', '--output-format=text', target_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    out, err = proc.communicate()
    if err:
        sys.exit(err)
    return out


def pep8(target_file):
    """Returns pep8 results."""
    proc = subprocess.Popen(
        ['pep8', target_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = proc.communicate()
    if err:
        sys.exit(err)
    return out

def get_problems(target_file):
    results = pep8(target_file)
    problems = []
    for line, col, code, msg in REXES['pep8'].findall(results):
        problems.append(
            Problem(
                line=int(line),
                column=col,
                code=code,
                message=msg.strip()
            )
        )
    return problems

def print_results(target_file, my_name):
    """Prints formatted results."""
    print(color('header', target_file))
    blame_results = blame(target_file)
    blame_lines = blame_results.splitlines()
    blame_name_rex = re.compile(r'\(([\w\s]+)\d{4}')

    problems = get_problems(target_file)

    if len(problems) == 0:
        print(color('bold', 'All clean!'))
    for i, problem in enumerate(problems):
        color_key = PYLINT_COLORS.get(problem.code)
        name_match = blame_name_rex.search(blame_lines[problem.line - 1])
        if name_match:
            name = name_match.group(1).strip()
        else:
            name = '???'

        if name == my_name:
            name_str = ''.join(
                [
                    color('bold', '['),
                    color('fail', '!'),
                    color('warn', name),
                    color('fail', '!'),
                    color('bold', ']'),
                ]
            )
        else:
            name_str = '[{}]'.format(name)

        print('{lineno}: [{code}] {message} {name}'.format(
            code=color(color_key, problem.code),
            lineno=problem.line,
            message=color(color_key, problem.message),
            name=name_str
        ))
    print


def clear():
    os.system('cls' if os.name=='nt' else 'clear')


def get_git_path():
    return subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel']
    ).strip()


def get_branch_files():
    changed_files = subprocess.check_output(['git', 'diff', '--name-only'])
    branch_files = subprocess.check_output(
        ['git', 'diff', '--name-only', 'master..HEAD']
    )
    combined = set(changed_files.splitlines() + branch_files.splitlines())
    return [f.strip() for f in combined if f.endswith('py')]

def get_target_files():
    if '--branch' in sys.argv:
        files = get_branch_files()
    else:    
        files = [validate_file_arg()]
    top_path = get_git_path()
    return [os.path.join(top_path, f) for f in files]

def get_additional_files(current_files):
    target_files = get_target_files()
    return (
        [f for f in target_files if f not in current_files],
        [f for f in current_files if f not in target_files],
    )


def run(files, my_name):
    clear()
    for f in files:
        print_results(f, my_name)


def watch(files):
    my_name = get_name()
    modified = {f:os.path.getmtime(f) for f in files}
    loop_count = 0

    while True:
        should_run = False
        add_files, sub_files = get_additional_files(modified.keys())
        if add_files or sub_files:
            should_run = True
        for f in add_files:
            modified[f] = os.path.getmtime(f)
        for f in sub_files:
            modified.pop(f)

        if not should_run:
            for target_file in modified:
                mtime = os.path.getmtime(target_file)
                if mtime != modified.get(target_file):
                    modified[target_file] = mtime
                    should_run = True
                    break

        if should_run or loop_count == 0:
            run(modified.keys(), my_name)
        loop_count += 1
        time.sleep(2)

if __name__ == '__main__':
    watch(get_target_files())



