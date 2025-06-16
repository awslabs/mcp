# Datazone_mcp_server

This is a [BrazilPython 3](https://w.amazon.com/bin/view/BrazilPython3/) Python project.

## Choosing your Python version

This is a change from BrazilPython 2; in BP3 you choose your Python version
using branches in your versionset. By default the version is inherited from
`live` (which as of this writing is CPython 3.4, but that is subject to change).
The actual version can be chosen using the [singleton interpreter process](https://w.amazon.com/index.php/BuilderTools/LiveCuration/SingletonInterpreters).

The short version of that is:

### Using CPython3

Build the following package major version/branches into your versionset:

* `Python-`**`default`** : `live`
* `CPython3-`**`default`** : `live`


This will cause `bin/python` to run `python3.7` as of 03/2020 but over time this
version will be kept up to date with the current best practice interpreters.

Your default interpreter is always enabled as a build target for python packages in your version set.

You should build the `no` branches for all interpreters into your versionset as
well, since the runtime interpreter will always build:

* `CPython27-`**`build`** : `no`
* `CPython34-`**`build`** : `no`
* `CPython36-`**`build`** : `no`
* `CPython37-`**`build`** : `no`
* `CPython38-`**`build`** : `no`
* `Jython27-`**`build`** : `no`

(Note that many of these are off in `live` already)

### Using a newer version of CPython3

If you need a special version of CPython (say you want to be on the cutting edge and use 3.9):

* `Python-`**`default`** : `live`
* `CPython3-`**`default`** : `CPython39`

This will cause `bin/python` to run `python3.9`

### Using CPython2 2.7 or Jython

**Don't**

## Building

Modifying the build logic of this package just requires overriding parts of the
setuptools process. The entry point is either the `release`, `build`, `test`, or
`doc` commands, all of which are implemented as setuptools commands in
the [BrazilPython-Base-3.0](https://code.amazon.com/packages/BrazilPython-Base/releases)
package.

### Restricting what interpreter your package will attempt to build for

If you want to restrict the set of Python versions a package builds for, first answer these questions

1. Do you need to build into version sets that may have more than the default interpreter enabled (such as live)?
2. Are there versions that are commonly enabled in those version sets that would be difficult to support?
  1. Example: Python 3.6 is currently enabled in `live` but if you want to publish a package to live that is only valid for Python 3.7+ consumers, then you may want to filter on it
  2. Counter example: while Jython is a valid build target, it has largely been deprecated from use and is not enabled in the vast majority of version sets, so filtering on it will add almost entirely unused cruft to your package when you may have no Jython-enabled consumers
3. Should the build fail if no valid interpreter is enabled?

If your answer to all of those is `yes`, then you may want to make a filter for your package.

Do so by creating an executable script named `build-tools/bin/python-builds` in
this package, and having it exit non-zero when the undesirable versions build.
By default, packages without this file package will build for every version of Python in your versionset.

The version strings that'll be passed in are:

* CPython##
* Jython##

Commands that only run for one version of Python will be run for the version in
the `default_python` argument to `setup()` in `setup.py`. `doc` is one such
command, and is configured by default to run the `doc_command` as defined in
`setup.py`, which will build Sphinx documentation.

An example can be found [here](https://code.amazon.com/packages/Pytest/blobs/5b12631bdbdc9fca03d994bb8ef3bbe8a70676d3/--/build-tools/bin/python-builds).

#### Best practices for filtering

1. Use forwards-compatible filters (i.e. `$version -ge 37`).  This will make it painless to test and update when you update your default
2. Don't tie to older versions.  This is expensive technical debt that paying it down sooner is far better than chaining yourself (and your consumers) to older interpreters
3. If you want to specifically only build for the default interpreter, you can add the filter `[[ $1 == "$(default-python-package-name)" ]] || exit 1`
  1. **Only do this if you intend to vend an executable that is specifically getting run with the default interpreter, for integration test packages, or for packages that only should be built for a single interpreter (such as a data-generation or activation-scripts package)**





## Testing

`brazil-build test` will run the test command defined in `setup.py`, by default `brazilpython_pytest`, which is defined in the [BrazilPython-Pytest-3.0](https://code.amazon.com/packages/BrazilPython-Pytest/releases) package. The arguments for this will be taken from `setup.cfg`'s `[tool:pytest]` section, but can be set in `pytest.ini` if that's your thing too. Coverage is enabled by default, provided by pytest-cov, which is part of the `PythonTestingDependencies` package group.

## Running

(For details, check out the [FAQ](https://w.amazon.com/bin/view/BrazilPython3/FAQ/#HHowdoIrunaninterpreterinmypackage3F))

To run a script in your bin/ directory named `my-script` with its default
shebang, you just do this:

`brazil-runtime-exec *my-script*`

To run the default interpreter for experimentation:

`brazil-runtime-exec python`

## Deploying

If this is a library, nothing needs to be done; it'll deploy the versions it builds. If you intend to ship binaries, add a dependency on [Python = default](https://devcentral.amazon.com/ac/brazil/directory/package/majorVersionSummary/Python?majorVersion=default) to `Config`, and then ensure that the right branch of `Python-default` is built into your versionset. You'll want either [CPython2](https://code.amazon.com/packages/Python/trees/CPython2) or [CPython3](https://code.amazon.com/packages/Python/trees/CPython3) for CPython.
