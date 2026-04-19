from pydantic import BaseModel, Field, ValidationError

class ToolDefinition:
    def __init__(self, name, description, input_schema, function):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.function = function

class ReadFileInput(BaseModel):
    path: str = Field(description="Relative path of a file in the working directory.")

def read_file(input_data: str):
    try:
        valid_input = ReadFileInput.model_validate_json(input_data)
        path = valid_input.path

        with open(path, "r") as rfile:
            return rfile.read()

    except ValidationError as e:
        return f"Schema Error: {e}"
    except Exception as e:
        return f"Execution Error: {e}"


read_file_definition = ToolDefinition(
    name="read_file",
    description="Read the contents of given relative file path. Use this when you want to see what's inside of the file. Do not use this with directory names.",
    input_schema=ReadFileInput.model_json_schema(),
    function=read_file
)
