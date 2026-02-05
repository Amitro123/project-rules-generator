import logging
import sys

def setup_logging(verbose: bool = False):
    """Configure the root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    # Using a simple format for CLI friendliness
    formatter = logging.Formatter('%(levelname)s: %(name)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Configure root logger
    root = logging.getLogger('project_rules_generator')
    root.setLevel(level)
    
    # Avoid duplicate handlers
    if not root.handlers:
        root.addHandler(handler)
        
    # Set external libraries to warning to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
