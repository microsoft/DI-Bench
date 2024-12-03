LOCATE_FILE_PROMPT = """You are a developer familiar with Python projects. You will be given a GitHub action CI yml file that includes commands for installing dependencies. You will also be provided with the project skeleton, including the names of each file and path under root. You will also be given several options of related files, including their content. Your task is to locate which file contains the list of dependency packages (note: we care about the project dependency packages, not the dev-dependencies that required for developing, like flake8, etc.). Your output shoule be a JSON object with the schema: {"dependency_file": str}.

Here is an example:

- CI YML file:
```yaml
dependencies:
  - name: pip
    run: |
      pip install -r requirements.txt
      pip install -r requirements.dev.txt
```
- Project skeleton:
```
setup.py
pyproject.toml
tests/main_test.py
README.md
requirements.txt
requirements.dev.txt
```
- Related files content:
...
- Output:
{"dependency_file": "requirements.txt"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"dependency_file": str}, which indicates the file path under root.
- Some projects install dependency packages in different ways, such as `poetry install` or `pip install -e .`, please make decision in flexibily.
"""


LOCATE_LINE_PROMPT = """You are a developer familiar with Python project configuration files. You will be given a file which is one of the following: pyproject.toml, setup.py, setup.cfg, requirements.txt, etc. The content you are provided contains line numbers at the beginning of each line. Your task is to give a list of line numbers where the list of project dependency packages are defined. (note: we care about the project dependency packages, not the dev-dependencies that required for developing, like flake8, etc. In some cases, the dev-dependencies has specific field name, please ignore them.) You should output a JSON object with the schema: {"dependency_lines": List[int]}.

Here is an example:
- File content (pyproject.toml):
```
0: [build-system]
1: requires = ["flit_core >=2,<4"]
2: build-backend = "flit_core.buildapi"
3:
4: [project]
5: name = "aiosqlite"
6: readme = "README.rst"
7: license = {file="LICENSE"}
8: dynamic = ["version", "description"]
9: authors = [
10:     {name="Amethyst Reese", email="amy@n7.gg"},
11: ]
12: classifiers = [
13:     "Development Status :: 5 - Production/Stable",
14:     "Framework :: AsyncIO",
15:     "Intended Audience :: Developers",
16:     "License :: OSI Approved :: MIT License",
17:     "Topic :: Software Development :: Libraries",
18: ]
19: requires-python = ">=3.8"
20: dependencies = [
21:     "typing_extensions >= 4.0",
22:     "openai >= 1.0",
23: ]
24:
25: [project.optional-dependencies]
26: dev = [
27:     "attribution==1.7.1",
28:     "black==24.3.0",
29:     "coverage[toml]==7.4.4",
30:     "flake8==7.0.0",
31:     "flake8-bugbear==24.2.6",
32:     "flit==3.9.0",
33:     "mypy==1.9.0",
34:     "ufmt==2.5.1",
35:     "usort==1.0.8.post1",
36: ]
37: docs = [
38:     "sphinx==7.2.6",
39:     "sphinx-mdinclude==0.5.3",
40: ]
```
- Output:
{"dependency_lines": [21, 22]}

Important notes:
- Your output should only contain a single JSON object in the schema: {"dependency_lines": List[int]}, which indicates the line numbers.
- Only project dependency, not dev or doc.
- Only output the lines that define dependency packages, which is, at least include package name, not the bracket, etc.
"""

