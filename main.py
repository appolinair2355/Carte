"""
Main entry point for the Telegram bot deployment on render.com
"""
import os
import logging
from flask import Flask, request
from bot import TelegramBot
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize bot
config = Config()
bot = TelegramBot(config.BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        update = request.get_json()
        if update:
            bot.handle_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for render.com"""
    return {'status': 'healthy', 'service': 'telegram-bot'}, 200

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return {'message': 'Telegram Bot is running', 'status': 'active'}, 200

def setup_webhook():
    """Set up webhook on startup"""
    try:
        webhook_url = os.getenv('WEBHOOK_URL')
        if webhook_url:
            success = bot.set_webhook(f"{webhook_url}/webhook")
            if success:
                logger.info(f"Webhook set successfully to {webhook_url}/webhook")
            else:
                logger.error("Failed to set webhook")
        else:
            logger.warning("WEBHOOK_URL not provided, webhook not set")
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")

if __name__ == '__main__':
    # Set up webhook on startup
    setup_webhook()
    
    # Get port from environment (render.com provides this)
    port = int(os.getenv('PORT', 10000))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
