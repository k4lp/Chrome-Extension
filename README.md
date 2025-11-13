# GemBrain 🧠

**A Gemini-powered agentic second brain desktop application**

## ⚠️ IMPORTANT: Data Structure Refactor

GemBrain has undergone a **major refactor** with new data structures optimized for iterative reasoning workflows. If you have an existing installation, you'll need to **migrate your database** (this will delete old data but create a backup).

👉 **See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for migration instructions**

## Overview

GemBrain is an intelligent personal knowledge management system designed for iterative reasoning workflows:

- **Tasks**: Decomposed work items with status tracking (pending/ongoing/paused/completed)
- **Memory**: Small hints, clues, and insights accessible on demand
- **Goals**: Expected outcomes for verification and quality checks
- **Datavault**: Large data storage (code, text, outputs) to avoid token limits
- **AI Agent**: Gemini orchestrates actions, creates structure, and provides insights
- **Automations**: Daily/weekly reviews, memory resurfacing, and custom workflows
- **Goal-Based Verification**: Verification LLM checks if outputs meet defined goals

## Features

### Agentic Intelligence
- **Iterative Reasoning**: Gemini breaks down complex queries into subtasks and executes them systematically
- **Goal-Based Verification**: Set goals for output quality; verification LLM checks if they're met
- **Smart Task Decomposition**: Automatically creates tasks from conversations with status tracking
- **Memory Storage**: Stores insights and facts for future reference
- **Code Execution**: Execute Python code with full GemBrain API access
- **Datavault**: Store large data blobs to avoid token limits
- **Automated Reviews**: Daily/weekly reviews and memory resurfacing

### Clean, Focused UI
- Swiss minimalist design aesthetic
- Multi-panel workspace (Chat, Tasks)
- Context-aware side panel showing recent tasks and memories
- Comprehensive Settings panel for all configuration
- Migration tool in File menu for database schema updates

### Data Ownership
- Local SQLite database
- Your data stays on your machine
- Automatic backups
- Easy data export

## Installation

### Using pip

```bash
pip install -r requirements.txt
```

### Using Poetry

```bash
poetry install
```

## Configuration

On first run, GemBrain will create a configuration file at `~/.gembrain/config.json`.

### Required Setup

1. **Gemini API Key**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it in Settings → Gemini → API Key

### Optional Configuration

Settings panel includes:
- **General**: Theme, fonts, compact mode
- **Gemini**: Model selection, temperature, token limits
- **Agent Behavior**: Auto-actions, confirmations
- **Storage**: Database location, backups
- **Automations**: Daily/weekly reviews, note resurfacing

## Usage

### Running the Application

```bash
# Using poetry
poetry run gembrain

# Using python directly
python -m gembrain.main
```

### Quick Start

1. **Set up your API key** in Settings
2. **Chat with GemBrain** to capture thoughts
3. **Review proposed actions** before applying
4. **Explore your notes and tasks** in dedicated panels
5. **Enable automations** for daily/weekly reviews

### Example Interactions

**Capturing a thought:**
> "I just had an idea for a new project: build a personal finance tracker. Should start by researching existing solutions."

GemBrain will:
- Create a new project note
- Add a task "Research existing finance trackers"
- Link them together

**Daily reflection:**
> "What did I accomplish today?"

GemBrain will:
- Review today's completed tasks
- Show recent note updates
- Optionally create a daily review note

## Architecture

```
gembrain/
├── config/          # Settings and configuration management
├── core/            # Database models, repositories, services
├── agents/          # Gemini client, orchestrator, tools
├── automation/      # Scheduler and automation rules
├── ui/              # PyQt6 GUI components
│   ├── widgets/     # Individual panels and dialogs
│   └── styles/      # QSS stylesheets
└── utils/           # Logging, paths, utilities
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black gembrain/
ruff check gembrain/
```

### Type Checking

```bash
mypy gembrain/
```

## Roadmap

- [ ] Phase 1: Core structure and configuration ✅
- [ ] Phase 2: Database models and services
- [ ] Phase 3: Gemini integration
- [ ] Phase 4: Automation engine
- [ ] Phase 5: GUI implementation
- [ ] Phase 6: Connect all systems
- [ ] Phase 7: Polish and styling
- [ ] Phase 8: Tests and documentation

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## Acknowledgments

- Powered by Google's Gemini AI
- Built with PyQt6
- Inspired by tools like Obsidian, Notion, and Roam Research
