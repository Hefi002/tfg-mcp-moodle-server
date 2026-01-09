#!/usr/bin/env python3
"""
Setup script for the Moodle MCP Server.

This script helps configure the project securely by requesting
necessary information from the user and creating the .env file
with credentials.
"""

import os
import sys
from pathlib import Path
from getpass import getpass


def print_header():
    """Print the welcome header."""
    print("=" * 60)
    print("  Moodle MCP Server Setup")
    print("=" * 60)
    print()


def print_section(title):
    """Print a section title."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")


def get_input(prompt, default=None, required=True):
    """
    Request input from user with validation.
    
    Args:
        prompt: Message to display
        default: Default value (optional)
        required: Whether the field is required
    
    Returns:
        str: Value entered by the user
    """
    if default:
        prompt = f"{prompt} [{default}]"
    
    prompt += ": "
    
    while True:
        value = input(prompt).strip()
        
        if not value and default:
            return default
        
        if not value and required:
            print("This field is required. Please enter a value.")
            continue
        
        return value


def get_yes_no(prompt, default=True):
    """
    Request yes/no confirmation from user.
    
    Args:
        prompt: Message to display
        default: Default value (True/False)
    
    Returns:
        bool: True if response is affirmative
    """
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def validate_url(url):
    """
    Validate that a URL has a correct basic format.
    
    Args:
        url: URL to validate
    
    Returns:
        bool: True if URL seems valid
    """
    return url.startswith(('http://', 'https://'))


def create_env_file(config):
    """
    Create the .env file with the provided configuration.
    
    Args:
        config: Dictionary with configuration
    """
    # Get project root directory (where setup.py is located)
    project_root = Path(__file__).parent
    env_path = project_root / '.env'
    
    # Check if it already exists
    if env_path.exists():
        print(f"\nThe .env file already exists at: {env_path}")
        if not get_yes_no("Do you want to overwrite it?", default=False):
            print("\nSetup cancelled.")
            sys.exit(0)
        
        # Backup existing .env
        backup_path = env_path.parent / f"{env_path.name}.backup"
        # Remove old backup if it exists
        if backup_path.exists():
            backup_path.unlink()
        env_path.rename(backup_path)
        print(f"✓ Backup created at: {backup_path}")
    
    # Create the new .env file
    env_content = f"""# Moodle Configuration
MOODLE_URL={config['moodle_url']}
MOODLE_TOKEN={config['moodle_token']}

# Server Configuration
LOG_LEVEL={config['log_level']}
DEBUG={config['debug']}
"""
    
    env_path.write_text(env_content, encoding='utf-8')
    print(f"\n✓ .env file created successfully at: {env_path}")


def create_env_example():
    """Create .env.example file if it doesn't exist."""
    # Get project root directory (where setup.py is located)
    project_root = Path(__file__).parent
    env_example_path = project_root / '.env.example'
    
    if env_example_path.exists():
        return
    
    example_content = """# Moodle Configuration
MOODLE_URL=http://localhost:8000
MOODLE_TOKEN=your_token_here

# Server Configuration
LOG_LEVEL=INFO
DEBUG=false
"""
    
    env_example_path.write_text(example_content, encoding='utf-8')
    print(f"✓ .env.example file created")


def main():
    """Main setup script function."""
    print_header()
    
    print("This script will help you configure the Moodle MCP Server.")
    print("You will be asked for the necessary information to create the .env")
    print("file with your credentials securely.\n")
    
    if not get_yes_no("Do you want to continue?", default=True):
        print("\nSetup cancelled.")
        sys.exit(0)
    
    config = {}
    
    # Request Moodle URL
    print_section("1. Moodle Configuration")
    
    while True:
        moodle_url = get_input(
            "Your Moodle instance URL",
            default="http://localhost:8000"
        )
        
        if validate_url(moodle_url):
            # Remove trailing slash if present
            config['moodle_url'] = moodle_url.rstrip('/')
            break
        else:
            print("URL must start with http:// or https://")
    
    # Request Moodle token
    print("\nTo get your Moodle token:")
    print("1. Log in to your Moodle instance as administrator")
    print("2. Go to: Site administration > Security > Security keys")
    print("3. Create a new token with the necessary permissions")
    print("4. Copy the generated token\n")
    
    config['moodle_token'] = getpass("Moodle authentication token (hidden): ").strip()
    
    if not config['moodle_token']:
        print("\nToken is required. Setup cancelled.")
        sys.exit(1)
    
    # Server configuration
    print_section("2. Server Configuration")
    
    print("Logging level:")
    print("  DEBUG   - Maximum detail (development)")
    print("  INFO    - General information (recommended)")
    print("  WARNING - Only warnings and errors")
    print("  ERROR   - Only errors")
    
    while True:
        log_level = get_input(
            "\nLogging level",
            default="INFO"
        ).upper()
        
        if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            config['log_level'] = log_level
            break
        else:
            print("Invalid level. Choose: DEBUG, INFO, WARNING or ERROR")
    
    config['debug'] = 'true' if get_yes_no(
        "\nEnable debug mode?",
        default=False
    ) else 'false'
    
    # Configuration summary
    print_section("3. Configuration Summary")
    print(f"Moodle URL:     {config['moodle_url']}")
    print(f"Token:          {'*' * len(config['moodle_token'])} (hidden)")
    print(f"Log Level:      {config['log_level']}")
    print(f"Debug:          {config['debug']}")
    
    if not get_yes_no("\nDo you confirm this configuration?", default=True):
        print("\nSetup cancelled.")
        sys.exit(0)
    
    # Create files
    print_section("4. Creating Configuration Files")
    create_env_file(config)
    create_env_example()
    
    # Final instructions
    print_section("5. Setup Complete!")
    print("✓ Your Moodle MCP Server is configured correctly.")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run tests: pytest")
    print("3. Check README.md for usage instructions")
    print("\nIMPORTANT: The .env file contains sensitive information.")
    print("   DO NOT share it or upload it to public repositories.")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during setup: {e}")
        sys.exit(1)