LOCATE_TEST_CI_PROMPT = """You are a developer familiar with GitHub Actions CI workflow. You will be given a list of workflow configuration yaml files, including file names and contents, defined under the `.github/workflows` directory. Your task is to find the one workflow that contains the project tests, i.e., that runs the tests. Your output should be a JSON object with the schema: {"ci_file": str}.

Here is an example:
# Input:
--- Start of .github/workflows/lint.yml ---
name: Lint
on:
  push:
    branches:
      - 'main'
  pull_request:


concurrency:
  cancel-in-progress: true
  group: ${{ github.workflow }}-${{ github.ref_name }}

jobs:
  lint:
    name: Python linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"
          cache: pip
          cache-dependency-path: deeplake/requirements/*.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r deeplake/requirements/common.txt
          pip install -r deeplake/requirements/tests.txt
          pip install -r deeplake/requirements/plugins.txt

      - name: Install deeplake
        run: pip install -e .

      - name: Check formatting with black
        if: always()
        run: |
          black --version
          black --check .

      - name: Lint docstrings with darglint
        if: always()
        run: |
          darglint --version
          darglint .

      - name: Check typing with mypy
        if: always()
        run: |
          mypy --version
          mypy .
--- End of .github/workflows/lint.yml ---

--- Start of .github/workflows/tests.yml ---
name: Langchain Tests

permissions:
  contents: read
  id-token: write

on:
  schedule:
    - cron: '0 4 * * *'
  workflow_dispatch: {}

concurrency:
  group: ${{ github.workflow }}
  cancel-in-progress: true

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - name: checkout
        uses: actions/checkout@v4.1.7
        with:
          ref: ${{ github.sha }}

      - name: configure aws credentials
        uses: aws-actions/configure-aws-credentials@v4.0.2
        with:
          role-to-assume: ${{ secrets.aws_role_arn }}
          aws-region: us-east-1
          role-duration-seconds: 21600
          role-session-name: deeplake-${{ github.sha }}

      - name: configure environment
        working-directory: .github/tests
        shell: bash
        run: |
          python3 -m venv .venv
          source .venv/bin/activate
          python3 setup_actions.py
          curl -sSL https://install.python-poetry.org | python3 -
          poetry install
          pip install -r requirements.txt

      - name: run tests
        working-directory: .github/tests
        env:
          ACTIVELOOP_TOKEN: ${{ secrets.ACTIVELOOP_HUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          BUCKET: ${{ secrets.AWS_S3_BUCKET }}
        run: |
          source .venv/bin/activate
          python3 -m pytest test_activeloop*
--- End of .github/workflows/tests.yml ---

# Output:
{"ci_file": ".github/workflows/tests.yml"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"ci_file": str}, which indicates the file path.
- The file should contains the project main tests, not the linting, doctest, etc.
- If there is no workflow contains test, output an empty: {"ci_file": ""}
"""

ACT_COMMAND_PROMPT = """You are a developer familiar with GitHub Action CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform and multi-version testing. Your task is to write an act command based on this file. The command should specify the project test job's ID and select only one matrix option, running tests only on Ubuntu Linux and choosing only one sdk version (if no matrix is used, this can be ignored). Your output should be a JSON object with the schema: {"act_command": str}.

Here is an example:
# Input:
--- Start of .github/workflows/common.yml ---
name: Common

on:
  push:
    branches:
      - master
  workflow_dispatch:
  pull_request:
    types: [review_requested, ready_for_review, auto_merge_enabled]

jobs:
  docs:
    name: Documentation
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # no need to check documentation with multiple python versions
        python-version: [ "3.12" ]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          # cache dependencies, cf. https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
          cache: 'pip'
          cache-dependency-path: './setup.cfg'

      - name: Install dependencies
        run: pip install tox tox-uv

      # - name: Check RST format
      #   run: tox -e doclint

      - name: Check README.rst
        run: tox -e readme

      - name: Check documentation build with Sphinx
        run: |
          sudo apt-get install graphviz
          tox -e docs-test
  tests:
    name: Tests
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: [ "3.9", "3.12" ]
        # cannot use macos-latest for now, cf.
        # https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#choosing-github-hosted-runners
        # cannot use Python 3.8
        # cannot use M1 at all, since PyG does not provide M1 packages...
        # include:
        #   - os: macos-14
        #     python-version: "3.11"

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          # cache dependencies, cf. https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
          cache: 'pip'
          cache-dependency-path: './setup.cfg'

      - name: Install dependencies
        run: pip install tox tox-uv

      - name: Run fast tests
        run: tox -e py

      - name: Run slow tests
        run: tox -e integration

      - name: Run doctests
        run: tox -e doctests

      # - name: Test notebooks
      #   run: tox -e treon

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
--- End of .github/workflows/common.yml ---

# Output:
{"act_command": "act -j 'tests' --matrix python-version:3.9 --matrix os:ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"act_command": str}, which indicates the act command.
- The command should only specify the -j option and --matrix option (if matrix is used).
- The specified job should be the one that runs the project tests, not the linting, doctest, etc.
- If there is no test job, output an empty: {"act_command": ""}
"""

