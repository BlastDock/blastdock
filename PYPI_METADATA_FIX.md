# PyPI Metadata Error Fix

## Problem

When trying to upload to PyPI, you encountered the error:
```
Metadata is missing required fields: Name, Version.
```

This occurs despite the metadata clearly containing both Name and Version fields.

## Root Cause

The issue is caused by a version mismatch:
- Modern setuptools (>=61.0) generates metadata with `Metadata-Version: 2.4`
- Twine 5.0.0 only supports metadata versions up to 2.2
- This causes twine to fail parsing the metadata, reporting missing fields

## Solution

### Immediate Fix

1. Use the provided `fix_metadata.py` script to downgrade the metadata version:
   ```bash
   python3 fix_metadata.py
   ```

2. Verify the fix worked:
   ```bash
   twine check dist/*
   ```

### Build Process

Use the `build_for_pypi.py` script for building PyPI-ready packages:
```bash
python3 build_for_pypi.py
```

This script:
1. Cleans build directories
2. Builds the distributions
3. Automatically fixes metadata versions
4. Validates packages with twine

### Manual Process

If you prefer to do it manually:

```bash
# Clean
rm -rf dist build *.egg-info

# Build
python3 -m build

# Fix metadata
python3 fix_metadata.py

# Validate
twine check dist/*

# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## Technical Details

### What the fix does

The `fix_metadata.py` script:
1. Extracts the wheel/sdist files
2. Finds METADATA/PKG-INFO files
3. Changes `Metadata-Version: 2.4` to `Metadata-Version: 2.1`
4. Repackages the files

### Why this works

- Metadata-Version 2.1 is widely supported
- The actual metadata format between 2.1 and 2.4 is compatible for basic fields
- PyPI accepts 2.1 metadata without issues

## Long-term Solutions

1. **Wait for twine update**: Future versions of twine will support Metadata-Version 2.4

2. **Use older setuptools**: Pin setuptools to a version that generates 2.1 metadata:
   ```toml
   [build-system]
   requires = ["setuptools>=45,<61", "wheel"]
   ```

3. **Use the build script**: Continue using `build_for_pypi.py` which handles this automatically

## Prevention

To avoid this issue in the future:

1. Always run `twine check` before uploading
2. Use the provided build script
3. Test uploads to TestPyPI first
4. Keep twine updated: `pip install --upgrade twine`

## Configuration Notes

The project uses both `pyproject.toml` and a minimal `setup.py` for compatibility. The minimal setup.py just calls `setup()` with no arguments, deferring all configuration to pyproject.toml.

This is the recommended approach for modern Python packaging while maintaining backward compatibility.