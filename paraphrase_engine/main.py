"""
Main entry point for Paraphrase Engine v1.0
"""

import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

from .config import settings
from .block1_telegram_bot import TelegramBotInterface

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('paraphrase_engine.log')
    ]
)

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"paraphrase-engine"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def start_health_server(port):
    """Start a simple HTTP server for health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()


def main():
    """Main application entry point"""
    logger.info("=" * 60)
    logger.info("Starting Paraphrase Engine v1.0")
    logger.info("=" * 60)
    
    # Log configuration
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Max file size: {settings.max_file_size_mb}MB")
    logger.info(f"File retention: {settings.file_retention_hours} hours")
    
    # Check required configurations
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        sys.exit(1)
    
    # Check AI provider configuration
    providers_configured = []
    if settings.openai_api_key:
        providers_configured.append("OpenAI")
    if settings.anthropic_api_key:
        providers_configured.append("Anthropic")
    if settings.google_api_key:
        providers_configured.append("Google Gemini")
    
    if not providers_configured:
        logger.error("No AI providers configured! At least one API key is required.")
        sys.exit(1)
    
    logger.info(f"AI Providers configured: {', '.join(providers_configured)}")
    
    # Check Google Sheets configuration
    if settings.google_sheets_credentials_path and settings.google_sheets_spreadsheet_id:
        logger.info("Google Sheets logging configured")
    else:
        logger.warning("Google Sheets not configured - using local logging only")
    
    try:
        # Start health check server in a separate thread
        port = int(os.getenv('PORT', '10000'))
        health_thread = threading.Thread(target=start_health_server, args=(port,), daemon=True)
        health_thread.start()
        logger.info(f"Health check server running on port {port}")
        
        # Create and run the bot
        bot = TelegramBotInterface()
        logger.info("Starting Telegram bot...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Paraphrase Engine stopped")


if __name__ == "__main__":
    main()
