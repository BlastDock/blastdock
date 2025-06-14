#!/usr/bin/env python3
"""
BlastDock CLI entry point for module execution
"""

if __name__ == '__main__':
    import sys
    import os
    
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Import and run the CLI
    try:
        # Import directly from cli.py to avoid conflict with cli/ directory
        import importlib.util
        
        # First ensure blastdock package is properly imported
        import blastdock
        
        # Load main_cli.py
        cli_module_path = os.path.join(os.path.dirname(__file__), 'main_cli.py')
        spec = importlib.util.spec_from_file_location("blastdock.main_cli", cli_module_path)
        cli_module = importlib.util.module_from_spec(spec)
        
        # Set the module's __package__ to enable relative imports
        cli_module.__package__ = 'blastdock'
        
        # Add to sys.modules
        sys.modules['blastdock.main_cli'] = cli_module
        
        # Now execute the module
        spec.loader.exec_module(cli_module)
        
        # Run the main function
        cli_module.main()
    except Exception as e:
        print(f"Failed to import CLI module: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)