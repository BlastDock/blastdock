# Deprecated CLI Module

## Notice
The `cli/main.py` file has been deprecated and renamed to `main.py.deprecated`.

## Reason
This file contained duplicate/legacy CLI commands with unimplemented functionality (marked as TODO).
The proper CLI implementation exists in:
- `main_cli.py` (primary CLI entry point)
- `cli/deploy.py` (deployment commands)
- `cli/marketplace.py` (marketplace commands)
- `cli/monitoring.py` (monitoring commands)
- `cli/config_commands.py` (config commands)
- And other CLI modules

## Migration
All functionality should be accessed through the main `blastdock` CLI command via `main_cli.py`.

## Date Deprecated
2025-11-07

## Related Bug Fix
Fixed as part of BUG-004: Unimplemented CLI Functions
