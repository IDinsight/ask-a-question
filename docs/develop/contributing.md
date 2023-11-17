# Contributing to AAQ

Thank you for being interested in contributing to AAQ. 

AAQ is an open source project started by data scientists at IDinsight and sponsored by Google.org. Everyone is welcome to contribute to it - in fact, the success of the project depends on it! :handshake_dark_skin_tone:

## Pull requests guide

These steps show you how to raise a pull request to the project

### Make a fork

1. Fork the [project repository](https://github.com/IDinsight/aaq-core) by clicking on the "Fork" button

2. Clone the repo using:

```
git clone git@github.com:<your GitHub handle>/aaq-core.git
```

### Setup your virtual python environment

You can automatically create a ready-to-go `aaq-core` conda environment with:

    make fresh-env

??? warning "Errors with `pyscopg2`?"

    `psycopg2` vs `psycopg2-binary`: For production use cases we should use `psycopg2` but for local development,
    `psycopg2-binary` suffices and is often easier to install. If you are getting errors
    from `psycopg2`, try installing `psycopg2-binary` instead.

    If you would like `psycopg2-binary` instead of `psycopg2`, run `make fresh-env psycopg_binary=true` instead (see below for why you may want this).

    See [here](https://www.psycopg.org/docs/install.html#psycopg-vs-psycopg-binary) for more details.

??? note "Setting up the environment manually"

    If you would like to setup the environment manually, you can use conda to create virtual environment (or `venv` or other).

        conda create --name aaq-core python=3.10

    Install the python packages. While in `aaq-core` directory, run:

        pip install -r core_backend/requirements.txt
        pip install -r requirements-dev.txt

### Install pre-commit

Navigate to repo and run pre-commit

    cd aaq-core
    pre-commit install  # 👈 to run it automatically before each commit

### Make your changes

<div class="annotate" markdown>
1. Create a `feature` branch for your development changes:
```
git checkout -b feature
```

2. Make your changes and then run `pre-commits` if you have not set it up to run automatically.
```
pre-commit run --all      # 👈 to run it manually
```
3. Run `mypy` separately with `mypy core_backend/app` (1)

</div>

1. `pre-commit` runs in its own virtual environment. Since `mypy` needs all the
   packages installed, this would mean keeping a whole separate copy of your
   environment just for it. That's too bulky so the pre-commit only checks
   a few high-level typing things. You still need to run `mypy` directly to catch
   all the typing issues.
   If you forget, GitHub Actions 'Linting' workflow will pick up all the mypy errors.

3. Then `git add` and `git commit` your changes:
```
git add modified_files
git commit
```
And then push the changes to your fork in GitHub
```
git push -u origin feature
```
4. Go to the GitHub web page of your fork of the AAQ repo. Click the ‘Pull request’ button
to send your changes to the project’s maintainers for review.
This will send a notification to the committers.

## Next steps

See [Setup](./setup.md) on how to setup your development environment.
