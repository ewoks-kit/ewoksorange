# ewoks_example_1_addon

An example Orange3 addon project which uses Ewoks.

## Install distribution

```bash
pip install ewoksorange/tests/examples/ewoks_example_1_addon/ -vv
```

## Register without installation

```python
from ewoksorange.registration import register_addon_package
from ewoksorange.test.examples import ewoks_example_1_addon

register_addon_package(ewoks_example_1_addon)
```
