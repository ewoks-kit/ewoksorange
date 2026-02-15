# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- 

## [4.0.0rc1] - 2026-02-11

### Fixed

- `OWEwoksBaseWidget.get_default_input_value`: also take into account values defined in the Pydantic model.
- `OWEwoksBaseWidget._get_pydantic_model_default_values`: ignore values marked as `invalid_data`.

## [4.0.0rc0] - 2026-02-09

### Changed

- Prepare the `4.0.0` prerelease line (`rc0`).
- No additional functional changes compared to `3.3.1`.

## [3.3.1] - 2026-01-28 [YANKED]

### Fixed

- Handle ewoksndreg pydantic mode use case (`Sequence`, `Dict`)

## [3.3.0] - 2026-01-22 [YANKED]

### Changed

- Improve pydantic model handling.
  - Default values defined in a task `InputModel` are now taken into account [PR 264](https://github.com/ewoks-kit/ewoksorange/pull/264).
  - Link between Orange `Input` and ewoks task Pydantic models now fully handle `Union` and `Optional` types [PR 268](https://github.com/ewoks-kit/ewoksorange/pull/268)

## [3.2.1] - 2026-01-16

### Fixed

- Fix a bug where Orange signals were not available as inputs of the `OWEwoksWidget` subclass instances.

## [3.2.0] - 2025-12-30

### Changed

- Progress bar : Adapt the code to make it available without `Orange3` or `OASYS` dependency. Only `orange-widget-base` is necessary.

### Fixed

- Progress bar : Exception raised at the initialization of a task with a progress bar.

## [3.1.1] - 2025-12-30

### Fixed

- `SignalManagerWithOutputTracking`: keep only weak reference to widgets.
- Adapt to `ewokscore>=4` test utility API change.

## [3.1.0] - 2025-11-24

## Added

- `block_signals`: accept multiple widgets.

## [3.0.2] - 2025-11-21

- Add the deprecated `ewoksorange.bindings.owwidgets.invalid_data`.
- Add the deprecated `ewoksorange.bindings.qtapp.QtEvent`.

## [3.0.1] - 2025-11-21

## Fixed

- Add the deprecated `ewoksorange.gui.parameterform.block_signals`.

## [3.0.0] - 2025-11-21

### Deprecated

- Module `ewoksorange.canvas`.
- Module `ewoksorange.registration`.
- All `ewoksorange.bindings.*` modules.
- All `ewoksorange.canvas.*` modules.

## Removed

- Module `ewoksorange.oasys_patch`.
- Module `ewoksorange.bindings.owsignals`.

## Fixed

- `ewoksorange.engine.OrangeWorkflowEngine` can be instantiated without importing Qt.

## Changed

- `OWEwoksBaseWidget.get_dynamic_input_value`: return the actual value, not the wrapper `Variable`.
- `OWEwoksBaseWidget.get_dynamic_input`: return the actual value, not the wrapper `Variable`.
- `signals`: Enhance creation of Orange Input and Output from deducing signal value data type
  from the Ewoks Task's models.

## Added

- `ewoksorange.gui.orange_utils.signals.Input` and `ewoksorange.gui.orange_utils.signals.Output`
  should be used to modify the Orange name of the signal. They accept an `ewoksname` argument
  which defaults to the attribute name in the `Inputs` and `Outputs` container classes.

## [2.1.0] - 2025-10-23

### Added

- `orangecontrib.ewoksnowidget.global_cleanup_ewoksnowidget` removes all dynamically generated widget
  declarations from the `orangecontrib.ewoksnowidget` Orange add-on. Used by pytest fixture `qtapp`.

### Fixed

- Widget classes from Ewoks tasks without Orange widget are now generated dynamically when
  opening or executing `.ows` files.

## [2.0.1] - 2025-09-22

### Fixed

- Fix type mismatch when linking `EwoksOrange` widgets to native Orange widgets
  [!319](https://github.com/ewoks-kit/ewoksorange/pull/319)
- Fix error when converting an Ewoks workflow containing native Orange widgets to OWS format
  (with `ewoks_to_ows`) [#59](https://github.com/ewoks-kit/ewoksorange/issues/59)

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

- `OWEwoksBaseWidget`: get default inputs with or without missing values.

### Fixed

- `ParameterForm`: fix serialization for sequences.

## [0.1.1] - 2023-01-26

### Added

- Test utility to run an ewoks task with or without the widget.

## [0.1.0] - 2022-12-03

### Added

- Bases classes for Orange Widgets natively compliant with ewoks.
  - `OWEwoksWidgetNoThread`: will execute ewoks task directly.
  - `OWEwoksWidgetOneThread`: will execute ewoks task on a thread. Refuse job is the thread is already running.
  - `OWEwoksWidgetOneThreadPerRun`: create one new thread per ewoks task to be execute.
  - `OWEwoksWidgetWithTaskStack`: has one thread to execute ewoks tasks. Work as a FIFO stack.
- Convert Orange workflows to Ewoks and vice versa.
- On-the-fly Orange add-on registration.
- Add-on setup tools.

[unreleased]: https://github.com/ewoks-kit/ewoksorange/compare/v4.0.0rc1...HEAD
[4.0.0rc1]: https://github.com/ewoks-kit/ewoksorange/compare/v4.0.0rc0...v4.0.0rc1
[4.0.0rc0]: https://github.com/ewoks-kit/ewoksorange/compare/v3.3.1...v4.0.0rc0
[3.3.1]: https://github.com/ewoks-kit/ewoksorange/compare/v3.3.0...v3.3.1
[3.3.0]: https://github.com/ewoks-kit/ewoksorange/compare/v3.2.1...v3.3.0
[3.2.1]: https://github.com/ewoks-kit/ewoksorange/compare/v3.2.0...v3.2.1
[3.2.0]: https://github.com/ewoks-kit/ewoksorange/compare/v3.1.1...v3.2.0
[3.1.1]: https://github.com/ewoks-kit/ewoksorange/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/ewoks-kit/ewoksorange/compare/v3.0.2...v3.1.0
[3.0.2]: https://github.com/ewoks-kit/ewoksorange/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/ewoks-kit/ewoksorange/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/ewoks-kit/ewoksorange/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/ewoks-kit/ewoksorange/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/ewoks-kit/ewoksorange/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/ewoks-kit/ewoksorange/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/ewoks-kit/ewoksorange/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/ewoks-kit/ewoksorange/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/ewoks-kit/ewoksorange/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/ewoks-kit/ewoksorange/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/ewoks-kit/ewoksorange/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/ewoks-kit/ewoksorange/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.8...v0.2.0
[0.1.8]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ewoks-kit/ewoksorange/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ewoks-kit/ewoksorange/releases/tag/v0.1.0
