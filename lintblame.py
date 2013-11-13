#!/usr/bin/python

"""lintblame!!!"""

import os
import sys
import re
import time
import subprocess
import datetime
from collections import defaultdict


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
    'pylint': re.compile(r'^(\w):\s+(\d+),\s*(\d+):\s(.+)$', re.MULTILINE),
}


class Environment(object):
    """Holds certain environmental values."""
    def __init__(self):
        self._git_name = False

    @property
    def git_name(self):
        """Returns name from .gitconfig or None."""

        if self._git_name is False:
            path = os.path.expanduser('~/.gitconfig')
            if os.path.isfile(path):
                with open(path, 'r') as open_f:
                    contents = open_f.read()
                    match = re.search(r'name = (.+)$', contents, re.MULTILINE)
                    if match:
                        self._git_name = match.group(1).strip()
                    else:
                        self._git_name = None
            else:
                self._git_name = None
        return self._git_name

ENV = Environment()


class Problem(object):
    """Represents an issue identified by a linter."""
    def __init__(self, lint_type, line, column, problem_code, message):
        self.lint_type = lint_type
        self.line = int(line)
        self.column = column
        self.problem_code = problem_code
        self.message = message

    def __str__(self):
        return '{}, {}: [{}] {}'.format(
            self.line,
            self.column,
            self.problem_code,
            self.message
        )


class TargetFile(object):
    """Represents a code file, and holds its linting issues."""
    blame_name_rex = re.compile(r'\(([\w\s]+)\d{4}')

    def __init__(self, path):
        self.path = path
        self._problems = defaultdict(list)
        self.lines = []

        try:
            self.blame_lines = subprocess.check_output(
                ['git', 'blame', self.path]
            ).splitlines()
        except subprocess.CalledProcessError:
            sys.exit("Unable to blame {}".format(self.path))

    def set_contents(self, contents):
        """Sets contents of the file this object references."""
        self.lines = contents.splitlines()

    @property
    def problems(self):
        """Returns generator that iterates over line, problem."""
        return self._problems.iteritems()

    @property
    def has_problems(self):
        return len(self._problems) > 0

    def add_problem(self, problem):
        self._problems[problem.line].append(problem)

    def author(self, lineno):
        match = self.blame_name_rex.search(self.blame_lines[int(lineno) - 1])
        if match:
            return match.group(1).strip()
        return None


def color(key, text):
    """Returns text wrapped with color."""
    if not key:
        return text
    return ''.join([COLORS[key], str(text), COLORS['endc']])


def validate_file_arg():
    """Returns file path if there's a valid file argument. Exits otherwise."""
    if len(sys.argv) < 2:
        sys.exit("Please provide an argument")

    target_file = os.path.join(os.getcwd(), sys.argv[1])
    if not target_file.endswith('.py'):
        sys.exit("{} is not a python file".format(target_file))
    return target_file


def pylint(path):
    """Returns pylint results."""
    proc = subprocess.Popen(
        'pylint --output-format=text {}'.format(path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    out, err = proc.communicate()
    if err:
        sys.exit(err)
    return out


def pep8(path):
    """Returns pep8 results."""
    proc = subprocess.Popen(
        ['pep8', path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = proc.communicate()
    if err:
        sys.exit(err)
    return out


def pylint_problems(path):
    results = pylint(path)
    for code, line, col, msg in REXES['pylint'].findall(results):
        yield Problem('pylint', line, col, code, msg)


def pep8_problems(path):
    results = pep8(path)
    for line, col, code, msg in REXES['pep8'].findall(results):
        yield Problem('pep8', line, col, code, msg)


def print_results(target_file):
    """Prints formatted results."""
    print(color('header', target_file.path))

    if not target_file.has_problems:
        print(color('bold', 'All clean!'))
    else:
        for line, problems in target_file.problems:
            author = target_file.author(line)
            author_color = 'blue'
            if author == ENV.git_name:
                author_color = 'warn'

            print('{}: [{}] {}'.format(
                color('bold', line),
                color(author_color, author),
                target_file.lines[line - 1].strip(),
            ))

            for problem in problems:
                color_key = PYLINT_COLORS.get(problem.problem_code)
                print('{space} [{code}] {msg}'.format(
                    space=' '.join(['' for i in range(len(str(line)) + 2)]),
                    code=problem.problem_code,
                    msg=color('bold', problem.message)
                ))
            print
    print


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


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
    if '--branch' in sys.argv or '-b' in sys.argv:
        files = get_branch_files()
    else:
        if os.path.isdir(sys.argv[1]):
            files = [f for f in os.listdir(sys.argv[1]) if f.endswith('.py')]
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


def run(files):
    start = datetime.datetime.now()
    target_files = []
    for path in files:
        target = TargetFile(path)
        with open(path, 'r') as open_f:
            target.set_contents(open_f.read())
        for problem in pylint_problems(path):
            target.add_problem(problem)
        for problem in pep8_problems(path):
            target.add_problem(problem)
        target_files.append(target)

    clear()
    for target in target_files:
        print_results(target)

    duration = datetime.datetime.now() - start
    print('Finished linting in {} seconds'.format(
        float(duration.seconds) + float(duration.microseconds) / 1000000
    ))


def watch(files):
    modified = {f: os.path.getmtime(f) for f in files}
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
            if loop_count > 0:
                print('Refreshing...')
            run(modified.keys())
        loop_count += 1
        time.sleep(1.5)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.append('--branch')
    watch(get_target_files())
