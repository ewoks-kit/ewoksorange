# ewoksorange

*ewoksorange* provides s desktop graphical interface for [ewoks](https://ewoks.readthedocs.io/).

## Install

```bash
pip install ewoksorange[test]
```

When using Oasys instead of Orange3

```bash
pip install oasys1
pip install AnyQt
pip install importlib_resources  # python_version < "3.9"
pip install ewokscore
pip install pytest
pip install --no-deps ewoksorange
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

and launch the Orange canvas with

```bash
ewoks-canvas /path/to/orange_wf.ows
```

or when Orange3 is installed

```bash
orange-canvas /path/to/orange_wf.ows
```

## Documentation

https://ewoksorange.readthedocs.io/