# ================================
# Prompts for Java Projects
# ================================

JAVA_ENV_PROMPT = """You are a developer familiar with Github Actions CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform or multi-sdk-version. In some case, there is no matrix, only fixed sdk version and platform. You will also be provided a act command for executing a certain job with a certain sdk version and platform. Your task is to determine the sdk version and OS platform that the act command runs based on the provided information. Your output should be a JSON object with the schema: {"SDK": str, "OS": str}.

Here is an example:
# Input:
--- Start of .github/workflows/maven.yml ---
name: Java CI with Maven

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

jobs:
  build:

    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2
    - name: Set up JDK 8
      uses: actions/setup-java@v2
      with:
        java-version: '8'
        distribution: 'temurin'
        cache: maven
    - name: maven
      run: mvn -B package --file pom.xml
--- End of .github/workflows/maven.yml ---
## Act command:
act -j 'build' -W '.github/workflows/maven.yml'

# Output:
{"SDK": "JDK 8", "OS": "ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"SDK": str, "OS": str}, which indicates the java sdk version and OS platform.
- If you cannot determine certain field, please put "N/A" in the field.
"""

LOCATE_TEST_CI_PROMPT_JAVA = """You are a developer familiar with GitHub Actions CI workflow. You will be given a list of workflow configuration yaml files for a Java project, including file names and contents, defined under the `.github/workflows` directory. Your task is to find the one workflow that contains the project tests, i.e., that runs the tests. Your output should be a JSON object with the schema: {"ci_file": str}.

Here is an example:
# Input:
--- Start of .github/workflows/lint.yml ---
name: Lint
on:
  push:
    branches:
      - 'main'
  pull_request:


concurrency:
  cancel-in-progress: true
  group: ${{ github.workflow }}-${{ github.ref_name }}

jobs:
  lint:
    name: Java linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK
        uses: actions/setup-java@v3
        with:
          java-version: "11"
          distribution: 'adopt'

      - name: Install dependencies
        run: |
          mvn install -DskipTests

      - name: Check formatting with Checkstyle
        if: always()
        run: |
          mvn checkstyle:check

      - name: Lint code with SpotBugs
        if: always()
        run: |
          mvn spotbugs:check
--- End of .github/workflows/lint.yml ---

--- Start of .github/workflows/java-tests.yml ---
name: Java Tests

permissions:
  contents: read
  id-token: write

on:
  schedule:
    - cron: '0 4 * * *'
  workflow_dispatch: {}

concurrency:
  group: ${{ github.workflow }}
  cancel-in-progress: true

jobs:
  java-tests:
    runs-on: ubuntu-latest
    steps:
      - name: checkout
        uses: actions/checkout@v4.1.7
        with:
          ref: ${{ github.sha }}

      - name: Set up JDK
        uses: actions/setup-java@v3
        with:
          java-version: "11"
          distribution: 'adopt'

      - name: Build with Maven
        run: mvn clean install

      - name: Run tests
        env:
          MAVEN_OPTS: "-Xmx2g"
        run: mvn test
--- End of .github/workflows/java-tests.yml ---

# Output:
{"ci_file": ".github/workflows/java-tests.yml"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"ci_file": str}, which indicates the file path.
- The file should contains the project main tests, not the linting, doctest, etc.
- If there is no workflow contains test, output an empty: {"ci_file": ""}
"""

