# EwoksOrange: Orange binding for Ewoks

## Install

```bash
python -m pip install ewoksorange[test]
```

When using Oasys instead of Orange3

```bash
python -m pip install --no-deps ewoksorange
python -m pip install ewokscore
python -m pip install AnyQt
python -m pip install oasys1
```

For the tests in an Oasys environment

```bash
python -m pip install ewokscore[test]
python -m pip install importlib_resources  # python_version < "3.7"
```

## Test

```bash
pytest --pyargs ewoksorange.tests
```

## Getting started

Launch the Orange canvas with the examples Addon

```bash
python -m ewoksorange.canvas --with_example
```

or alternatively install the example Addon and launch the Orange canvas normally

```bash
python -m pip install ewoksorange/tests/examples/ewoks_example_1_addon
python -m pip install ewoksorange/tests/examples/ewoks_example_2_addon

python -m Orange.canvas
```

When removing an editable install, you may need to delete one file manually:

```bash
python -m pip install -e ewoksorange/tests/examples/ewoks_example_1_addon
python -m pip uninstall ewoks-example-1-addon
python -c "import site,os;os.unlink(os.path.join(site.getsitepackages()[0],'ewoks-example-1-addon-nspkg.pth'))"
```

## Documentation

https://workflow.gitlab-pages.esrf.fr/ewoks/ewoksorange/
