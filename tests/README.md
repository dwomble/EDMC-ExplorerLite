# EDMC Plugin Test Harness

This is a unit testing tool for EDMC plugins that mocks up EDMC functionality in order to run `pytest` unit tests in a headless environment without modifying the plugin.

## Features

* Journal event replay, with customization
* Mock state handling
* Mock EDMC config
* Mock ED logging
* Mock i10n translation
* Mock CAPI event handling
* Mock EDMC Overlay
* Mock HotKeys
* Mock (or live) HTTPS requests
* Mock dashboard event replay

## Getting Started

1. Extract the code into a `tests` folder within your plugin directory
1. Create a `venv` and install the dependencies
1. Edit `test_conformance.py` to match your plugin's startup and configuration needs
1. Run the conformance tests to confirm your plugin initializes with the harness
1. Start writing and running tests

Whlie `test_conformance.py` in combination with the `load.py` acts as a set of worked examples for running unit tests if, like me, you work best from example the following plugins use the harness:

* [Neutron Dancer](https://github.com/dwomble/EDMC-NeutronDancer)
* [BGS-Tally](https://github.com/aussig/BGS-Tally/tree/feature/Issue-454/test-harness)
* [EDMC Mining Analytics](https://github.com/SweetJonnySauce/EDMC-Mining-Analytics)

## Components

### Harness

The `harness.py` does the initialization of EDMC. It uses some actual EDMC modules and some mock modules from the `edmc` folder.

The harness provides a mock edmc config object loaded from `config/edmc_config.ini` and a journal event replay capability.

Journal records can be loaded from a json or log file using `load_events` and then called individually with `fire_event` or in sequence with `play_sequence`. The journal record processing supports "f" strings and time deltas so that they can be customized/maintained without continual editing.

```python
load_events(source:str, **kwargs) -> dict[str, list[dict]]:
fire_event(event:dict, state:dict = {}) -> None:
play_sequence(name:str, delay:float = 0.5, state:dict = {}) -> None:
```

### Test files

Test files and data live in the `/tests` folder which is where your plugin will look for, and write, files by default. This makes it easy to use test-specific data files and avoids live files being overwritten during testing.

Unit tests exist in files that start `test_`. These import the test harness, initialize it, and define a class (or classes) with functions that pytest will run.

The initialization may vary depending on the tests and the plugin. It typically loads the plugin and then calls the plugin `plugin_start3` and `plugin_app` functions just as EDMC would.

Prior to loading a plugin it may be desirable to copy standardized versions of any save files to ensure consistent initial conditions.

It will often load a set of journal events that the test series will require and registers the plugin's `journal_entry` function as the recipient of those events when triggered.

### Writing tests

At their most basic a test is just a matter of calling a plugin function and verifying the result or that the outcome is as expected.

Testing can get quite sophisticated. The journal replay can run through sequences of hundreds of journal events; the mock requests object can respond to and return test data; and pytest's monkeypatch can intercept individual functions to monitor/alter plugin features..

### Running tests

Setup a python virtual environment and install `pytest`. You can then run `pytest` from the command line or from within an IDE such as VS Code.

### Debugging tests

If you install the python debugger you can run the tests with the debugger enabling breakpoints, inspecting variables, and stepping through code. With an IDE such as VS Code tests can be directly run using the python debugger to step through sections.

### Test coverage

`pytest-cov` enables code coverage. In VS Code which lines have, and have not, been executed are highlighted.

```
---------- coverage: platform darwin, python 3.14.3-final-0 ----------
Name                        Stmts   Miss Branch BrPart  Cover
-------------------------------------------------------------
load.py                        75      6      4      0    90%
tests/__init__.py               2      0      0      0   100%
tests/edmc/EDMCLogging.py     200     69     68     23    60%
tests/edmc/TkScheduler.py     105     43     26      8    53%
tests/edmc/edmc_data.py        94      0      2      0   100%
tests/edmc/mocks.py           268     43     84     12    82%
tests/edmc/monitor.py        1284    979    622    114    23%
tests/edmc/requests.py        174     53     62     16    63%
tests/edmc/util_ships.py       10      5      2      0    42%
tests/harness.py              330     76    132     38    72%
tests/test_conformance.py     170      9      8      3    93%
utils/debug.py                 24     13      2      0    42%
utils/updater.py              100     67     22      1    31%
-------------------------------------------------------------
TOTAL                        2836   1363   1034    215    47%

======================== 25 passed, 5 warnings in 3.57s ========================
Finished running tests!
```

## Directories

The test environment is entirely contained within the `/tests` directory.

### /tests/config

This folder is used for test configuration files including `edmc_config.json` that is used to store EDMC config items.

### /tests/journal_config

This folder is used for test journal files including journal event files that can be replayed and test configuration files for the "special" `.json` files ED creates (`Cargo.json`, `Market.json`, `Status.json` etc.)

Most of the "special" files are replacements for the journal events. For example, the journal `Market` event is empty except for station information. All the details are written to `Market.json`. This means the harness can't populate them, hence the need to copy pre-defined versions for tests that require them. Cargo is a slight exception in that the harness will update `Cargo.json` based on cargo transfer events.

### /tests/edmc

This contains live and mock edmc modules used to emulate EDMC so the plugin can run standalone from EDMC.

### Others

Other folders created by the plugin for saving data will be created in `/tests` to avoid overwriting or corrupting files in the main plugin directory.

## Tips and Tricks

### Plugin config

It's often desirable to use a consistent configuration for testing. This can be achieved by storing a standard version in `config` and copying it to wherever your plugin looks for it prior to startup e.g.

```python
   shutil.copy(Path(__file__).parent / "config" / "colonisation_init.json",  Path(__file__).parent / "otherdata" / "colonisation.json")
```

### Mock EDMC Config

The harness mocks the EDMC config and loads `config/config.toml` as an initial config. If you create a `config/config_init.toml` the harness will start each test by copying  this file for use.

If you want to use an entirely different config for a specific test call `load_edmc_config(file)`.

### Mock HTTP Requests

By default these are mocked and what they return can be set by using `queue_response`:

```python
queue_response(method:str, response: MockResponse, url:str|None = None, sticky:bool = False)
```

* `sticky` indicates the response should be for all matching requests, otherwise it's returned just once
* `url` will match only requests with the appropriate method and matching url. If left blank any request will be matched regardless of url.

For example:

```python
from datetime import datetime, UTC
from tests.edmc.requests import queue_response, MockResponse

# A mock response for the galaxy tick query
queue_response('get',
               MockResponse(200,
                            url='http://tick.infomancer.uk/galtick.json',
                            json_data={"lastGalaxyTick":f"{datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}"}),
                            sticky=True)
```

Requests can be made *live* in any of the following ways:

1. Initializing the harness object with the parameter `live_requests=True`, good for an entire suite of tests
1. Adding the decorator `@pytest.mark.live_requests` to a test function, good for a single test
1. Calling `set_requests_mode(True)` on the harness, good for changing the mode partway through a test

### Mock Journal Events

A journal event can be mocked simply by calling `journal_entry` in your plugin but the test harness provides a more sophisticated solution that handles a lot of the work for you.

It works as follows:

1. Sequences of journal events are loaded from a `json` or `log` file using `load_events`
1. The plugin's journal handling function is registered with the harness using `register_journal_handler`
1. A test can then fire individual events with `fire_event` or replay an entire sequence with `play_sequence`

Events fired this way will be given a current timestamp if there is no `timestamp` field, and the event file can contain `f` strings enabling variable data or specific timing.

Customisation options include:

* `now:` or `delta:<int>` will be replaced by the current datetime or the current datetime plus a number of seconds respectively
* `params.<param>` any named parameter passed to the `load_events` function.
* any variable in the harness. eg. `harness.myplugin.somevar`

For example:

```json
{
    "startup": [
        { "event":"Startup", "System":"Sol", "Body":"Earth", "BodyID":3 }
    ],
   "carrier_events": [
        { "timestamp": "delta:-900", "event":"CarrierJumpRequest", "CarrierType":"FleetCarrier", "CarrierID":"{self.plugin.fleet_carrier.overview.get(\"carrier_id\")}", "SystemName":"Aparui", "Body":"Aparui 1", "SystemAddress":1956293399241, "BodyID":"{params.BodyId}", "DepartureTime":"delta:-1"},
        { "event":"CarrierLocation", "CarrierType":"FleetCarrier", "CarrierID":"{self.plugin.fleet_carrier.overview.get(\"carrier_id\")}", "StarSystem":"Aparui", "SystemAddress":1956293399241, "BodyID":"{params.BodyId}" }
   ]
}
```

Two file formats are supported.

1. `.json` data files. These should be a dictionary of lists where the dictionary keys are the action to run and the list is a sequence of log entries.

1. ED journal `.log` files. These can be taken directly from the ED journal folder. All the entries will be loaded and given the action name "default".

### Mock Dashboard Events

It works as follows:

1. Register your dashboard event handling function with the harness using `register_dashoard_handler`
1. A test can then mimic a dashboard event by calling `fire_dashboard_event`

For example:

```python
    harness.register_dashboard_handler(dashboard_entry)
    harness.fire_dashboard_event({"GuiFocus": edmc_data.GuiFocusGalaxyMap})

    harness.fire_dashboard_event({"Flags2": edmc_data.Flags2OnFoot | edmc_data.Flags2LowOxygen})
```

### Testing with and without Overlay

The test harness can be initialized with legacy overlay, modern overlay, or no overlay enabled. This is achieved by passing an `overlay` parameter containing `Modern`, `Legacy` or `None` to the `TestHarness` object making it possible to test how your code works with and without an overlay plugin installed.

Similarly to live and mock HTTP requests overlay can be enabled or disabled in multiple ways:

1. Initializing the harness object with the parameter `overlay`, good for an entire suite of tests `test_harness = TestHarness(overlay='Modern')`
1. Adding the decorator `@pytest.mark.overlay` to a test function, good for a single test `@pytest.mark.overlay('None')`
