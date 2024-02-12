# CHANGELOG.md

## 0.7.0 (unreleased)

## 0.6.0

New Features:

- Add `DataViewer` widget to browse and display data from files supported by silx (like silx view)

Changes:

- Fix error handling for testing widgets and Qt workflows
- Oasys fork: fix name mapping for downstream widget clearing

## 0.5.0

Changes:

- Make post task execution (output changed callbacks and downstream propagation)
  equivalent for all widget types (no thread, single thread, multi thread).

## 0.4.0

New Features:

- Allow hiding inputs/outputs from the canvas when making a link

Bug fixes:

- Exclude buggy orange project release from the requirement

## 0.3.1

Changes:

- remove prints

## 0.3.0

Changes:

- `OWWidget` homogenize getting/setting values of default and dynamic inputs

## 0.2.1

Bug fixes:

- `ParameterForm` callback on value change was not called when selecting files/datasets from a dialog

## 0.2.0

Changes:

- PyQt5 is only install with the `full` option
- `OWWidget.get_default_input_values` accepts defaults

## 0.1.8

Changes:

- remove deprecated ewokscore Task properties

## 0.1.7

Changes:

- add more test utilities for projects to provide ewoks widgets

## 0.1.6

Bug fixes:

- fix graph comparison tests

## 0.1.5

Changes:

- add demo widgets
- fix ewoks_to_ows for orange-canvas-core>=0.1.30

## 0.1.4

Changes:

- use new "engine" argument instead of the deprecated "binding"

## 0.1.3

New features:

- Support widgets that do not derive from OWEwoksBaseWidget for headless execution

## 0.1.2

Bug fixes:

- ParameterForm: fix serialization for sequences

New features:

- OWEwoksBaseWidget: get default inputs with or without missing values

## 0.1.1

New features:

- Test utility to run an ewoks task with or without the widget

## 0.1.0

New features:

- Bases classes for Orange Widgets natively compliant with ewoks
  - OWEwoksWidgetNoThread: will execute ewoks task directly
  - OWEwoksWidgetOneThread: will execute ewoks task on a thread. Refuse job is the thread is already running
  - OWEwoksWidgetOneThreadPerRun: create one new thread per ewoks task to be execute
  - OWEwoksWidgetWithTaskStack: has one thread to execute ewoks tasks. Work as a FIFO stack
- Convert Orange workflows to Ewoks and vice versa
- On-the-fly Orange add-on registration
- Add-on setup tools
