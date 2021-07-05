from pkg_resources import iter_entry_points
from prybar import dynamic_entrypoint

from contextlib import ExitStack


epoints = [
    dynamic_entrypoint("example.types", name=name, module="nonexisting")
    for name in ["int", "float", "str", "bool"]
]
with ExitStack() as stack:
    for ep in epoints:
        stack.enter_context(ep)

    for ep in iter_entry_points("example.types"):
        t = ep.load()
        print(t("12"))
