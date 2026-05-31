from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio
import nest_asyncio

nest_asyncio.apply()

load_dotenv()


class MCP_ChatBot:

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.available_tools = []
        self.available_prompts = []
        self.sessions = {}

    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()

            try:
                # List available tools
                tools_response = await session.list_tools()
                if tools_response and tools_response.tools:
                    for tool in tools_response.tools:
                        self.sessions[tool.name] = session
                        self.available_tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.inputSchema,
                            }
                        )

                # List available prompts
                prompts_response = await session.list_prompts()
                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.sessions[prompt.name] = session
                        self.available_prompts.append(
                            {
                                "name": prompt.name,
                                "description": prompt.description,
                                "arguments": prompt.arguments,
                            }
                        )

                # List available resources
                resources_response = await session.list_resources()
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.sessions[resource_uri] = session

            except Exception as e:
                print(f"Error on server '{server_name}': {e}")

        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise

    async def process_query(self, query):
        messages = [{"role": "user", "content": query}]

        while True:
            response = self.anthropic.messages.create(
                max_tokens=2024,
                model="claude-sonnet-4-6",
                tools=self.available_tools,
                messages=messages,
            )

            assistant_content = []
            has_tool_use = False

            for content in response.content:
                if content.type == "text":
                    print(content.text)
                    assistant_content.append(content)
                    messages.append({"role": "assistant", "content": assistant_content})

                elif content.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append(content)

                    # Get session and call tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool {content.name} not found")
                        break
                    result = await session.call_tool(
                        content.name, arguments=content.input
                    )

                    # Collect all tool results
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content,
                        }
                    )

                # Exit loop if no tool use is needed
                if not has_tool_use:
                    break

    async def get_resource(self, resource_uri):
        session = self.sessions.get(resource_uri)

        # Fallback for paper URI - Try any papers resource session
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("papers://"):
                    session = sess
                    print(f"Using session for {uri}")
                    break

        if not session:
            print(f"Resource session for {resource_uri} not found")

        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource {resource_uri}")
                print(f"\nContent:")
                print(result.contents[0].text)
            else:
                print(f"No content found for resource {resource_uri}")
        except Exception as e:
            print(f"Error reading resource {resource_uri}: {e}")

    async def list_prompts(self):
        """List all available prompts."""

        if not self.available_prompts:
            print("No prompts available")
            return

        print("Available Prompts:")
        for prompt in self.available_prompts:
            print(f" - {prompt['name']}: {prompt['description']}")
            if prompt["arguments"]:
                print(f"   Arguments:")
                for arg in prompt["arguments"]:
                    arg_name = (
                        arg.name if hasattr(arg, "name") else arg.get("name", " ")
                    )
                    print(f"     - {arg_name}")

    async def execute_prompt(self, prompt_name, args):
        """Execute a prompt with the given arguments."""

        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt {prompt_name} not found")
            return

        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content

                # Extract text from the prompt content
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, "text"):
                    text = prompt_content.text
                else:
                    text = " ".join(
                        item.text if hasattr(item, "text") else str(item)
                        for item in prompt_content
                    )
                print(f"\nExecuting prompt {prompt_name}...")
                await self.process_query(text)
        except Exception as e:
            print(f"\nError executing prompt {prompt_name}: {e}")

    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        print("Use @folders to see available topics.")
        print("Use @<topic> to search papers in that topic.")
        print("Use /prompts to list available prompts.")
        print("Use /prompt <name> to execute a specific prompt.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if not query:
                    continue

                if query.lower() == "quit":
                    break

                # Check for @resource syntax
                if query.startswith("@"):
                    # Remove @ sign
                    topic = query[1:]
                    if topic == "folders":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://folders/{topic}"
                    await self.get_resource(resource_uri)
                    continue

                # Check for /command syntax
                if query.startswith("/"):
                    parts = query.split(" ")
                    command = parts[0].lower()

                    if command == "/prompts":
                        await self.list_prompts()
                    elif command == "/prompt":
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1>")
                            continue
                        prompt_name = parts[1]
                        args = {}

                        # Parse arguments
                        for arg in parts[2:]:
                            if "=" in arg:
                                key, value = arg.split("=", 1)
                                args[key] = value
                        await self.execute_prompt(prompt_name, args)
                    continue

                await self.process_query(query)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
