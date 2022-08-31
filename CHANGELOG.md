# CHANGELOG.md

## 0.1.0 (unreleased)

Added:
  - Bases classes for Orange Widgets natively compliant with ewoks
    - OWEwoksWidgetNoThread: will execute ewoks task directly
    - OWEwoksWidgetOneThread: will execute ewoks task on a thread. Refuse job is the thread is already running
    - OWEwoksWidgetOneThreadPerRun: create one new thread per ewoks task to be execute
    - OWEwoksWidgetWithTaskStack: has one thread to execute ewoks tasks. Work as a FIFO stack
  - Convert Orange workflows to Ewoks and vice versa
  - On-the-fly Orange add-on registration
  - Add-on setup tools
