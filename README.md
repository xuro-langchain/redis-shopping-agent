# Redis Music Store Agent

A multi-agent customer support system for a digital music store, powered by LangGraph and Redis. The system uses a supervisor architecture with specialized sub-agents for handling music catalog queries and invoice/purchase history requests.

## Features

- 🎵 **Music Catalog Agent** - Browse artists, albums, songs, and genres
- 🧾 **Invoice Agent** - Access purchase history and invoice details
- 🧠 **Long-term Memory** - Remembers user preferences across conversations backed by Redis
- 💾 **Persistent Threads** - Conversations survive restarts via Redis checkpointing
- 🔐 **Account Verification** - Human-in-the-loop verification flow
- 📝 **Customizable Prompts** -- Prompts dynamically loaded from Redis to allow for versioning and updates remotely

## Quickstart

### Set up environment
```bash
# Copy the environment template
cp .env.example .env

# Edit .env with your API keys:
# - OPENAI_API_KEY
# - REDIS_URL (defaults to redis://localhost:6379)
```

### Install dependencies
```bash
# Install uv if you haven't already!
pip install uv

# Install the package
uv sync
```

### Start [Redis](https://redis.io/cloud)
```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:latest

# Or use Redis Cloud / your existing Redis instance
```

---

## CLI Usage

The easiest way to interact with the agent is through the CLI:

```bash
# Start a new conversation
uv run music-store

# Resume an existing conversation
uv run music-store --thread <thread-id>

# Force a new thread
uv run music-store --new
```

### CLI Commands

Once in the shell, you can use these commands:

| Command | Description |
|---------|-------------|
| `exit` / `quit` / `q` | Exit the CLI (conversation is saved) |
| `clear` | Clear the screen |
| `thread` | Display the current thread ID |

### Example Session

```
╭──────────────────────────────────────────────────────────────╮
│ 🎵 Music Store Agent                                         │
│ Thread: a1b2c3d4-e5f6-7890-abcd-ef1234567890                 │
│ Status: new                                                  │
│                                                              │
│ Commands: exit or quit to leave, clear to reset              │
╰──────────────────────────────────────────────────────────────╯

You: What albums do you have by The Rolling Stones?

Agent
╭──────────────────────────────────────────────────────────────╮
│ I'd be happy to help you with that! Before I can provide     │
│ information about our available albums, could you please     │
│ provide your customer ID, email, or phone number to verify   │
│ your account?                                                │
╰──────────────────────────────────────────────────────────────╯

You: My customer ID is 1

Agent
╭──────────────────────────────────────────────────────────────╮
│ Thank you! I found the following albums by The Rolling       │
│ Stones in our catalog:                                       │
│                                                              │
│ • Voodoo Lounge (1994)                                       │
│ • No Security (1998)                                         │
│ • ...                                                        │
╰──────────────────────────────────────────────────────────────╯

You: exit

Goodbye! Your conversation is saved.
Resume with: uv run music-store --thread a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## Jupyter Notebook Demo

For a more detailed walkthrough, check out the included notebooks:

```bash
# Start Jupyter
uv run jupyter notebook

# Open demo.ipynb for the main demo
```


## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Supervisor Agent                        │
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
│  │   Verify    │──▶│    Load     │──▶│   Supervisor    │    │
│  │    Info     │   │   Memory    │   │   (orchestrate) │    │
│  └─────────────┘   └─────────────┘   └─────────────────┘    │
│         │                                     │              │
│         ▼                                     ▼              │
│  ┌─────────────┐                    ┌─────────────────┐      │
│  │   Human     │                    │  Create Memory  │      │
│  │   Input     │                    │                 │      │
│  └─────────────┘                    └─────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
     ┌─────────────────┐             ┌─────────────────┐
     │  Music Catalog  │             │    Invoice      │
     │    Sub-agent    │             │   Sub-agent     │
     └─────────────────┘             └─────────────────┘
```

---

## Project Structure

```
redis-shopping-agent/
├── agents/
│   ├── agent.py        # Main graph and supervisor logic
│   ├── checkpoint.py   # Redis checkpointer and store setup
│   ├── cli.py          # CLI interface
│   ├── prompts.py      # System prompts
│   ├── subagents.py    # Music and invoice sub-agents
│   ├── tools.py        # Database query tools
│   └── utils.py        # Shared utilities
├── demo.ipynb          # Interactive demo notebook
├── multi_agent.ipynb   # Multi-agent architecture notebook
├── langgraph.json      # LangGraph configuration
└── pyproject.toml      # Project dependencies
```

---

## Resources

- **[LangChain Documentation](https://docs.langchain.com/oss/python/langchain/overview)** - Complete LangChain reference
- **[LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/overview)** - LangGraph guides and API reference  
- **[LangChain Academy](https://academy.langchain.com/)** - Free courses with video tutorials
- **[LangSmith](https://smith.langchain.com)** - Debugging and monitoring for LLM applications
- **[Redis](https://redis.io)** - In-memory data store for checkpointing and memory
