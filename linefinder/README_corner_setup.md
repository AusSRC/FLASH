# FLASH Plotting Dependencies: `corner` and `contourpy` Setup

This README documents a local fix for the `corner` plotting module used by
`flash_finder.py` / `plotting.py`, made necessary by the Setonix module stack
change from `pawseyenv/2025.08` to `pawseyenv/2024.05`.

## Background

After the `pawseyenv` swap, two issues appeared:

1. `ModuleNotFoundError: No module named 'corner'` — the custom `corner`
   plotting package (not a Pawsey/Spack module) was no longer being found on
   `sys.path`.
2. `AttributeError: module 'contourpy' has no attribute 'contour_generator'`
   — the Spack-provided `py-contourpy/1.0.7` module under `pawseyenv/2024.05`
   is missing its `__init__.py`, leaving only the compiled `.so` extension.
   This makes Python treat it as a broken namespace package with no public
   API exposed. This appears to be a genuine bug in the shared Spack install
   and has not been reported to Pawsey as of writing.

Both issues are worked around locally under `$FLASHHOME`, so that any user
with their own `$FLASHHOME` can reproduce the fix without editing
`plotting.py`.

## Setup for a new `$FLASHHOME`

### 1. `corner` package

Copy the working `corner` package into `$FLASHHOME/corner/`:

```bash
cp -r /software/projects/ja3/ger063/setonix/python/lib/python3.11/site-packages/corner \
      "$FLASHHOME/corner"
```

This should result in `$FLASHHOME/corner/` containing:

```
__init__.py
arviz_corner.py
core.py
corner.py
version.py
__pycache__/
```

### 2. `contourpy` fix

Load the standard job module environment first (see `set_local_flash_env.sh`
or the module list below), then install a clean, dependency-free copy of
`contourpy` into `$FLASHHOME/contourpy_fix/`:

```bash
python3 -m pip install --target="$FLASHHOME/contourpy_fix" --no-deps contourpy==1.0.7
```

**Important:** the `--no-deps` flag is required. Without it, `pip` will also
pull in a current `numpy` (e.g. 2.x), which is incompatible with the
environment's pinned `py-numpy/1.24.4`, `py-scipy/1.11.3`, and
`py-matplotlib/3.8.1` (all of which require `numpy<2`). The existing
environment's `numpy 1.24.4` already satisfies `contourpy`'s real
requirement (`numpy>=1.16`), so no separate numpy install is needed.

### 3. Required module environment

```bash
module unload gcc-native/14.2
module swap pawseyenv/2025.08 pawseyenv/2024.05
module load gcc/12.2.0
module load libfabric/1.15.2.0
module load python/3.11.6
module load py-matplotlib/3.8.1
module load py-astropy/5.1
module load py-mpi4py/3.1.5-py3.11.6
module load gcc/12.2.0
module load py-scipy/1.11.3
module load py-numpy/1.24.4
```

## `plotting.py` path setup

Near the top of `plotting.py`, before `import corner`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.environ["FLASHHOME"], "contourpy_fix"))
sys.path.insert(0, os.environ["FLASHHOME"])
import corner
```

Order matters: `contourpy_fix` must be inserted before `import corner`
resolves matplotlib's internal `import contourpy`, and it should sit ahead
of the broken Spack `contourpy` module on `sys.path`.

## Verifying the setup

```bash
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['FLASHHOME'], 'contourpy_fix'))
sys.path.insert(0, os.environ['FLASHHOME'])
import contourpy
print(contourpy.__file__)
print(contourpy.contour_generator)
import numpy
print(numpy.__version__)
import corner
print(corner.__file__)
"
```

Expected output:

- `contourpy.__file__` → `$FLASHHOME/contourpy_fix/contourpy/__init__.py`
- `contourpy.contour_generator` → `<function contour_generator at 0x...>`
- `numpy.__version__` → `1.24.4` (confirms `contourpy_fix` did not shadow numpy)
- `corner.__file__` → `$FLASHHOME/corner/__init__.py`

## Notes

- `$FLASHHOME` is set in "set_local_flash_env.sh" - ensure it is sourced!

- If Setonix's module stack changes again in future, re-check whether the
  Spack `py-contourpy` module has been fixed upstream (i.e. has a proper
  `__init__.py`) before assuming this workaround is still needed.
