"""
Configuration settings for the Telegram bot
"""
import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        self.BOT_TOKEN = self._get_bot_token()
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
        self.PORT = int(os.getenv('PORT', 10000))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Validate configuration
        self._validate_config()
    
    def _get_bot_token(self) -> str:
        """Get bot token from environment variables"""
        token = os.getenv('BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN', ''))
        
        if not token:
            logger.error("Bot token not found in environment variables")
            raise ValueError(
                "Bot token is required. Set BOT_TOKEN or TELEGRAM_BOT_TOKEN environment variable."
            )
        
        return token
    
    def _validate_config(self) -> None:
        """Validate configuration settings"""
        if not self.BOT_TOKEN:
            raise ValueError("Bot token is required")
        
        if len(self.BOT_TOKEN.split(':')) != 2:
            raise ValueError("Invalid bot token format")
        
        if self.WEBHOOK_URL and not self.WEBHOOK_URL.startswith('https://'):
            logger.warning("Webhook URL should use HTTPS for production")
        
        logger.info("Configuration validated successfully")
    
    def get_webhook_url(self) -> str:
        """Get full webhook URL"""
        if self.WEBHOOK_URL:
            return f"{self.WEBHOOK_URL}/webhook"
        return ""
    
    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        return f"Config(webhook_url={self.WEBHOOK_URL}, port={self.PORT}, debug={self.DEBUG})"
