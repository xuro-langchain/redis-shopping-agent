# 🎵 Redis Music Store Agent

A multi-agent AI customer support system for a digital music store and live entertainment platform. Built with **LangGraph** for orchestration and **Redis** for context management, memory, and semantic search.

<p align="center">
  <img src="https://img.shields.io/badge/LangGraph-Multi--Agent-blue" alt="LangGraph">
  <img src="https://img.shields.io/badge/Redis-Checkpointing%20%7C%20Memory%20%7C%20Vector%20Search-red" alt="Redis">
  <img src="https://img.shields.io/badge/OpenAI-GPT--4.1-green" alt="OpenAI">
</p>

---

## What is this?

This project demonstrates a production-ready **multi-agent architecture** where a supervisor agent orchestrates specialized subagents to handle different customer queries:

| Subagent | Purpose | Data Source |
|----------|---------|-------------|
| 🎵 **Music Catalog** | Browse artists, albums, songs, genres | Chinook SQL Database |
| 🧾 **Invoice** | View purchase history, invoice details | Chinook SQL Database |
| 🎤 **Concert** | Personalized concert recommendations | Redis Vector Search |

The system features **human-in-the-loop verification**, **long-term user memory**, and **persistent conversations**—all powered by Redis.

---

## Features

- 🎵 **Music Catalog Search** — Query artists, albums, tracks, and genres from a digital music store
- 🧾 **Invoice & Purchase History** — Access customer billing records and transaction details
- 🎤 **Concert Recommendations** — Semantic search over 3,000+ concerts with filtering by genre, location, and budget
- 🧠 **Long-term Memory** — Remembers user music preferences, location, and budget across sessions
- 💾 **Persistent Conversations** — Resume any conversation where you left off
- 🔐 **Account Verification** — Human-in-the-loop flow to verify customer identity
- 📝 **Dynamic Prompts** — Prompts stored in Redis for live updates without redeployment

---

## Architecture Overview

```
                              ┌─────────────────────────────────────────────┐
                              │           LANGGRAPH STATE GRAPH             │
                              │                                             │
   User Input                 │  ┌──────────┐    ┌────────────┐            │
       │                      │  │  Verify  │───▶│    Load    │            │
       ▼                      │  │   Info   │    │   Memory   │            │
┌─────────────┐               │  └────┬─────┘    └─────┬──────┘            │
│    CLI /    │               │       │                │                   │
│  Notebook   │──────────────▶│       │ (interrupt)    ▼                   │
└─────────────┘               │  ┌────▼─────┐    ┌───────────┐             │
                              │  │  Human   │    │Supervisor │             │
                              │  │  Input   │    │   Agent   │             │
                              │  └──────────┘    └─────┬─────┘             │
                              │                        │                   │
                              │         ┌──────────────┼──────────────┐    │
                              │         ▼              ▼              ▼    │
                              │   ┌──────────┐  ┌──────────┐  ┌──────────┐ │
                              │   │  Music   │  │ Invoice  │  │ Concert  │ │
                              │   │ Subagent │  │ Subagent │  │ Subagent │ │
                              │   └────┬─────┘  └────┬─────┘  └────┬─────┘ │
                              │        │             │             │       │
                              │        ▼             ▼             ▼       │
                              │   ┌──────────────────────────────────────┐ │
                              │   │            Create Memory             │ │
                              │   └──────────────────────────────────────┘ │
                              └─────────────────────────────────────────────┘
                                          │              │              │
                          ┌───────────────┘              │              └───────────────┐
                          ▼                              ▼                              ▼
                   ┌─────────────┐               ┌─────────────┐               ┌─────────────┐
                   │   CHINOOK   │               │    REDIS    │               │    REDIS    │
                   │  DATABASE   │               │   (State)   │               │  (Vectors)  │
                   │   (SQLite)  │               │             │               │             │
                   ├─────────────┤               ├─────────────┤               ├─────────────┤
                   │ • Albums    │               │ • Checkpoint│               │ • Concert   │
                   │ • Artists   │               │ • Memory    │               │   embeddings│
                   │ • Tracks    │               │ • Prompts   │               │ • Hybrid    │
                   │ • Invoices  │               │             │               │   search    │
                   │ • Customers │               │             │               │             │
                   └─────────────┘               └─────────────┘               └─────────────┘
```

