# CONTRIBUTING

## Getting started

Requirements are listed in `setup.cfg` and can be installed with

```bash
pip install [--user] .[dev]
```

## Linting

The configuration for [black](https://black.readthedocs.io/en/stable/) and [flake8](https://flake8.pycqa.org/en/latest/index.html) can be modified in `setup.cfg`.

Comment lines with `# noqa: E123` to ignore certain linting errors.

## Testing

Tests make use [pytest](https://docs.pytest.org/en/stable/index.html) and can be run as follows

```bash
pytest .
```

Testing the installed project is done like this

```bash
pytest --pyargs ewoksorange.tests
```

## Write documentation

The documentation is composed of RST files located in `doc`. You can look at the [Sphinx doc](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) for information on how to write RST files.

If a new file is created, don't forget to reference it in one of the `toctree` directive.

## Build documentation

The documentation is built with [Sphinx](https://www.sphinx-doc.org/en/master/) that generates HTML pages out of the RST files. The configuration of Sphinx is in `doc/conf.py`.

Requirements (including Sphinx) can be installed with

```bash
pip install [--user] .[doc]
```

Then, build the documentation with

```bash
sphinx-build doc build/sphinx/html -E -a
```

The generated HTML pages will be available in `build/sphinx/html`. You can browse them easily by opening `build/sphinx/html/index.html` in your browser.

When rebuilding the documentation, don't forget to remove generated files to have a fresh `autodoc` documentation:

```bash
rm -rf doc/reference/_generated/; sphinx-build doc build/sphinx/html -E -a
```

## Releasing

1. Add the [changes](https://changelog.md) to `CHANGELOG.md`

2. Increment the version number in `<project>/__init__.py`. The number must match the [regex pattern](https://regex101.com/r/Ly7O1x/3/) provided by the [semantic versioning](https://semver.org) guidelines. For example the lifecycle of a single version could be

   ```
   1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta < 1.0.0-beta.1 < 1.0.0-rc.1 < 1.0.0
   ```

3. Deploy on [testpypi](https://test.pypi.org) and [pypi](https://pypi.org)

   ```bash
   rm -rf dist
   python3 setup.py sdist
   twine upload -r testpypi --sign dist/*
   twine upload -r pypi --sign dist/*
   ```

   Alternatively you can release the gitlab CI artifacts with the [deploy script](https://gitlab.esrf.fr/dau/ci/pyci/-/blob/main/scripts/deploy.sh)

   ```bash
   ./scripts/deploy.sh project_name [-n group/subgroup]
   ```

   or

   ```bash
   curl -sSL https://gitlab.esrf.fr/dau/ci/pyci/-/raw/main/scripts/deploy.sh | bash -s -- project_name [-n group/subgroup]
   ```

4. Create a git tag and write release notes in the `Tags` page of the gitlab repository

   ```bash
   git tag v1.2.3 -m "Release version 1.2.3"
   git push && git push --tags
   ```

   Alternatively you can use the [tag script](https://gitlab.esrf.fr/dau/ci/pyci/-/blob/main/scripts/tag.sh)

   ```bash
   ./scripts/tag.sh 1.2.3
   ```

   or

   ```bash
   curl -sSL https://gitlab.esrf.fr/dau/ci/pyci/-/raw/main/scripts/tag.sh | bash -s -- 1.2.3
   ```

5. Activate the tag on https://readthedocs.org when it is a stable version
