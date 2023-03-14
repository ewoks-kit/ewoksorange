# ewoksorange

*ewoksorange* provides s desktop graphical interface for [ewoks](https://ewoks.readthedocs.io/).

## Install

```bash
pip install ewoksorange[test]
```

When using Oasys instead of Orange3

```bash
pip install --no-deps ewoksorange
pip install ewokscore
pip install AnyQt
pip install oasys1
```

For the tests in an Oasys environment

```bash
pip install ewokscore[test]
pip install importlib_resources  # python_version < "3.7"
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

or for an installation with the system python

```bash
python3 -m ewoksorange.canvas
```

or when Orange3 is installed

```bash
orange-canvas /path/to/orange_wf.ows --config orangewidget.workflow.config.Config
```

or for an installation with the system python

```bash
python3 -m orangecanvas /path/to/orange_wf.ows --config orangewidget.workflow.config.Config
```

Launch the Orange canvas using the Ewoks CLI

```bash
ewoks execute /path/to/ewoks_wf.json --engine orange
ewoks execute /path/to/orange_wf.ows --engine orange
```

or for an installation with the system python

```bash
python3 -m ewoks execute /path/to/ewoks_wf.json --engine orange
python3 -m ewoks execute /path/to/orange_wf.ows --engine orange
```

Launch the Orange canvas with the examples add-on

```bash
ewoks-canvas --with-examples
```

or alternatively install the example add-ons

```bash
pip install src/ewoksorange/tests/examples/ewoks_example_1_addon
pip install src/ewoksorange/tests/examples/ewoks_example_2_addon
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
pip install -e src/ewoksorange/tests/examples/ewoks_example_1_addon
pip uninstall ewoks-example-1-addon
python3 -c "import site,os;os.unlink(os.path.join(site.getsitepackages()[0],'ewoks-example-1-addon-nspkg.pth'))"
```

## Documentation

https://ewoksorange.readthedocs.io/
