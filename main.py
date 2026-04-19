#!/usr/bin/env python3

from google import genai
from termcolor import colored
from dotenv import load_dotenv
from google.genai import types
from tools import AVAILABLE_TOOLS
from config import system_prompt

load_dotenv()

class OshnaAgent:
    def __init__(self):
        self.client = genai.Client()
        self.conversation = []
        self.tools = AVAILABLE_TOOLS
        self.system_prompt = system_prompt
        self.max_history_chars = 200000
        
    def get_user_input(self) -> str:
        try:
            user_input = input(colored("\nYou: ", "blue")).strip()
            return user_input
        except (EOFError, KeyboardInterrupt):
            return None
            
    def execute_function(self, call_id: str, name: str, args: dict) -> types.Part:
        # HUMAN-IN-THE-LOOP SECURITY BOUNDARY
        if name == "execute_bash":
            command = args.get('command', 'UNKNOWN COMMAND')
            print(colored(f"\n⚠️  WARNING: The agent wants to run a bash command:", "red", attrs=['bold']))
            print(colored(f"   $ {command}", "yellow"))
            
            confirm = input(colored("Allow this command? [y/N]: ", "red")).strip().lower()
            if confirm != 'y':
                print(colored("System: Command execution denied by user.", "grey"))
                # Return the denial directly to the LLM so it knows why it failed
                return types.Part(
                    function_response=types.FunctionResponse(
                        id=call_id,
                        name=name,
                        response={"error": "The human user denied permission to execute this command. You must ask the user for an alternative approach."}
                    )
                )

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
    
    def manage_context(self):
        """
        Calculates character heuristic and drops the oldest conversation turns.
        Ensures tool responses are never orphaned without their preceding calls.
        """
        # Calculate approximate length by casting schema parts to strings
        current_length = sum(len(str(part)) for turn in self.conversation for part in turn.parts)
        
        while current_length > self.max_history_chars and len(self.conversation) > 2:
            # 1. Pop the oldest turn
            dropped_turn = self.conversation.pop(0)
            
            # 2. Check for newly orphaned responses
            # If we dropped a model turn containing a function_call, the NEW oldest turn 
            # (index 0) is the user's function_response. It is now orphaned and MUST be dropped.
            if dropped_turn.role == "model" and any(getattr(p, "function_call", None) for p in dropped_turn.parts):
                if self.conversation and self.conversation[0].role == "user" and any(getattr(p, "function_response", None) for p in self.conversation[0].parts):
                    self.conversation.pop(0)
                    
            # 3. Scrub mid-chain orphans
            # Conversely, if we dropped a text prompt and the NEW oldest turn is a function_response,
            # it means we started pruning in the middle of a tool chain. Keep popping until clean.
            while self.conversation and self.conversation[0].role == "user" and any(getattr(p, "function_response", None) for p in self.conversation[0].parts):
                self.conversation.pop(0)
                
            # Recalculate
            current_length = sum(len(str(part)) for turn in self.conversation for part in turn.parts)

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

            self.manage_context()

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
                        system_instruction=self.system_prompt,
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