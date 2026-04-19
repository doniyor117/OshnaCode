import os
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import inspect
from pathlib import Path

# tools: mkdir, rmdir, touch, rm, cd, mv, cp and find or grep

class ToolDefinitionSchema:
    def __init__(self, name, description, input_schema, function):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.function = function

def is_safe_path(target_path: str, root_dir: str = "."):
    # Resolve absolute paths to prevent "../../../" attacks
    root = Path(root_dir).resolve()
    target = Path(target_path).resolve()
    return root in target.parents or target == root


class MakeDirInput(BaseModel):
    path: str = Field(description="Relative path of a directory (or a directory with it's parents) to be created.")

class RemoveDirInput(BaseModel):
    path: str = Field(description="Relative path of a directory to be removed.")
    recursive: bool = Field(description="Whether to remove the directory recursively or not.")

class ListDirectoryInput(BaseModel):
    path: str = Field(description="Relative path of a directory to list contents.")

class CreateFileInput(BaseModel):
    path: str = Field(description="Relative path of a file to be created or updated (metadata).")

class RemoveFileInput(BaseModel):
    path: str = Field(description="Relative path of a file to be removed/deleted.")

class ReadFileInput(BaseModel):
    path: str = Field(description="Relative path of a file in the to be read.")

class EditFileInput(BaseModel):
    path: str = Field(
        description="The relative path to the file to be edited."
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


def make_dir(**kwargs):
    try:
        valid_input = MakeDirInput(**kwargs)
        input_path = valid_input.path
        if not is_safe_path(input_path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")

        os.makedirs(input_path, exist_ok=True)
        return f"Successfully created directory: {input_path}"
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def remove_dir(**kwargs):
    try:
        valid_input = RemoveDirInput(**kwargs)
        recursive = valid_input.recursive
        input_path = valid_input.path
        if not is_safe_path(input_path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")


        if recursive:
            import shutil
            shutil.rmtree(input_path)
            return f"Permanently deleted directory and all contents: {input_path}"
        else:
            os.rmdir(input_path)
            return f"Deleted empty directory: {input_path}"
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def list_dir(**kwargs):
    try:
        valid_input = ListDirectoryInput(**kwargs)

        entries_itr = os.scandir(valid_input.path)
        return str([{file.name: "file" if file.is_file() else "directory"} for file in entries_itr])
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def create_file(**kwargs):
    try:
        valid_input = CreateFileInput(**kwargs)
        input_path = Path(valid_input.path)
        if not is_safe_path(input_path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")
        
        input_path.touch(exist_ok=True)
        return f"File created: {input_path}"
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def remove_file(**kwargs):
    try:
        valid_input = RemoveFileInput(**kwargs)
        input_path = valid_input.path
        # Safety: check if it's a directory first to avoid confusing the agent
        if os.path.isdir(input_path):
            return f"Error: '{input_path}' is a directory. Use rmdir instead."
        
        os.remove(input_path)
        return f"Successfully deleted: {input_path}"
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def read_file(**kwargs):
    try:
        valid_input = ReadFileInput(**kwargs)
        input_path = valid_input.path
        if not is_safe_path(input_path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")
        
        with open(input_path, "r") as rfile:
            return rfile.read()
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"

def edit_file(**kwargs):
    try:
        valid_input = EditFileInput(**kwargs)

        input_path = Path(valid_input.path)
        old_str = valid_input.old_string if valid_input.old_string else None
        new_str = valid_input.new_string

        if not is_safe_path(input_path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")
        if old_str == new_str:
            raise ValueError("Invalid input params -- new string cannot be the same with old string.")

        if not input_path.exists():
            if not input_path.parent.exists():
                input_path.parent.mkdir(parents=True, exist_ok=True)
            if old_str is None:
                input_path.write_text(new_str)
                return f"Successfully created new file at {input_path}"
            else:
                raise ValueError("Given path for the file to be edited does not exist.")
        else:
            if old_str is None:
                raise ValueError("String to be replaced is not provided. Please, read the file first.")
            
            content = input_path.read_text()
            if old_str not in content:
                raise ValueError("The old_str provided was not found in the file. Check for exact spacing and indentation.")
            
            occurrences = content.count(old_str)
            if occurrences > 1:
                raise ValueError(f"Found {occurrences} instances of old_str. Provide more surrounding lines of code to make the match globally unique.")
            
            new_content = content.replace(old_str, new_str)

            temp_input_path = input_path.with_name(f"{input_path.name}.tmp")
            temp_input_path.write_text(new_content)
            os.replace(temp_input_path.resolve(), input_path.resolve())

            return f"Successfully updated {input_path}"

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"


make_dir_def = ToolDefinitionSchema(
    name="make_dir",
    description="Creates a directory or a directory with it's parent directories. Don't use this with files.",
    input_schema=MakeDirInput.model_json_schema(),
    function=make_dir
)

remove_dir_def = ToolDefinitionSchema(
    name="remove_dir",
    description="Removes the given path directory. If recursive true, it removes the dir with it's contents and child directories. ONLY use recursive if you are 100 percent sure and user agrees too.",
    input_schema=RemoveDirInput.model_json_schema(),
    function=remove_dir
)

list_dir_def = ToolDefinitionSchema(
    name="list_dir",
    description="List files in the given relative path. Returns the name and the type of entries as list of key-value dictionaries. Do not use with file paths.",
    input_schema=ListDirectoryInput.model_json_schema(),
    function=list_dir
)

create_file_def = ToolDefinitionSchema(
    name="create_file",
    description="Creates a file for the given relative path or updates it's metadata. DO NOT use this with directories.",
    input_schema=CreateFileInput.model_json_schema(),
    function=create_file
)

remove_file_def = ToolDefinitionSchema(
    name="remove_file",
    description="Removes a file for the given relative path. DO NOT use this with directories. ONLY use it if you are 100 percent sure and user agrees too.",
    input_schema=RemoveFileInput.model_json_schema(),
    function=remove_file
)

read_file_def = ToolDefinitionSchema(
    name="read_file",
    description="Read the contents of given relative file path. Do not use with directories.",
    input_schema=ReadFileInput.model_json_schema(),
    function=read_file
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
    make_dir_def,
    remove_dir_def,
    list_dir_def,
    create_file_def,
    remove_file_def,
    read_file_def,
    edit_file_def
]