---

## Data Sources

### 1. Chinook Database (SQLite)

The [Chinook database](https://github.com/lerocha/chinook-database) is a sample digital music store database containing:

- **Customers** — User accounts with email, phone, and support rep assignments
- **Invoices** — Purchase history with line items and billing details
- **Artists & Albums** — Music catalog with artist information
- **Tracks** — Individual songs with genre, duration, and pricing
- **Genres** — Music genre classifications

The database is loaded into memory at startup from the official SQL source.

### 2. Concert Index (Redis Vector Search)

A synthetic dataset of **~50 concerts** with rich metadata:

```yaml
fields:
  - name, artist, venue, description  # Text search
  - genre, location, age_restriction  # Tag filters
  - price_min, price_max              # Numeric range filters
  - coordinates                       # Geo search
  - embedding                         # 3072-dim vector (text-embedding-3-large)
```

The concert subagent performs **hybrid search** combining:
- **Semantic similarity** — Natural language queries like "energetic outdoor festival"
- **Metadata filtering** — Genre, location, max price, availability

### 3. User Memory (Redis Store)

User preferences are extracted from conversations and persisted:

```python
{
    "customer_id": "42",
    "music_preferences": ["rock", "jazz", "blues"],
    "preferred_location": "Austin, TX",
    "max_concert_budget": 150.00
}
```

These preferences are loaded at the start of each session and used to personalize recommendations.

---

## Quickstart

### Prerequisites

- Python 3.13+
- Redis instance (local Docker or [Redis Cloud](https://redis.io/cloud))
- OpenAI API key

### 1. Clone and configure environment

```bash
git clone https://github.com/redis-developer/redis-shopping-agent.git
cd redis-shopping-agent

# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# OPENAI_API_KEY=sk-...
# REDIS_URL=redis://localhost:6379
```

### 2. Install dependencies

```bash
# Install uv package manager (if needed)
pip install uv

# Install project dependencies
uv sync
```

### 3. Start Redis

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis/redis-stack:latest

# Or connect to Redis Cloud / existing instance via REDIS_URL
```

---

## Usage

### CLI (Recommended)

The CLI provides a beautiful interactive experience with Rich formatting:

```bash
# Start a new conversation
uv run music-store

# Resume an existing conversation by thread ID
uv run music-store --thread <thread-id>
```

#### CLI Commands

| Command | Description |
|---------|-------------|
| `exit` / `quit` / `q` | Exit and save conversation |
| `clear` | Clear the terminal screen |
| `thread` | Display current thread ID |

#### Example Session

```
╭──────────────────────────────────────────────────────────────────╮
│ 🎵 Music Store Agent                                             │
│ Thread: a1b2c3d4-e5f6-7890-abcd-ef1234567890                     │
│ Status: new                                                      │
│                                                                  │
│ Commands: exit or quit to leave, clear to reset                  │
╰──────────────────────────────────────────────────────────────────╯

You: What rock concerts are happening in Austin under $100?

Agent
╭──────────────────────────────────────────────────────────────────╮
│ Before I can help you, could you please verify your account?     │
│ Please provide your customer ID, email, or phone number.         │
╰──────────────────────────────────────────────────────────────────╯

You: My email is luisg@embraer.com.br

Agent
╭──────────────────────────────────────────────────────────────────╮
│ Thank you! I verified your account (Customer ID: 1).             │
│                                                                  │
│ I found these rock concerts in Austin under $100:                │
│                                                                  │
│ 🎸 **Garage Revival Night**                                      │
│    Venue: Stubb's BBQ                                            │
│    Date: June 15, 2025                                           │
│    Price: $45 - $85                                              │
│                                                                  │
│ 🎸 **Desert Highway Tour**                                       │
│    Venue: Austin City Limits Live                                │
│    Date: July 3, 2025                                            │
│    Price: $60 - $95                                              │
╰──────────────────────────────────────────────────────────────────╯

You: exit

Goodbye! Your conversation is saved.
Resume with: uv run music-store --thread a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Jupyter Notebook

For development and exploration, use the included notebook [demo.ipynb](demo.ipynb).

The notebook demonstrates:
- Step-by-step agent invocation
- Interrupt handling for account verification
- Memory persistence across turns
- Tool execution traces

---

## Project Structure

```
redis-shopping-agent/
├── agents/
│   ├── agent.py          # Main StateGraph and supervisor logic
│   ├── subagents.py      # Music, Invoice, and Concert subagents
│   ├── tools.py          # Database and vector search tools
│   ├── prompts.py        # Prompt loading from Redis
│   ├── checkpoint.py     # RedisSaver and RedisStore setup
│   ├── utils.py          # LLM, Redis, and database utilities
│   ├── cli.py            # Rich CLI interface
│   └── seed/
│       ├── prompts.json        # Default system prompts
│       ├── concerts.json       # 3,000+ concert records with embeddings
│       └── concert_index.yaml  # RedisVL schema for concert index
├── demo.ipynb            # Interactive walkthrough notebook
├── langgraph.json        # LangGraph deployment config
├── pyproject.toml        # Project dependencies
└── README.md
```

---

## How It Works

### 1. Account Verification (Human-in-the-Loop)

When a user starts a conversation, the graph first attempts to verify their identity:

```python
def verify_info(state: State):
    # Parse user input for customer ID, email, or phone
    # Look up in database
    # If not found, interrupt for human input
```

The `interrupt()` function pauses the graph, returning control to the user. When they provide credentials, the graph resumes via `Command(resume=user_input)`.

### 2. Memory Loading

Once verified, the user's saved preferences are loaded from Redis:

```python
def load_memory(state: State, store: BaseStore):
    namespace = ("memory_profile", user_id)
    existing_memory = store.get(namespace, "user_memory")
    # Returns: music_preferences, preferred_location, max_concert_budget
```

### 3. Supervisor Routing

The supervisor agent decides which subagent(s) to call based on the query:

- "What albums does AC/DC have?" → **Music Catalog Subagent**
- "Show me my last 3 invoices" → **Invoice Subagent**  
- "Find me jazz concerts in NYC" → **Concert Subagent**

### 4. Memory Creation

After each conversation turn, new preferences are extracted and saved:

```python
def create_memory(state: State, store: BaseStore):
    # LLM extracts: music_preferences, preferred_location, max_concert_budget
    store.put(namespace, key, {"memory": updated_memory.model_dump()})
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for GPT-4.1 and embeddings |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `LANGSMITH_API_KEY` | — | Optional: Enable LangSmith tracing |
| `LANGSMITH_PROJECT` | — | Optional: LangSmith project name |

### Switching LLMs

Edit `agents/utils.py` to use a different model:

```python
# OpenAI (default)
llm = ChatOpenAI(model_name="gpt-4.1", temperature=0)

# Anthropic
# llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)

# Google Vertex AI
# llm = ChatVertexAI(model_name="gemini-1.5-flash-002", temperature=0)
```

---

## Resources

- **[LangGraph Documentation](https://langchain-ai.github.io/langgraph/)** — Multi-agent orchestration framework
- **[LangChain Documentation](https://python.langchain.com/)** — LLM application framework
- **[RedisVL](https://github.com/redis/redis-vl-python)** — Python client for Redis vector search
- **[LangSmith](https://smith.langchain.com/)** — Debugging and monitoring for LLM applications

---

## License

MIT License — See [LICENSE](LICENSE) for details.
