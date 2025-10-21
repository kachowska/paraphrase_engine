# Paraphrase Engine v1.0

A premium text paraphrasing service that uses multiple AI models to deliver high-quality, academically-styled text rewrites while maintaining meaning and context.

## 🎯 Overview

Paraphrase Engine v1.0 is a sophisticated text processing system designed to provide deep paraphrasing of text fragments, particularly for academic and scientific content. The system leverages multiple AI providers in parallel to generate the best possible paraphrases, all while presenting a simple, user-friendly interface through Telegram.

## 🏗️ Architecture

The system is built with a modular architecture consisting of five main blocks:

### Block 1: Telegram Bot Interface
- User-facing interface via Telegram
- Simple, guided workflow
- No technical choices exposed to users

### Block 2: Task Management Core
- Orchestrates the entire paraphrasing pipeline
- Manages task lifecycle and state
- Handles asynchronous processing

### Block 3: Paraphrasing Agent Core (The "Secret Sauce")
- Multi-AI parallel processing
- Intelligent evaluation and selection
- Final humanization stage
- Supports OpenAI, Anthropic Claude, and Google Gemini

### Block 4: Document Builder
- Intelligent .docx document processing
- Format-preserving text replacement
- Reverse-order processing for accuracy

### Block 5: Logging and Monitoring
- Comprehensive operation logging
- Google Sheets integration for analytics
- Performance monitoring and error tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token
- At least one AI provider API key (OpenAI, Anthropic, or Google)
- (Optional) Google Sheets API credentials for logging

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd paraphrase_engine
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Configure your environment variables:
```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
SECRET_KEY=your_secret_key

# At least one AI provider (can configure multiple)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# Optional - Google Sheets logging
GOOGLE_SHEETS_CREDENTIALS_PATH=path/to/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

### Running the Application

#### Local Development
```bash
python -m paraphrase_engine.main
```

#### Using Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 📱 Usage

1. **Start the bot**: Send `/start` to your Telegram bot
2. **Upload document**: Send a .docx file when prompted
3. **Provide fragments**: Enter the text fragments to be paraphrased (each on a new line)
4. **Receive results**: The bot will process and return your document with paraphrased text

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot authentication token | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | No* | - |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | No* | - |
| `GOOGLE_API_KEY` | Google Gemini API key | No* | - |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | No | 10 |
| `FILE_RETENTION_HOURS` | Hours to retain files | No | 24 |
| `AI_TEMPERATURE` | AI generation temperature | No | 0.7 |
| `AI_MAX_TOKENS` | Maximum tokens per generation | No | 2000 |

*At least one AI provider key is required

### Google Sheets Logging

To enable Google Sheets logging:

1. Create a Google Cloud Project
2. Enable Google Sheets API
3. Create a service account and download credentials JSON
4. Share your spreadsheet with the service account email
5. Set `GOOGLE_SHEETS_CREDENTIALS_PATH` and `GOOGLE_SHEETS_SPREADSHEET_ID`

## 🧪 Development

### Project Structure
```
paraphrase_engine/
├── block1_telegram_bot/    # Telegram interface
├── block2_orchestrator/     # Task management
├── block3_paraphrasing/     # AI paraphrasing core
├── block4_document/         # Document processing
├── block5_logging/          # Logging system
├── config/                  # Configuration
├── temp_files/             # Temporary storage
├── logs/                   # Application logs
└── main.py                 # Entry point
```

### Testing

Run tests:
```bash
pytest tests/
```

### Adding New AI Providers

1. Create a new provider class in `block3_paraphrasing/ai_providers.py`
2. Inherit from `AIProvider` base class
3. Implement `_initialize_client()` and `generate()` methods
4. Add initialization logic in `ParaphrasingAgent._initialize_providers()`

## 📊 Monitoring

The system provides comprehensive logging through:

- **Local logs**: JSON-formatted logs in `logs/` directory
- **Google Sheets**: Real-time analytics dashboard
- **Structured logging**: Using structlog for detailed tracing

### Log Categories

- **Tasks**: Task lifecycle and status
- **Operations**: API calls and processing steps
- **Results**: Original and paraphrased text pairs
- **Errors**: Detailed error tracking with context

## 🚢 Deployment

### Production Checklist

- [ ] Set `APP_ENV=production`
- [ ] Configure strong `SECRET_KEY`
- [ ] Set up SSL/TLS for webhooks (if using)
- [ ] Configure monitoring and alerting
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Set up log rotation
- [ ] Configure firewall rules

### Recommended Deployment

1. **VPS Deployment** (DigitalOcean, Vultr, etc.):
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone and configure
git clone <repository>
cd paraphrase_engine
cp .env.example .env
# Edit .env with production values

# Run with Docker Compose
docker-compose up -d
```

2. **Cloud Platform** (Google Cloud Run, AWS ECS, etc.):
- Build and push Docker image
- Configure environment variables
- Deploy container with appropriate resources

## 🔒 Security Considerations

- All API keys are stored as environment variables
- User files are automatically deleted after retention period
- No user data is permanently stored
- All operations are logged for audit purposes
- Docker runs as non-root user

## 📈 Performance

- Parallel AI processing for optimal speed
- Asynchronous task handling
- Efficient document processing
- Automatic retry logic for API failures
- Resource cleanup after task completion

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Your License Here]

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the development team

## 🗺️ Roadmap

### Version 1.1 (Planned)
- [ ] Web interface alternative to Telegram
- [ ] Batch processing support
- [ ] Additional language support
- [ ] Custom style templates

### Version 2.0 (Future)
- [ ] Machine learning-based quality scoring
- [ ] Custom model fine-tuning
- [ ] API endpoint for third-party integration
- [ ] Advanced analytics dashboard

---

**Note**: This is a premium service positioned as "manual rewriting" to end users. All technical complexity is intentionally hidden from the user interface.
