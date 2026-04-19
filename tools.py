import os
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
import inspect
from pathlib import Path
import shutil
import re

# tools to be implemented: cd, mv, cp and find or grep

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

class MoveInput(BaseModel):
    path: str = Field(description="Relative path of the source file or directory.")
    destination: str = Field(description="Relative path to the destination.")

class CopyInput(BaseModel):
    path: str = Field(description="Relative path of the source file or directory.")
    destination: str = Field(description="Relative path to the destination.")

class SearchInput(BaseModel):
    directory: str = Field(description="Relative path of the directory to search in.")
    pattern: str = Field(description="Regular expression pattern to search for.")

class CreateFileInput(BaseModel):
    path: str = Field(description="Relative path of a file to be created or updated (metadata).")

class RemoveFileInput(BaseModel):
    path: str = Field(description="Relative path of a file to be removed/deleted.")

class ReadFileInput(BaseModel):
    path: str = Field(description="Relative path of a file in the to be read.")

# class EditFileInput(BaseModel):
#     path: str = Field(
#         description="The relative path to the file to be edited."
#     )
#     old_str: str = Field(
#         description=(
#             "The exact snippet of text you want to replace. "
#             "CRITICAL: This string must be globally unique within the file. "
#             "You MUST include surrounding lines of code (such as function definitions or comments) to guarantee uniqueness. "
#             "If you are creating a new file from scratch, leave this as an empty string (\"\")."
#         )
#     )
#     new_str: str = Field(
#         description="The exact new string that will overwrite the old_string."
#     )

class EditFileInput(BaseModel):
    path: str = Field(description="Relative path of the file.")
    start_line: int = Field(description="Line number to start replacing (1-indexed). Use -1 to append to the end of the file.")
    end_line: int = Field(description="Line number to end replacing (inclusive). Use -1 to replace from start_line to the end of the file. To insert without deleting, set end_line to start_line - 1.")
    new_content: str = Field(description="The exact new text to insert. Pass an empty string to delete the specified lines.")


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

def move_item(**kwargs):
    try:
        valid_input = MoveInput(**kwargs)
        if not os.path.exists(valid_input.path):
            return f"Execution Error: Source '{valid_input.path}' does not exist."
        
        shutil.move(valid_input.path, valid_input.destination)
        return f"Successfully moved '{valid_input.path}' to '{valid_input.destination}'."
    
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def copy_item(**kwargs):
    try:
        valid_input = CopyInput(**kwargs)
        if not os.path.exists(valid_input.path):
            return f"Execution Error: Source '{valid_input.path}' does not exist."
        
        if os.path.isdir(valid_input.path):
            shutil.copytree(valid_input.path, valid_input.destination)
            return f"Successfully copied directory '{valid_input.path}' to '{valid_input.destination}'."
        else:
            shutil.copy2(valid_input.path, valid_input.destination)
            return f"Successfully copied file '{valid_input.path}' to '{valid_input.destination}'."
            
    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

