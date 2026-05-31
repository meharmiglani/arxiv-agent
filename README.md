# arxiv-agent

An AI-powered research assistant that uses Claude and the Model Context Protocol (MCP) to search, retrieve, and summarize academic papers from arXiv.

## Overview

This project exposes an MCP server with tools, resources, and prompts for querying arXiv. A Claude-powered chatbot client connects to that server (and optionally other MCP servers) and lets you ask research questions in natural language.

## Project Structure

```
arxiv-agent/
├── stdio_local_server.py   # MCP server using stdio transport (local use)
├── sse_remote_server.py    # MCP server using SSE transport on port 8001 (remote use)
├── mcp_client.py           # Basic MCP chatbot client
├── mcp_client_v2.py        # Enhanced client with resource and prompt support
├── server_config.json      # MCP server connection config
└── papers/                 # Downloaded paper metadata (auto-created)
```

## MCP Server

Both server files expose the same tools, resources, and prompts — they differ only in transport.

### Local Server (`stdio_local_server.py`)

Uses **stdio transport**. The client automatically spawns this as a subprocess on your local machine — you don't need to start it manually when using the chatbot client, as `server_config.json` handles that.

To start it directly (e.g. for standalone testing):

```bash
uv run stdio_local_server.py
```

### Remote Server (`sse_remote_server.py`)

Uses **SSE (Server-Sent Events) transport** on port 8001. This server runs as a standalone process that remote clients connect to over HTTP.

To start it locally:

```bash
uv run sse_remote_server.py
```

The remote server is also deployed on Render:

> **Deployed URL:** <!-- paste your Render URL here -->

### Inspecting with MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a visual tool that lets you interact with your MCP server through a browser UI — great for testing tools, browsing resources, and running prompts without writing any code.

To launch it:

```bash
npx @modelcontextprotocol/inspector
```

This opens a local web UI where you can connect to either server:

- **Local server (stdio):** select `stdio` as the transport, set the command to `uv` and args to `run stdio_local_server.py`
- **Remote server (SSE):** select `SSE` as the transport and enter `http://localhost:8001/sse` (or your Render URL for the deployed version)

Once connected, you can see all available tools, resources, and prompts, invoke them with custom inputs, and inspect the raw responses — all without running the full chatbot client.

### Tools

| Tool | Description |
|---|---|
| `search_papers(topic, max_results)` | Search arXiv for papers on a topic and save results locally |
| `extract_info(paper_id)` | Retrieve saved metadata for a specific paper by ID |

### Resources

| URI | Description |
|---|---|
| `papers://folders` | List all locally saved topic folders |
| `papers://{topic}` | Get full paper details for a given topic |

### Prompts

| Prompt | Description |
|---|---|
| `generate_search_prompt(topic, num_papers)` | Generate a structured Claude prompt for deep research on a topic |

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- An Anthropic API key

### Installation

```bash
git clone https://github.com/meharmiglani/arxiv-agent.git
cd arxiv-agent
uv sync
```

### Environment Variables

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### Configure MCP Servers

Edit `server_config.json` to point to the server file you want to use:

```json
{
  "mcpServers": {
    "research": {
      "command": "uv",
      "args": ["run", "stdio_local_server.py"]
    }
  }
}
```

## Usage

### Run the chatbot

```bash
uv run mcp_client_v2.py
```

### Chat commands

| Input | Action |
|---|---|
| Any text | Send a research query to Claude (tools called automatically) |
| `@folders` | List all locally saved topic folders |
| `@<topic>` | View saved papers for a topic |
| `/prompts` | List available MCP prompts |
| `/prompt <name> <arg=value>` | Execute a specific prompt |
| `quit` | Exit the chatbot |

### Example session

```
Query: What are the latest advances in diffusion models?

Calling tool search_papers with args {'topic': 'diffusion models', 'max_results': 2}
[Claude summarizes the retrieved papers]

Query: @folders
Available Topics:
- diffusion_models

Query: /prompts
Available Prompts:
 - generate_search_prompt: Generate a prompt for Claude to find and discuss academic papers on a specific topic.

Query: /prompt generate_search_prompt topic=transformers num_papers=5
```

## Dependencies

| Package | Purpose |
|---|---|
| `anthropic` | Claude API client |
| `arxiv` | arXiv search and paper retrieval |
| `mcp` | Model Context Protocol SDK |
| `python-dotenv` | Load `.env` variables |
| `nest-asyncio` | Allow nested event loops (used in v2 client) |