ACT_COMMAND_PROMPT_JAVA = """You are a developer familiar with GitHub Action CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform and multi-version testing. Your task is to write an act command based on this file. The command should specify the project test job's ID and select only one matrix option, running tests only on Ubuntu Linux and choosing only one JDK version (if no matrix is used, this can be ignored). Your output should be a JSON object with the schema: {"act_command": str}.

Here is an example:
# Input:
--- Start of .github/workflows/common.yml ---
name: Common

on:
  push:
    branches:
      - master
  workflow_dispatch:
  pull_request:
    types: [review_requested, ready_for_review, auto_merge_enabled]

jobs:
  docs:
    name: Documentation
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # no need to check documentation with multiple JDK versions
        java-version: [ "11", "17" ]
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK ${{ matrix.java-version }}
        uses: actions/setup-java@v3
        with:
          java-version: ${{ matrix.java-version }}
          distribution: 'adopt'

      - name: Install dependencies
        run: mvn clean install

  tests:
    name: Tests
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        java-version: [ "8", "11", "17" ]
        # cannot use macos-latest for now, cf.
        # https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#choosing-github-hosted-runners

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK ${{ matrix.java-version }}
        uses: actions/setup-java@v3
        with:
          java-version: ${{ matrix.java-version }}
          distribution: 'adopt'

      - name: Install dependencies
        run: mvn clean install

      - name: Run tests
        run: mvn test

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
--- End of .github/workflows/common.yml ---

# Output:
{"act_command": "act -j 'tests' --matrix java-version:11 --matrix os:ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"act_command": str}, which indicates the act command.
- The project is Java project.
- The command should only specify the -j option and --matrix option (if matrix is used).
- The specified job should be the one that runs the project tests, not the linting, doctest, etc.
- If there is no test job, output an empty: {"act_command": ""}
"""

# ================================
# Prompts for Python Projects
# ================================

PYTHON_ENV_PROMPT = """You are a developer familiar with Github Actions CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform or multi-python-version. In some case, there is no matrix, only fixed python version and platform. You will also be provided a act command for executing a certain job with a certain python version and platform. Your task is to determine the python version and OS platform that the act command runs based on the provided information. Your output should be a JSON object with the schema: {"SDK": str, "OS": str}.

Here is an example:
# Input:
--- Start of .github/workflows/common.yml ---
# GitHub Action workflow to build and run Impacket's tests
#

name: Build and test Impacket

on: [push, pull_request]

env:
  DOCKER_TAG: impacket:latests

jobs:
  lint:
    name: Check syntax errors and warnings
    runs-on: ubuntu-latest
    if:
      github.event_name == 'push' || github.event.pull_request.head.repo.full_name !=
      github.repository

    steps:
      - name: Checkout Impacket
        uses: actions/checkout@v3

      - name: Setup Python 3.8
        uses: actions/setup-python@v4
        with:
          python-version: 3.8

      - name: Install Python dependencies
        run: |
          python -m pip install flake8

      - name: Check syntax errors
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Check PEP8 warnings
        run: |
          flake8 . --count --ignore=E1,E2,E3,E501,W291,W293 --exit-zero --max-complexity=65 --max-line-length=127 --statistics

  test:
    name: Run unit tests and build wheel
    needs: lint
    runs-on: ${{ matrix.os }}
    if:
      github.event_name == 'push' || github.event.pull_request.head.repo.full_name !=
      github.repository

    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.8", "3.9", "3.10","3.11"]
        experimental: [false]
        os: [ubuntu-latest]
        include:
          - python-version: "3.12-dev"
            experimental: true
            os: ubuntu-latest
    continue-on-error: ${{ matrix.experimental }}

    steps:
      - name: Checkout Impacket
        uses: actions/checkout@v3

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip wheel
          python -m pip install tox tox-gh-actions -r requirements.txt -r requirements-test.txt

      - name: Run unit tests
        run: |
          tox -- -m 'not remote'

      - name: Build wheel artifact
        run: |
          python setup.py bdist_wheel
--- End of .github/workflows/common.yml ---
## Act command:
act -j 'test' --matrix python-version:3.8 --matrix os:ubuntu-latest -W '.github/workflows/common.yml'

# Output:
{"SDK": "Python 3.8", "OS": "ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"SDK": str, "OS": str}, which indicates the python version and OS platform.
- If you cannot determine certain field, please put "N/A" in the field.
"""

# ================================
# Prompts for Csharp Projects
# ================================

