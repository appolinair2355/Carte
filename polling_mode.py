#!/usr/bin/env python3
"""
Mode polling pour traiter les messages Telegram en développement
"""
import time
import requests
import json
import logging
from bot import TelegramBot
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Mode polling pour développement"""
    config = Config()
    bot = TelegramBot(config.BOT_TOKEN)
    
    logger.info("🔄 Démarrage du bot en mode polling")
    logger.info(f"🎯 Canal cible: {-1002682552255}")
    logger.info("🔍 Traitement des messages pour prédictions et vérifications")
    
    offset = 0
    
    while True:
        try:
            # Récupérer les updates
            url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUpdates"
            params = {
                'offset': offset,
                'limit': 10,
                'timeout': 30
            }
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                updates = data['result'] 
                
                for update in updates:
                    update_id = update.get('update_id')
                    offset = max(offset, update_id + 1)
                    
                    # Log du type d'update
                    if 'message' in update:
                        logger.info(f"📨 POLLING - Message normal reçu (ID: {update_id})")
                    elif 'edited_message' in update:
                        logger.info(f"✏️ POLLING - Message édité reçu (ID: {update_id})")
                    
                    # Traiter l'update
                    bot.handle_update(update)
                    
            time.sleep(1)  # Petite pause entre les requêtes
            
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du bot demandé")
            break
        except Exception as e:
            logger.error(f"❌ Erreur polling: {e}")
            time.sleep(5)  # Pause plus longue en cas d'erreur

if __name__ == "__main__":
    main()