def search_grep(**kwargs):
    try:
        valid_input = SearchInput(**kwargs)
        if not os.path.isdir(valid_input.directory):
            return f"Execution Error: Directory '{valid_input.directory}' does not exist."
        
        compiled_pattern = re.compile(valid_input.pattern)
        results = []
        match_limit = 100 # Context window protection
        
        for root, _, files in os.walk(valid_input.directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if compiled_pattern.search(line):
                                results.append(f"{file_path}:{line_num}: {line.strip()}")
                                if len(results) >= match_limit:
                                    results.append("... [Truncated: Match limit reached]")
                                    return "\n".join(results)
                except UnicodeDecodeError:
                    continue # Silently skip binary files
                    
        if not results:
            return "No matches found."
        return "\n".join(results)
        
    except ValidationError as e:
        return f"Schema Error: {e}"
    except re.error as e:
        return f"Execution Error: Invalid regex pattern '{valid_input.pattern}': {str(e)}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

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

# def edit_file(**kwargs):
#     try:
#         valid_input = EditFileInput(**kwargs)

#         input_path = Path(valid_input.path)
#         old_str = valid_input.old_string if valid_input.old_string else None
#         new_str = valid_input.new_string

#         if not is_safe_path(input_path):
#             raise ValueError("Permission Denied: Cannot operate outside of the project directory.")
#         if old_str == new_str:
#             raise ValueError("Invalid input params -- new string cannot be the same with old string.")

#         if not input_path.exists():
#             if not input_path.parent.exists():
#                 input_path.parent.mkdir(parents=True, exist_ok=True)
#             if old_str is None:
#                 input_path.write_text(new_str)
#                 return f"Successfully created new file at {input_path}"
#             else:
#                 raise ValueError("Given path for the file to be edited does not exist.")
#         else:
#             if old_str is None:
#                 raise ValueError("String to be replaced is not provided. Please, read the file first.")
            
#             content = input_path.read_text()
#             if old_str not in content:
#                 raise ValueError("The old_str provided was not found in the file. Check for exact spacing and indentation.")
            
#             occurrences = content.count(old_str)
#             if occurrences > 1:
#                 raise ValueError(f"Found {occurrences} instances of old_str. Provide more surrounding lines of code to make the match globally unique.")
            
#             new_content = content.replace(old_str, new_str)

#             temp_input_path = input_path.with_name(f"{input_path.name}.tmp")
#             temp_input_path.write_text(new_content)
#             os.replace(temp_input_path.resolve(), input_path.resolve())

#             return f"Successfully updated {input_path}"

#     except ValidationError as e:
#         return f"Schema Error: {e}"
#     except Exception as e:
#         return f"Execution Error: {e}"

def edit_file(**kwargs):
    try:
        valid_input = EditFileInput(**kwargs)
        path = valid_input.path
        start = valid_input.start_line
        end = valid_input.end_line
        content = valid_input.new_content

        if not is_safe_path(path):
            raise ValueError("Permission Denied: Cannot operate outside of the project directory.")

        # Ensure new content terminates with a newline if it contains text
        if content and not content.endswith('\n'):
            content += '\n'

        # Handle file creation if appending to a non-existent file
        if not os.path.exists(path):
            if start == 1 or start == -1:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Successfully created new file '{path}'."
            else:
                return f"Execution Error: File '{path}' does not exist."

        # Read existing file into memory as a list of lines
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Append Mode
        if start == -1:
            # Prevent appending to the same line if the file doesn't end with a newline
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            
            if content:
                lines.append(content)
            msg = f"Successfully appended content to the end of '{path}'."
            
        # Edit/Insert Mode
        else:
            start_idx = max(0, start - 1)
            
            # Replace until the end of the file
            if end == -1:
                lines[start_idx:] = [content] if content else []
            # Standard slice replacement/insertion
            else:
                end_idx = max(0, end)
                lines[start_idx:end_idx] = [content] if content else []
            
            action = "deleted" if not content else "edited"
            msg = f"Successfully {action} lines {start} to {end if end != -1 else 'end'} in '{path}'."

        # Write the modified list back to the file
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        return msg

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {str(e)}"


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

move_def = ToolDefinitionSchema(
    name="move_item",
    description="Move or rename a file or directory. Equivalent to 'mv' command.",
    input_schema=MoveInput.model_json_schema(),
    function=move_item
)

copy_def = ToolDefinitionSchema(
    name="copy_item",
    description="Copy a file or directory. Equivalent to 'cp' command.",
    input_schema=CopyInput.model_json_schema(),
    function=copy_item
)

search_def = ToolDefinitionSchema(
    name="search_grep",
    description="Search for a regex pattern within all text files in a given directory. Equivalent to 'grep -r'.",
    input_schema=SearchInput.model_json_schema(),
    function=search_grep
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

# edit_file_def = ToolDefinitionSchema(
#     name="edit_file",
#     description=inspect.clean_doc("""
#         Edits an existing file or create a new one. Do not rewrite the entire file unless necessary.
        
#         TO EDIT AN EXISTING FILE:
#         - You must replace a specific block of text. 
#         - CRITICAL: 'old_str' must be globally unique within the file. You MUST include surrounding lines of code (like function definitions) to guarantee a unique match.
#         - 'old_str' must exactly match the existing file content, including all spaces, newlines, and indentation.
        
#         TO CREATE A NEW FILE:
#         - If the file path does not exist, it will be created automatically.
#         - You MUST pass an empty string ("") for 'old_str'.
#         - Pass the complete content for the new file in 'new_string'.
        
#         RULES: 'old_str' and 'new_str' must never be identical.
#     """),
#     input_schema=EditFileInput.model_json_schema(),
#     function=edit_file
# )

edit_file_def = ToolDefinitionSchema(
    name="edit_file",
    description="Edit an existing file or create a new one using precise line numbers. Can insert, replace, delete, or append text.",
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
    move_def,
    copy_def,
    search_def,
    create_file_def,
    remove_file_def,
    read_file_def,
    edit_file_def
]