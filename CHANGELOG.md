# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `orangecontrib.ewoksnowidget.global_cleanup_ewoksnowidget` removes all dynamically generated widget
  declarations from the `orangecontrib.ewoksnowidget` Orange add-on. Used by pytest fixture `qtapp`.

### Fixed

- Widget classes from Ewoks tasks without Orange widget are now generated dynamically when
  opening or executing `.ows` files.

## [2.0.1] - 2025-09-22

### Fixed

- Fix type mismatch when linking `EwoksOrange` widgets to native Orange widgets
  [!232](https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/-/merge_requests/232)
- Fix error when converting an Ewoks workflow containing native Orange widgets to OWS format
  (with `ewoks_to_ows`) [#59](https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/-/issues/59)

## [2.0.0] - 2025-07-25

### Added

- Implement the `WorkflowEngineWithSerialization` interface.
- Add an entry point to the group `ewoks.engines`.
- Add an entry point to the group `ewoks.engines.serialization.representations`.

## [1.2.0] - 2025-06-10

### Changed

- Drop support for Python 3.6 and 3.7.
- `ows_to_ewoks`: load default inputs even when the orange widget does not exist.
- `OWEwoksWidgetOneThreadPerRun`: ensure every execution result is used and not
  ignored because of a new execution.

## [1.1.0] - 2025-01-13

### Added

- PyQt6 compatibility (now used by default).

## [1.0.0] - 2024-12-25

## [0.9.0] - 2024-11-07

### Added

- Add `task_options` to `execute_graph`.

### Fixed

- `OWEwoksWidgetOneThreadPerRun`: fix `__disconnect_all_task_executors`.

## [0.8.0] - 2024-10-15

### Changed

- `OWEwoksWidgetOneThread`, `OWEwoksWidgetOneThreadPerRun`, `OWEwoksWidgetWithTaskStack`:
  new method `cancel_running_task` to cancel the current task.
- Usage with Python 3.6 and 3.7 is deprecated. These versions will not be supported by the next major release.

## [0.7.2] - 2024-06-23

### Fixed

- Support pip 24.1.

## [0.7.1] - 2024-06-14

### Fixed

- `enable_ewokstest_category` failed when called more than once.
- `qtapp` session fixture for tests failed when called more than once.

## [0.7.0] - 2024-06-05

### Changed

- Task creation exception error log when non created by an upstream signal.
- Remove deprecated `pkg_resources` usage.
- Remove support for runtime installation of Orange add-ons and replace with
  a hidden "ewokstest" widget category. This category is visible only when
  the canvas is launched with `ewoks-canvas --with-examples`.
- Provide Orange configuration of all supported Orange forks.
- Declare `orangecontrib` as an implicit namespace package.
- Provide a helper function `widget_discovery` to be used in add-ons that
  need to avoid using `pkg_resources`.

### Fixed

- `OWEwoksBaseWidget.get_default_input_value` and `OWEwoksBaseWidget.get_dynamic_input_value`.
- `OrangeCanvasHandler.wait_widgets` should raise task exception only when the workflow is finished.

## [0.6.0] - 2024-02-20

### Added

- Add `DataViewer` widget to browse and display data from files supported by silx (like silx view).

### Changed

- Fix error handling for testing widgets and Qt workflows.
- Oasys fork: fix name mapping for downstream widget clearing.

## [0.5.0] - 2024-02-06

### Changed

- Make post task execution (output changed callbacks and downstream propagation)
  equivalent for all widget types (no thread, single thread, multi thread).

## [0.4.0] - 2023-12-15

### Added

- Allow hiding inputs/outputs from the canvas when making a link.

### Fixed

- Exclude buggy orange project release from the requirement.

## [0.3.1] - 2023-10-03

### Changed

- Remove prints.

## [0.3.0] - 2023-10-03

### Changed

- `OWWidget` homogenize getting/setting values of default and dynamic inputs.

## [0.2.1] - 2023-09-18

### Fixed

- `ParameterForm` callback on value change was not called when selecting files/datasets from a dialog.

### Changed

- PyQt5 is only install with the `full` option.
- `OWWidget.get_default_input_values` accepts defaults.

## [0.1.8] - 2023-05-15

### Changed

- Remove deprecated ewokscore Task properties.

## [0.1.7] - 2023-03-31

### Changed

- Add more test utilities for projects to provide ewoks widgets.

## [0.1.6] - 2023-03-23

### Fixed

- Fix graph comparison tests.

## [0.1.5] - 2023-03-17

### Changed

- Add demo widgets.
- Fix ewoks_to_ows for orange-canvas-core>=0.1.30.

## [0.1.4] - 2023-03-09

### Changed

- Use new "engine" argument instead of the deprecated "binding".

## [0.1.3] - 2023-02-21

### Added

- Support widgets that do not derive from OWEwoksBaseWidget for headless execution.

## [0.1.2] - 2023-01-27

### Added

- OWEwoksBaseWidget: get default inputs with or without missing values.

### Fixed

- ParameterForm: fix serialization for sequences.

## [0.1.1] - 2023-01-26

### Added

- Test utility to run an ewoks task with or without the widget.

## [0.1.0] - 2022-12-03

### Added

- Bases classes for Orange Widgets natively compliant with ewoks.
  - OWEwoksWidgetNoThread: will execute ewoks task directly.
  - OWEwoksWidgetOneThread: will execute ewoks task on a thread. Refuse job is the thread is already running.
  - OWEwoksWidgetOneThreadPerRun: create one new thread per ewoks task to be execute.
  - OWEwoksWidgetWithTaskStack: has one thread to execute ewoks tasks. Work as a FIFO stack.
- Convert Orange workflows to Ewoks and vice versa.
- On-the-fly Orange add-on registration.
- Add-on setup tools.

[unreleased]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v2.0.1...HEAD
[2.0.1]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v2.0.0...v2.0.1
[2.0.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v1.2.0...v2.0.0
[1.2.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v1.1.0...v1.2.0
[1.1.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v1.0.0...v1.1.0
[1.0.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.9.0...v1.0.0
[0.9.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.8.0...v0.9.0
[0.8.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.7.2...v0.8.0
[0.7.2]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.7.1...v0.7.2
[0.7.1]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.7.0...v0.7.1
[0.7.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.6.0...v0.7.0
[0.6.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.5.0...v0.6.0
[0.5.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.4.0...v0.5.0
[0.4.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.3.1...v0.4.0
[0.3.1]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.3.0...v0.3.1
[0.3.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.2.1...v0.3.0
[0.2.1]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.2.0...v0.2.1
[0.2.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.8...v0.2.0
[0.1.8]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.7...v0.1.8
[0.1.7]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.6...v0.1.7
[0.1.6]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.5...v0.1.6
[0.1.5]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.4...v0.1.5
[0.1.4]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.3...v0.1.4
[0.1.3]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.2...v0.1.3
[0.1.2]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.1...v0.1.2
[0.1.1]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/compare/v0.1.0...v0.1.1
[0.1.0]: https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/-/tags/v0.1.0
