import os
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import inspect
from pathlib import Path

class ToolDefinitionSchema:
    def __init__(self, name, description, input_schema, function):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.function = function


class ReadFileInput(BaseModel):
    path: str = Field(description="Relative path of a file in the working directory.")

class ListDirectoryInput(BaseModel):
    path: str = Field(description="Relative path of a directory in the working directory.")

class EditFileInput(BaseModel):
    path: str = Field(
        description="The relative path to the file."
    )
    old_str: str = Field(
        description=(
            "The exact snippet of text you want to replace. "
            "CRITICAL: This string must be globally unique within the file. "
            "You MUST include surrounding lines of code (such as function definitions or comments) to guarantee uniqueness. "
            "If you are creating a new file from scratch, leave this as an empty string (\"\")."
        )
    )
    new_str: str = Field(
        description="The exact new string that will overwrite the old_string."
    )


def read_file(**kwargs):
    try:
        valid_input = ReadFileInput(**kwargs)
        
        with open(valid_input.path, "r") as rfile:
            return rfile.read()

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def list_dir(**kwargs):
    try:
        valid_input = ListDirectoryInput(**kwargs)

        entries_itr = os.scandir(valid_input.path)
        return str([{file.name: "file" if file.is_file() else "directory"} for file in entries_itr])

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def edit_file(**kwargs):
    try:
        valid_input = EditFileInput(**kwargs)

        file_path = Path(valid_input.path)
        old_str = valid_input.old_string if valid_input.old_string else None
        new_str = valid_input.new_string

        if old_str == new_str:
            raise ValueError("Invalid input params -- new string cannot be the same with old string.")

        if not file_path.exists():
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            if old_str is None:
                file_path.write_text(new_str)
                return f"Successfully created new file at {file_path}"
            else:
                raise ValueError("Given path for the file to be edited does not exist.")
        else:
            if old_str is None:
                raise ValueError("String to be replaced is not provided. Please, read the file first.")
            
            content = file_path.read_text()

            if old_str not in content:
                raise ValueError("The old_str provided was not found in the file. Check for exact spacing and indentation.")
            
            occurrences = content.count(old_str)

            if occurrences > 1:
                raise ValueError(f"Found {occurrences} instances of old_str. Provide more surrounding lines of code to make the match globally unique.")
            
            new_content = content.replace(old_str, new_str)

            temp_file_path = file_path.with_name(f"{file_path.name}.tmp")
            temp_file_path.write_text(new_content)
            os.replace(temp_file_path.resolve(), file_path.resolve())

            return f"Successfully updated {file_path}"

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"


read_file_def = ToolDefinitionSchema(
    name="read_file",
    description="Read the contents of given relative file path. Do not use with directories.",
    input_schema=ReadFileInput.model_json_schema(),
    function=read_file
)

list_dir_def = ToolDefinitionSchema(
    name="list_dir",
    description="List files in the given relative path. Returns the name and the type of entries as list of key-value dictionaries. Do not use with file paths.",
    input_schema=ListDirectoryInput.model_json_schema(),
    function=list_dir
)

edit_file_def = ToolDefinitionSchema(
    name="edit_file",
    description=inspect.clean_doc("""
        Edits an existing file or create a new one. Do not rewrite the entire file unless necessary.
        
        TO EDIT AN EXISTING FILE:
        - You must replace a specific block of text. 
        - CRITICAL: 'old_str' must be globally unique within the file. You MUST include surrounding lines of code (like function definitions) to guarantee a unique match.
        - 'old_str' must exactly match the existing file content, including all spaces, newlines, and indentation.
        
        TO CREATE A NEW FILE:
        - If the file path does not exist, it will be created automatically.
        - You MUST pass an empty string ("") for 'old_str'.
        - Pass the complete content for the new file in 'new_string'.
        
        RULES: 'old_str' and 'new_str' must never be identical.
    """),
    input_schema=EditFileInput.model_json_schema(),
    function=edit_file
)

# ---------------------------------------------------------
# EXPORT REGISTRY
# main.py will import this list. Add new tools here.
# ---------------------------------------------------------
AVAILABLE_TOOLS = [
    read_file_def,
    list_dir_def,
    edit_file_def
]