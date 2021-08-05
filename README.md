# EwoksOrange: Orange binding for Ewoks

## Install

```bash
python -m pip install ewoksorange[test]
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

## Documentation

https://workflow.gitlab-pages.esrf.fr/ewoks/ewoksorange/
