import json
from google import genai
from termcolor import colored
from dotenv import load_dotenv
from google.genai import types
from tools import read_file_definition

load_dotenv()

class OshnaAgent:
    def __init__(self):
        self.client = genai.Client()
        self.conversation = []
        self.tools = [read_file_definition]
        self.system_prompt = "You are a helpful assistant." 
        
    def get_user_input(self) -> str:
        try:
            user_input = input(colored("\nYou: ", "blue")).strip()
            return user_input
        except (EOFError, KeyboardInterrupt):
            return None
            
    def execute_function(self, call_id: str, name: str, args: dict) -> types.Part:
        """
        Executes the matched function and returns a properly structured 
        types.Part containing the FunctionResponse.
        """
        for tool in self.tools:
            if tool.name == name:
                try:
                    # tools.py expects a JSON string input, so we dump the args dictionary
                    args_json = json.dumps(args)
                    result = tool.function(args_json)
                    
                    # The response must be a dictionary. We wrap the string result.
                    response_data = {"result": result}
                except Exception as e:
                    # Catch all execution errors and feed them back to the LLM
                    response_data = {"error": f"Execution failed: {str(e)}"}
                
                # Construct the formal function_response part, including the matching ID
                return types.Part.from_function_response(
                    id=call_id,
                    name=name,
                    response=response_data
                )
                
        # Fallback if the model hallucinates a tool name
        return types.Part.from_function_response(
            id=call_id,
            name=name,
            response={"error": f"Tool '{name}' is not defined."}
        )

    def run(self):
        print(colored("Agent Initialized. Type 'exit' to quit.", "cyan"))
        read_user_input = True
        
        while True:
            if read_user_input:
                user_input = self.get_user_input()
                if user_input is None or user_input.lower() == 'exit':
                    print(colored("\nSystem: Exiting...", "grey"))
                    break
                if not user_input:
                    continue
                    
                # Append standard user text turn
                self.conversation.append(
                    types.Content(
                        role="user", 
                        parts=[types.Part.from_text(text=user_input)]
                    )
                )

            # Build the tool declarations dynamically
            function_declarations = [
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.input_schema
                )
                for tool in self.tools
            ]

            try:
                response = self.client.models.generate_content(
                    model="gemma-4-26b-a4b-it",
                    contents=self.conversation,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(function_declarations=function_declarations)],
                        temperature=0.1,
                        max_output_tokens=8000
                    )
                )
            except Exception as e:
                print(colored(f"\nAPI Error: {e}", "red"))
                self.conversation.pop() # Remove the failed prompt to allow retry
                read_user_input = True
                continue

            if not response or not response.candidates:
                print(colored("\nSystem: Inference failed. Reverting turn.", "red"))
                self.conversation.pop()
                read_user_input = True
                continue
            
            # 1. Append the model's exact response to history immediately.
            # This ensures both text and function_calls are recorded perfectly.
            model_content = response.candidates[0].content
            self.conversation.append(model_content)

            # 2. Parse the parts to separate text from tool calls
            full_text = ""
            tool_calls = []

            for part in model_content.parts:
                if getattr(part, "thought", False):
                    continue

                if part.text:
                    full_text += part.text
                if part.function_call:
                    tool_calls.append(part.function_call)

            if full_text:
                print(colored("Gemini: ", "yellow"), end="")
                print(full_text)

            # 3. If tools were called, execute them and format the response
            if tool_calls:
                tool_response_parts = []
                for tool_call in tool_calls:
                    print(colored(f"\n[System: Executing tool '{tool_call.name}']", "magenta"))
                    
                    # Note: tool_call.args is a dict
                    response_part = self.execute_function(
                        call_id=tool_call.id,
                        name=tool_call.name,
                        args=tool_call.args
                    )
                    tool_response_parts.append(response_part)

                # Append the function responses as a new user turn
                self.conversation.append(
                    types.Content(role="user", parts=tool_response_parts)
                )
                
                # Loop continues immediately without waiting for user input 
                # so the model can process the tool results.
                read_user_input = False
            else:
                # No tools called, wait for the next human input
                read_user_input = True

if __name__=="__main__":
    agent = OshnaAgent()
    agent.run()