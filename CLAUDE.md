# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🧮 Common Development Commands

### Testing Commands
```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_agent.py -v

# Run tests with coverage
python -m pytest tests/ -v --cov

# Run integration tests specifically
python -m pytest -m integration
```

### Code Quality Commands  
```bash
# Format and fix code style issues
ruff check --fix

# Run type checking (if mypy is configured)
mypy .

# Format code with black
black .
```

### Virtual Environment
```bash
# Always use the project virtual environment for Python commands
source venv_linux/bin/activate  # Linux/Mac
# or
venv_linux\Scripts\activate     # Windows
```

## 🏗️ Project Architecture

This is a **Context Engineering Template** focused on web scraping automation using Playwright and Python, with the following key architectural patterns:

### Agent-Based Architecture
- **Modular agent design** following the pattern: `agent.py`, `tools.py`, `prompts.py`
- **Multi-agent systems** with subagents for specialized tasks (see `use-cases/agent-factory-with-subagents/`)
- **Dependency injection** using Pydantic models for agent configuration

### Web Scraping Framework Structure
- **Playwright-based scraping** for dynamic content extraction
- **Recursive data extraction** through parent/child category navigation  
- **CSV output format** with structured naming: `{OUT_PREFIX}-{date_time}.csv`
- **Snowflake integration** for data warehouse storage

### Key Directories
- `examples/` - Reference implementations and Jupyter notebooks for scraping logic
- `use-cases/` - Specialized implementations (RAG agents, multi-agent systems)
- `PRPs/` - Product Requirements Prompts for feature development
- `.claude/commands/` - Custom Claude Code commands (`generate-prp.md`, `execute-prp.md`)

## 🔄 Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use the project virtual environment** whenever executing Python commands, including for unit tests.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.