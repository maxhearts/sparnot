"""JSON editor utility with validation."""

import json
import tempfile
import subprocess
import os
from pathlib import Path
from typing import TypeVar, Type, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def edit_json(
    data: Optional[Dict[str, Any]],
    schema_class: Type[T],
    description: str = "schema",
) -> Optional[T]:
    """
    Edit JSON data in system editor with validation.
    
    Args:
        data: Initial data dict (or None for new)
        schema_class: Pydantic model class to validate against
        description: Description of what's being edited (for error messages)
    
    Returns:
        Validated schema instance, or None if user cancelled
    """
    # Create temp file with JSON
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        if data:
            json.dump(data, f, indent=2)
        else:
            json.dump({}, f, indent=2)
        temp_path = f.name

    try:
        # Open in editor
        editor = os.environ.get("EDITOR", "nano")
        if editor == "nano" and not _command_exists("nano"):
            editor = "vim"
        
        subprocess.run([editor, temp_path], check=True)

        # Read edited JSON
        with open(temp_path) as f:
            edited_data = json.load(f)

        # Validate
        try:
            instance = schema_class(**edited_data)
            return instance
        except ValidationError as e:
            print(f"\n✗ Validation errors for {description}:")
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                print(f"  - {field}: {message}")
            
            retry = input("\nWould you like to edit again? (y/n): ").strip().lower()
            if retry == "y":
                return edit_json(edited_data, schema_class, description)
            return None

    except subprocess.CalledProcessError:
        print("Editor was closed without saving. Cancelled.")
        return None
    except json.JSONDecodeError as e:
        print(f"\n✗ Invalid JSON: {e}")
        retry = input("Would you like to edit again? (y/n): ").strip().lower()
        if retry == "y":
            return edit_json(data, schema_class, description)
        return None
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(
            ["which", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

