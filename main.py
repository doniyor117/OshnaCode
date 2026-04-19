from google import genai
from termcolor import colored
from dotenv import load_dotenv
from google.genai import types
from tools import AVAILABLE_TOOLS

load_dotenv()

class OshnaAgent:
    def __init__(self):
        self.client = genai.Client()
        self.conversation = []
        self.tools = AVAILABLE_TOOLS
        self.system_prompt = "You are a helpful assistant." 
        
    def get_user_input(self) -> str:
        try:
            user_input = input(colored("\nYou: ", "blue")).strip()
            return user_input
        except (EOFError, KeyboardInterrupt):
            return None
            
    def execute_function(self, call_id: str, name: str, args: dict) -> types.Part:
        for tool in self.tools:
            if tool.name == name:
                try:
                    # Pass the dictionary directly as keyword arguments
                    result = tool.function(**args)
                    response_data = {"result": result}
                except Exception as e:
                    response_data = {"error": f"Execution failed: {str(e)}"}
                
                # Construct the raw schema types directly to support the 'id' field
                return types.Part(
                    function_response=types.FunctionResponse(
                        id=call_id,
                        name=name,
                        response=response_data
                    )
                )
                
        # Fallback if the model hallucinates a tool name
        return types.Part(
            function_response=types.FunctionResponse(
                id=call_id,
                name=name,
                response={"error": f"Tool '{name}' is not defined."}
            )
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
                    
                self.conversation.append(
                    types.Content(
                        role="user", 
                        parts=[types.Part.from_text(text=user_input)]
                    )
                )

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
                self.conversation.pop() 
                read_user_input = True
                continue

            if not response or not response.candidates:
                print(colored("\nSystem: Inference failed. Reverting turn.", "red"))
                self.conversation.pop()
                read_user_input = True
                continue
            
            model_content = response.candidates[0].content
            self.conversation.append(model_content)

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

            if tool_calls:
                tool_response_parts = []
                for tool_call in tool_calls:
                    print(colored(f"\n[System: Executing tool '{tool_call.name}']", "magenta"))
                    
                    response_part = self.execute_function(
                        call_id=tool_call.id,
                        name=tool_call.name,
                        args=tool_call.args
                    )
                    tool_response_parts.append(response_part)

                self.conversation.append(
                    types.Content(role="user", parts=tool_response_parts)
                )
                
                read_user_input = False
            else:
                read_user_input = True

if __name__=="__main__":
    agent = OshnaAgent()
    agent.run()