# Development

This page describes how to run the plugin from this checkout inside QGIS 3
(Qt5) or QGIS 4 (Qt6). The plugin supports both.

The plugin is run in a **separate QGIS profile**, `geosearch-dev`. A released
Geosearch DK installed in your `default` profile is not touched.

## macOS: `make dev`

```sh
make dev            # QGIS 4 (default)
make dev QGIS=3     # QGIS 3
```

`make dev`:

1. creates the profile `geosearch-dev` if it does not exist
   (`~/Library/Application Support/QGIS/QGIS<n>/profiles/geosearch-dev`),
   and enables the plugin in a new profile;
2. symlinks `src/geosearch_dk` into the profile's `python/plugins/` folder;
3. starts QGIS with `open -n -a <QGIS.app> --args --profile geosearch-dev`.

QGIS remembers `--profile` as the last used profile. `make` restores the
previous value when QGIS quits, so starting QGIS normally still opens your
`default` profile.

`make help` lists all targets and prints the current values of the variables.

| Variable   | Default | Meaning |
|------------|---------|---------|
| `QGIS`     | `4`     | QGIS major version, `3` or `4` |
| `QGIS_APP` | newest `QGIS*.app` in `/Applications` or `~/Applications` with version `$(QGIS).x` | the QGIS app to start |
| `PROFILE`  | `geosearch-dev` | QGIS profile name |

Other targets:

