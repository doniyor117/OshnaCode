import os
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

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
        description="The relative path to the file. If the file or directory does not exist, it will be automatically created."
    )
    old_string: str = Field(
        description=(
            "The exact snippet of text you want to replace. "
            "CRITICAL: This string must be globally unique within the file. "
            "You MUST include surrounding lines of code (such as function definitions or comments) to guarantee uniqueness. "
            "If you are creating a new file from scratch, leave this as an empty string (\"\")."
        )
    )
    new_string: str = Field(
        description="The exact new string that will overwrite the old_string. Ensure proper spacing, newlines, and indentation are maintained."
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
        return [{file.name: "file" if file.is_file() else "directory"} for file in entries_itr]

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
            else:
                raise ValueError("Given path for the file to be edited does not exist.")
        else:
            if old_str is None:
                raise ValueError("String to be replaced is not provided. Please, read the file first.")
            
            content = file_path.read_text()

            if old_str not in content:
                raise ValueError("The old_str provided was not found in the file. Check for exact spacing and indentation.")
            
            occurences = content.count(old_str)

            if occurences > 1:
                raise ValueError(f"Found {occurrences} instances of old_str. Provide more surrounding lines of code to make the match globally unique.")
            
            new_content = content.replace(old_str, new_str)

            temp_file_path = file_path.with_stem(f"{file_path.stem}_temp")
            temp_file_path.write_text(new_content)

            os.replace(temp_file_path.resolve(), file_path.resolve())

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
    description=(
        "Make edits to a file by replacing a specific block of text. "
        "Use this instead of rewriting entire files to save context. "
        "You must accurately provide the old text to be replaced and the new text to insert."
    ),
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