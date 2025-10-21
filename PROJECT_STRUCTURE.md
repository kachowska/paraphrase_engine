# Paraphrase Engine v1.0 - Project Structure

## 📁 Directory Layout

```
paraphrase_engine/
├── 📄 README.md                          # Main documentation
├── 📄 DEPLOYMENT.md                      # Deployment guide
├── 📄 PROJECT_STRUCTURE.md               # This file
├── 📄 requirements.txt                   # Python dependencies
├── 📄 .gitignore                         # Git ignore rules
├── 📄 Dockerfile                         # Docker container configuration
├── 📄 docker-compose.yml                 # Docker Compose orchestration
├── 📄 env.example                        # Environment variables template
├── 📄 main.py                            # Application entry point
├── 📄 start.sh                           # Startup script
├── 📄 test_providers.py                  # Provider testing utility
├── 📄 __init__.py                        # Package initialization
│
├── 📁 config/                            # Configuration module
│   ├── __init__.py
│   └── settings.py                       # Application settings
│
├── 📁 block1_telegram_bot/               # Block 1: User Interface
│   ├── __init__.py
│   └── bot.py                            # Telegram bot implementation
│
├── 📁 block2_orchestrator/               # Block 2: Task Management
│   ├── __init__.py
│   └── task_manager.py                   # Task orchestration logic
│
├── 📁 block3_paraphrasing/               # Block 3: AI Processing
│   ├── __init__.py
│   ├── agent_core.py                     # Multi-AI agent system
│   └── ai_providers.py                   # AI provider implementations
│
├── 📁 block4_document/                   # Block 4: Document Processing
│   ├── __init__.py
│   └── document_builder.py               # .docx manipulation
│
├── 📁 block5_logging/                    # Block 5: Logging System
│   ├── __init__.py
│   └── logger.py                         # Comprehensive logging
│
├── 📁 temp_files/                        # Temporary file storage (created at runtime)
│   └── tasks/                            # Task data storage
│
├── 📁 logs/                              # Application logs (created at runtime)
│   ├── operations.jsonl
│   ├── errors.jsonl
│   └── results.jsonl
│
└── 📁 credentials/                       # API credentials (not in git)
    └── google-sheets-key.json

```

## 📊 File Statistics

```
Total Files: 24
Total Lines of Code: ~3,365+
Language: Python 3.11+
```

## 🔧 Core Modules

### Configuration (`config/`)
- **settings.py** (60 lines): Centralized configuration management using Pydantic

### Block 1: Telegram Bot Interface (`block1_telegram_bot/`)
- **bot.py** (313 lines): User interaction layer
  - Command handlers (`/start`, `/cancel`)
  - File upload handling
  - Fragment processing
  - Result delivery

### Block 2: Task Orchestrator (`block2_orchestrator/`)
- **task_manager.py** (351 lines): Core business logic
  - Task creation and lifecycle management
  - Fragment processing orchestration
  - Document building coordination
  - File cleanup and retention

### Block 3: Paraphrasing Agent (`block3_paraphrasing/`)
- **agent_core.py** (353 lines): Multi-AI paraphrasing system
  - Parallel candidate generation
  - Intelligent evaluation
  - Final humanization
- **ai_providers.py** (233 lines): AI service integrations
  - OpenAI GPT-4o provider
  - Anthropic Claude provider
  - Google Gemini provider

### Block 4: Document Builder (`block4_document/`)
- **document_builder.py** (394 lines): .docx processing
  - Format-preserving replacement
  - Reverse-order processing
  - Paragraph and table handling

### Block 5: Logging System (`block5_logging/`)
- **logger.py** (481 lines): Comprehensive logging
  - Structured logging (JSON)
  - Google Sheets integration
  - Performance analytics
  - Error tracking

## 🚀 Entry Points

### Main Application
```bash
python -m paraphrase_engine.main
# or
./start.sh
```

### Testing Utilities
```bash
python test_providers.py  # Test AI provider configuration
```

### Docker Deployment
```bash
docker-compose up -d
```

## 📦 Dependencies

### Core Dependencies
- `fastapi` - Web framework (for future API endpoints)
- `python-telegram-bot` - Telegram bot framework
- `python-docx` - Document processing
- `pydantic` - Configuration management

### AI Providers
- `openai` - OpenAI GPT integration
- `anthropic` - Claude integration
- `google-generativeai` - Gemini integration

### Logging & Storage
- `gspread` - Google Sheets API
- `structlog` - Structured logging
- `redis` - Task queue (optional)

### Utilities
- `tenacity` - Retry logic
- `httpx` - Async HTTP client
- `aiofiles` - Async file operations

## 🔄 Data Flow

```
User (Telegram)
    ↓
[Block 1: Bot Interface]
    ↓
[Block 2: Task Manager] ←→ [Block 5: Logger]
    ↓
[Block 3: AI Agent]
    ↓ (paraphrased text)
[Block 4: Document Builder]
    ↓
[Block 1: Bot Interface]
    ↓
User (Telegram)
```

## 🗂️ Generated Files & Directories

These are created at runtime and excluded from Git:

- `temp_files/` - Temporary storage for uploaded and processed documents
- `logs/` - Application log files
- `credentials/` - API credentials and keys
- `paraphrase_engine.db` - SQLite database (if used)
- `*.log` - Log files

## 🔐 Security Notes

- All sensitive data in `.env` (not tracked in Git)
- Credentials directory excluded from version control
- Temporary files auto-cleaned after retention period
- Docker runs as non-root user

## 📈 Code Metrics by Block

| Block | Files | Lines | Purpose |
|-------|-------|-------|---------|
| Block 1 | 1 | 313 | User Interface |
| Block 2 | 1 | 351 | Orchestration |
| Block 3 | 2 | 586 | AI Processing |
| Block 4 | 1 | 394 | Document Processing |
| Block 5 | 1 | 481 | Logging |
| Config | 1 | 60 | Configuration |
| **Total** | **7** | **~2,185** | **Core Logic** |

## 🧪 Testing Structure

```
tests/ (to be created)
├── test_bot.py
├── test_task_manager.py
├── test_agent_core.py
├── test_document_builder.py
└── test_logger.py
```

## 📚 Documentation Files

- **README.md** (267 lines): Overview, quick start, features
- **DEPLOYMENT.md** (361 lines): Deployment instructions for various platforms
- **PROJECT_STRUCTURE.md**: This file - project organization

## 🔧 Configuration Files

- **requirements.txt**: Python package dependencies
- **Dockerfile**: Container build instructions
- **docker-compose.yml**: Multi-container orchestration
- **env.example**: Environment variable template
- **.gitignore**: Git exclusion rules

## 🎯 Development Workflow

1. **Setup**: Copy `env.example` to `.env` and configure
2. **Install**: `pip install -r requirements.txt`
3. **Test**: `python test_providers.py`
4. **Run**: `python -m paraphrase_engine.main`
5. **Deploy**: `docker-compose up -d`

---

**Last Updated**: October 21, 2025
**Version**: 1.0.0