- `make dev-link`: only create the profile and the symlink (does not start QGIS)
- `make dev-unlink`: remove the symlink (the profile is kept)
- `make visual`: run the visual run, see below
- `make macos-patch-qgis`: see [QGIS 4 crashes at startup on macOS 27](#qgis-4-crashes-at-startup-on-macos-27)

To remove the dev profile completely, delete its folder.

## Linux

`make dev` works on Linux as well. The profile is created in
`~/.local/share/QGIS/QGIS<n>/profiles/geosearch-dev`, and QGIS is started with
`qgis --profile geosearch-dev`. If QGIS 3 and 4 are installed side by side, give
the binary explicitly:

```sh
make dev QGIS=3 QGIS_BIN=/usr/bin/qgis
make dev QGIS=4 QGIS_BIN=/opt/qgis4/bin/qgis
```

By hand:

```sh
P=~/.local/share/QGIS/QGIS4/profiles/geosearch-dev/python/plugins   # QGIS3 for QGIS 3
mkdir -p "$P"
ln -sfn "$PWD/src/geosearch_dk" "$P/geosearch_dk"
qgis --profile geosearch-dev
```

Enable *Geosearch DK* under *Plugins > Manage and Install Plugins > Installed*
the first time.

## Windows

There is no `make dev` for Windows. Do the same steps by hand in `cmd.exe`
(replace `QGIS4` with `QGIS3` for QGIS 3):

```bat
set P=%APPDATA%\QGIS\QGIS4\profiles\geosearch-dev\python\plugins
mkdir "%P%"
mklink /J "%P%\geosearch_dk" "C:\path\to\qgis-geosearch\src\geosearch_dk"
```

`mklink /J` creates a directory junction, which does not need an administrator
shell. (`mklink /D` creates a real symlink, but needs an administrator shell or
Developer Mode.)

Start QGIS with the profile. Use the command of the QGIS Start menu shortcut
(right-click > *More* > *Open file location*, then *Properties > Target*) and
add `--profile geosearch-dev`, for example:

```bat
"C:\Program Files\QGIS 3.44.8\bin\qgis-ltr-bin.exe" --profile geosearch-dev
"C:\OSGeo4W\bin\qgis.bat" --profile geosearch-dev
```

A copy of the shortcut with `--profile geosearch-dev` added to *Target* is
handy.

Enable *Geosearch DK* under *Plugins > Manage and Install Plugins > Installed*
the first time. To remove the link, run `rmdir "%P%\geosearch_dk"`; this
removes only the junction, not the source files.

## Fast reloads with Plugin Reloader

Because the profile uses a symlink, QGIS runs the code in the checkout
directly. Instead of restarting QGIS after each change, use the
[Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/) plugin:

1. In the `geosearch-dev` profile, install *Plugin Reloader* from
   *Plugins > Manage and Install Plugins*.
2. Open the menu of the Plugin Reloader toolbar button, choose *Configure*,
   and select `geosearch_dk`.
3. After a change, press **Ctrl+F5** (macOS: **Cmd+F5**) or click the toolbar
   button. The plugin is unloaded and loaded again from the checkout.

Restart QGIS when reloading is not enough, for example after changing
`metadata.txt`.

## Visual run

`tests/manual/visual_run.py` drives the real plugin UI. For each case in the
case catalogue (`tests/cases.yaml`, see below) it:

1. types the input into the plugin's search box, key by key;
2. waits for the result popup and saves a screenshot of it;
3. moves to the expected hit with the arrow keys and presses Enter;
4. waits for the marker or outline on the map and saves an image of the map.

It only uses widgets (the dock *Geosearch DK*, its search field and the
popup), not plugin internals. The same script therefore works against the
GSearch plugin and the Bifrost version.

The result is `out/report.html`: a table with the status of every case, and
per case the GSearch baseline, the popup and the map. Open it in a browser.
`out/report.json` has the same data.

### From a shell

```sh
make visual                      # QGIS 4, all cases
make visual QGIS=3               # QGIS 3
make visual ONLY=adr-vangebovej-71,kom-koege
make visual CASES=tests/manual/sample_cases.yaml OUT=out/sample
```

`make visual` starts QGIS with the `geosearch-dev` profile, runs the script,
quits QGIS and prints the result of each case. The QGIS log is in
`out/qgis.log`. Do not use the mouse or keyboard while it runs: the script
sends key presses to the search box.

Use `VISUAL_ARGS` for other options, e.g.
`make visual VISUAL_ARGS="--basemap none --no-filters"`.

### From the QGIS Python console

Start QGIS with `make dev`, open *Plugins > Python Console*, and run:

```python
import runpy; runpy.run_path("/path/to/qgis-geosearch/tests/manual/visual_run.py", run_name="__main__")
```

With options:

```python
import sys; sys.path.insert(0, "/path/to/qgis-geosearch/tests/manual")
import visual_run
visual_run.main(["--only", "adr-vangebovej-71", "--out", "/tmp/geosearch-out"])
visual_run.main(["--help"])     # all options
```

### Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--cases` | `tests/cases.yaml`, or `tests/manual/sample_cases.yaml` if it does not exist | case catalogue |
| `--out` | `out` | output folder |
| `--fixtures` | `tests/fixtures/gsearch` | recorded GSearch responses (`<id>.json`), shown as the baseline |
| `--only` | | comma separated case ids |
| `--basemap` | `auto` | `auto` adds a temporary OpenStreetMap layer when the project has no layers; `osm` always; `none` never |
| `--no-filters` | | do not apply the case's `types` and `kommuner` to the plugin settings |
| `--quit` | | quit QGIS when done (used by `make visual`) |

There are also timeouts (`--popup-timeout`, `--geometry-timeout`,
`--render-timeout`, ...). See `--help`.

### Cases and results

The case catalogue is a YAML list:

```yaml
- id: adr-vangebovej-71
  story: "Brugeren vil finde Vangebovej 71 ..."
  input: "Vangebovej 71"         # exactly what is typed
  types: [adr]                   # adr ste pos mat kom ops pol reg; omit = all
  kommuner: []                   # optional kommunefilter codes
  expect: { text: "...", within: 3, geometry: point }
  known_gap: 3                   # optional issue number
  notes: ""
```

`tests/manual/sample_cases.yaml` is a small example.

Unless `--no-filters` is given, the case's `types` and `kommuner` are written
to the plugin settings before the case. Your settings are restored when the
run ends, also when it fails. The project's CRS and extent are restored too.

Status per case:

- **PASS**: `expect.text` is among the first `within` hits, and selecting it
  showed a geometry of the expected kind on the map.
- **FAIL**: the hit was not found, or no geometry (or the wrong kind) was shown.
- **ERROR**: the script failed, e.g. the popup did not appear.
- **KNOWN GAP**: the case failed, but has `known_gap` (an open issue).
- **PASS (KNOWN GAP)**: the case passed although it has `known_gap`. The issue
  may be fixed.

## QGIS 4 crashes at startup on macOS 27

QGIS 4.2.3 crashes right after it starts on macOS 27.2 (`EXC_BREAKPOINT` in
`CGImageCreate`, called from `QgsMacNative::setIconPath`). It crashes with any
profile, also without this plugin. QGIS 3.44 is not affected.

The crash happens while QGIS sets its Dock icon. A copy of the app with the
colour profile removed from that icon starts normally:

```sh
make macos-patch-qgis           # creates ~/Applications/QGIS-final-4_2_3-patched.app
make dev                        # the "-patched" copy is chosen automatically
```

`scripts/macos_patch_qgis.py` copies the app (an APFS clone, so it uses
almost no disk space), removes the `sRGB`/`iCCP`/`gAMA`/`cHRM` chunks from
`qgis-icon-macos.png` and signs the copy ad hoc. The original app is not
changed. Delete the copy when a fixed QGIS is released.

On macOS, start QGIS 4 through `open` (as `make` does). Starting the binary
inside the app directly also crashes.
