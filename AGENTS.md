# AGENTS.md

## Project map (read this first)
- This repo has **two distinct code paths**:
  - `library/enviroplus/`: publishable hardware library (`gas.py`, `noise.py`) with tests in `library/tests/`.
  - top-level app (`main.py` + `helper/`): a personal/home automation scheduler for Hue + Kasa + Enviro display.
- `examples/` are standalone scripts showing direct sensor/network integrations (MQTT, Luftdaten, LCD dashboards); they are not the same architecture as `main.py`.

## Runtime architecture and data flow
- Entry point for automation mode is `main.py` -> `helper/scheduler.py:MyScheduler`.
- `MyScheduler` wires three adapters: `EnviroWrapper` (`helper/enviro_helper.py`), `HueWrapper` (`helper/phillips_hue_wrapper.py`), and `KasaWrapper` (`helper/kasa_helper.py`).
- Heater control loop (`_manage_heater`) reads compensated temperature from `EnviroWrapper.get_temperature()` and switches Kasa device alias `Heater` using duty-cycle counters (`heater_on_for`, `heater_off_for`).
- Lighting loop (`_manage_lights`) delegates to `HueWrapper.do_whatever()`, which selects profiles by weekday/hour and uses global day state from `helper/colour_helper.py`.
- Sun events are recomputed daily via Astral (`_get_sunset_sunrise`), then translated into APScheduler triggers; sunrise/sunset interpolation updates `colour_helper.day_factor`.

## Developer workflows that matter here
- Core install/uninstall flows are shell scripts, not pip-only:
  - `install.sh` parses `library/setup.cfg` `[pimoroni]` to install apt deps and mutate `/boot/config.txt`.
  - `uninstall.sh` reverses serial/config changes and uninstalls package.
- Packaging + consistency checks live in `Makefile`:
  - `make check` verifies whitespace/line endings and version sync across `library/setup.cfg`, `library/enviroplus/__init__.py`, and `library/CHANGELOG.txt`.
  - `make python-dist` builds wheel + sdist from `library/`.
- Test flow is scoped to `library/`:
  - `cd library && tox -vv` (as in `.travis.yml`).
  - `library/tests/conftest.py` mocks hardware modules by injecting into `sys.modules`.

## Project-specific coding patterns (follow these)
- Hardware imports often use compatibility fallback patterns (e.g., `try: from ltr559 import LTR559 ... except ImportError: import ltr559` in `helper/enviro_helper.py` and examples).
- Several modules rely on **module-level mutable state**:
  - `enviroplus/gas.py` (`_is_setup`, `_adc_enabled`, `_adc_gain`),
  - `helper/colour_helper.py` (`day_factor`, `brightness`, `current_theme`).
  Keep this in mind when adding tests or parallel flows.
- CPU temperature compensation via `vcgencmd measure_temp` is a repeated pattern (`helper/enviro_helper.py`, `examples/all-in-one.py`, `examples/mqtt-all.py`).
- Device discovery is name-driven and implicit (`KasaWrapper.get_device('Heater')`; Hue light names hardcoded in `HueWrapper` defaults).

## Integration points and external services
- Hardware libs: `bme280`, `ltr559`, `ST7735`, `pms5003`, `ads1015`, `RPi.GPIO`, `sounddevice`.
- Network/home integrations: `phue` (Hue bridge), `pyHS100` (TP-Link Kasa), OpenWeatherMap (`helper/weather_helper.py`), MQTT (`examples/mqtt-all.py`), Luftdaten (`examples/luftdaten.py`).
- Config is minimal and file-based: `helper/config_helper.py` expects `config.json` in current working directory.

## Safe change strategy for agents
- Decide first whether your change belongs to `library/` (reusable package) or top-level `helper/` app logic.
- For library changes, update/add tests in `library/tests/` using the existing mock-fixture style.
- For scheduler/home automation changes, preserve trigger cadence and avoid blocking calls inside APScheduler jobs.
- If you change package version behavior, keep `library/setup.cfg`, `library/enviroplus/__init__.py`, and `library/CHANGELOG.txt` consistent (`make check` enforces this).

