# Contributing to AAQ

Thank you for your interest in contributing to AAQ!

AAQ is an open source project started by data scientists at IDinsight and sponsored by
Google.org. Everyone is welcome to contribute! :handshake_dark_skin_tone:

---
**Note**

If you want to set up the complete development environment for AAQ first, you can
follow the [setup instructions here](./setup.md). Otherwise, this page provides general
guidelines on how to contribute to the project with a minimal setup.

---

## Pull requests guide

This section shows you how to raise a pull request to the project.

### Make a fork
1. Fork the [project repository](https://github.com/IDinsight/ask-a-question) by clicking on
the "Fork" button.
2. Clone the repo using:

        git clone git@github.com:<your GitHub handle>/ask-a-question.git

3. Navigate to the project directory.

        cd ask-a-question

### Install prerequisites

Install
[conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).

### Setup your virtual Python environment

You can automatically create a ready-to-go `aaq` conda environment with:

    make fresh-env
    conda activate aaq

If you encounter errors while installing `psycopg2`, see [here](setup.md#psycopg2) for
troubleshooting.

If you would like to set up your Python environment manually, you can follow the steps
[here](setup.md#set-up-manually).

### Make your changes

<div class="annotate" markdown>

1. Create a `feature` branch for your development changes:

        git checkout -b feature

2. Run `mypy` with `mypy core_backend/app` (1)

3. Then `git add` and `git commit` your changes:

        git add modified_files
        git commit

4. And then push the changes to your fork in GitHub

        git push -u origin feature

5. Go to the GitHub web page of your fork of the AAQ repo. Click the `Pull request`
button to send your changes to the project’s maintainers for review. This will send a
notification to the committers.

</div>

1. `pre-commit` runs in its own virtual environment. Since `mypy` needs all the
   packages installed, this would mean keeping a whole separate copy of your
   environment just for it. That's too bulky so the pre-commit only checks
   a few high-level typing things. You still need to run `mypy` directly to catch
   all the typing issues.
   If you forget, GitHub Actions 'Linting' workflow will pick up all the mypy errors.

## Next steps

If you haven't already, see [Setup](./setup.md) on how to set up the complete
development environment for AAQ. Otherwise, you can check out
[how to test the AAQ codebase](./testing.md).
