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

Launch the Orange canvas

```bash
ewoks-canvas /path/to/orange_wf.ows
```

or when Orange3 is installed

```bash
orange-canvas /path/to/orange_wf.ows --config orangewidget.workflow.config.Config
```

Launch the Orange canvas using the Ewoks CLI

```bash
ewoks execute /path/to/ewoks_wf.json --binding orange
ewoks execute /path/to/orange_wf.ows --binding orange
```

Launch the Orange canvas with the examples add-on

```bash
ewoks-canvas --with-examples
```

or alternatively install the example add-ons

```bash
python -m pip install ewoksorange/tests/examples/ewoks_example_1_addon
python -m pip install ewoksorange/tests/examples/ewoks_example_2_addon
```

and launch the Orange canvas with

```bash
ewoks-canvas /path/to/orange_wf.ows
```

or when Orange3 is installed

```bash
orange-canvas /path/to/orange_wf.ows
```

When removing an editable install, you may need to delete one file manually:

```bash
python -m pip install -e ewoksorange/tests/examples/ewoks_example_1_addon
python -m pip uninstall ewoks-example-1-addon
python -c "import site,os;os.unlink(os.path.join(site.getsitepackages()[0],'ewoks-example-1-addon-nspkg.pth'))"
```

## Documentation

https://ewoksorange.readthedocs.io/