CSHARP_ENV_PROMPT = """You are a developer familiar with Github Actions CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform or multi-csharp-sdk-version. In some case, there is no matrix, only fixed csharp sdk version and platform. You will also be provided a act command for executing a certain job with a certain sdk version and platform. Your task is to determine the sdk version and OS platform that the act command runs based on the provided information. Your output should be a JSON object with the schema: {"SDK": str, "OS": str}.

Here is an example:
# Input:
--- Start of .github/workflows/build.yml ---
#https://lukelowrey.com/use-github-actions-to-publish-nuget-packages/
name: Publish Packages

on:
   # push:
   #    branches: [ master ]
   workflow_dispatch:

jobs:
   build:
      runs-on: ubuntu-latest
      env:
         HUSKY: 0
      steps:
         -  name: Checkout code
            uses: actions/checkout@v3

         -  name: Setup .NET 8
            uses: actions/setup-dotnet@v3
            with:
               dotnet-version: 8.0.x
         -  name: Print information
            run: |
               ls -la
               dotnet --info
         -  name: Restore dependencies
            run: dotnet restore
         -  name: Build
            run: dotnet build --configuration Release --no-restore
         -  name: Test
            run: dotnet test --configuration Release --no-build --verbosity normal
--- End of .github/workflows/build.yml ---
## Act command:
act -j 'build' -W '.github/workflows/build.yml'

# Output:
{"SDK": "dotnet 8", "OS": "ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"SDK": str, "OS": str}, which indicates the sdk version and OS platform.
- If you cannot determine certain field, please put "N/A" in the field.
"""

# ================================
# Prompts for Typescript Projects
# ================================

TS_ENV_PROMPT = """You are a developer familiar with Github Actions CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform or multi-sdk-version. In some case, there is no matrix, only fixed sdk version and platform. You will also be provided a act command for executing a certain job with a certain sdk version and platform. Your task is to determine the sdk version and OS platform that the act command runs based on the provided information. Your output should be a JSON object with the schema: {"SDK": str, "OS": str}.

Here is an example:
# Input:
--- Start of .github/workflows/run_tests.yml ---
name: Node.js CI

on:
  push:
    branches: [ main, typescript4.6 ]
    tags: [ '*' ]
  pull_request:
    branches: [ main ]
  release:
    types: [ published ]

jobs:
  build:

    runs-on: ${{ matrix.os }}

    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [20.x, 22.x]

    steps:
      - uses: actions/checkout@v4
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm install
      - run: npm run build --if-present
      - run: npm test
--- End of .github/workflows/run_tests.yml ---
## Act command:
act -j 'build' --matrix node-version:20.x --matrix os:ubuntu-latest -W '.github/workflows/run_tests.yml'

# Output:
{"SDK": "node 20.x", "OS": "ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"SDK": str, "OS": str}, which indicates the sdk version and OS platform.
- If you cannot determine certain field, please put "N/A" in the field.
"""

RUST_ENV_PROMPT = """You are a developer familiar with Github Actions CI workflows and act (a tool for running GitHub Actions locally). You will be provided with a GitHub Action CI .yml file containing the project's test job, which may use a matrix for multi-platform or multi-sdk-version. In some case, there is no matrix, only fixed sdk version and platform. You will also be provided a act command for executing a certain job with a certain sdk version and platform. Your task is to determine the sdk version and OS platform that the act command runs based on the provided information. Your output should be a JSON object with the schema: {"SDK": str, "OS": str}.

Here is an example:
# Input:
--- Start of .github/workflows/ci.yml ---
name: CI

on:
  merge_group:
  pull_request:
    branches:
      - main

jobs:
  linter-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: 1.81.0
          components: clippy, rustfmt
      - name: Run clippy
        run: cargo clippy --all-targets --all-features -- --deny warnings
      - name: Run rustfmt
        run: cargo fmt --all -- --check

  tests-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: 1.81.0
      - name: Run backend tests
        run: cargo test
--- End of .github/workflows/ci.yml ---
## Act command:
act -j 'tests-backend' -W '.github/workflows/ci.yml'

# Output:
{"SDK": "Rust toolchain 1.81.0", "OS": "ubuntu-latest"}

Important notes:
- Your output should only contain a single JSON object in the schema: {"SDK": str, "OS": str}, which indicates the sdk version and OS platform.
- If you cannot determine certain field, please put "N/A" in the field.
"""
