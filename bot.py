"""
Telegram Bot implementation with advanced features and deployment capabilities
"""
import os
import logging
import requests
import json
from typing import Dict, Any
from handlers import TelegramHandlers
from card_predictor import card_predictor

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.deployment_file_path = "deployment.zip"
        # Initialize advanced handlers
        self.handlers = TelegramHandlers(token)
        # Cache pour stocker les noms des canaux/groupes
        self.chat_names_cache = {}
        # Nom par défaut du bot si impossible de récupérer le nom du canal
        self.default_bot_name = "🎭 Bot Joker"

    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle incoming Telegram update with advanced features for webhook mode"""
        try:
            # Log avec type de message
            if 'message' in update:
                logger.info(f"🔄 Bot traite message normal via webhook")
            elif 'edited_message' in update:
                logger.info(f"🔄 Bot traite message édité via webhook")
            
            logger.info(f"Received update: {json.dumps(update, indent=2)}")

            # Use the advanced handlers for processing (they handle card predictions too)
            self.handlers.handle_update(update)
            
            # Log succès du traitement
            logger.info(f"✅ Update traité avec succès via webhook")

        except Exception as e:
            logger.error(f"❌ Error handling update via webhook: {e}")

    def _process_card_predictions(self, message: Dict[str, Any]) -> None:
        """Process message for card predictions"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')

            # Only process card predictions in groups/channels
            if chat_type in ['group', 'supergroup', 'channel'] and 'text' in message:
                text = message['text']

                # Check if we should make a prediction
                should_predict, game_number, combination = card_predictor.should_predict(text)

                if should_predict and game_number is not None and combination is not None:
                    prediction = card_predictor.make_prediction(game_number, combination)
                    logger.info(f"Making prediction: {prediction}")

                    # Send prediction to the chat
                    self.send_message(chat_id, prediction)

                # Check if this message verifies a previous prediction
                verification_result = card_predictor.verify_prediction(text)
                if verification_result:
                    logger.info(f"Verification result: {verification_result}")

                    if verification_result['type'] == 'update_message':
                        # For webhook mode, just send the updated status as a new message
                        self.send_message(chat_id, verification_result['new_message'])

        except Exception as e:
            logger.error(f"Error processing card predictions: {e}")

    def handle_start_command(self, chat_id: int) -> None:
        """Handle /start command by sending deployment zip file"""
        try:
            # Send initial message
            self.send_message(
                chat_id, 
                "🚀 Preparing your deployment zip file... Please wait a moment."
            )

            # Check if deployment file exists
            if not os.path.exists(self.deployment_file_path):
                self.send_message(
                    chat_id,
                    "❌ Deployment file not found. Please contact the administrator."
                )
                logger.error(f"Deployment file {self.deployment_file_path} not found")
                return

            # Send the file
            success = self.send_document(chat_id, self.deployment_file_path)

            if success:
                self.send_message(
                    chat_id,
                    "✅ Deployment zip file sent successfully!\n\n"
                    "📋 Instructions:\n"
                    "1. Download the zip file\n"
                    "2. Extract it to your project directory\n"
                    "3. Deploy to render.com\n"
                    "4. Configure your environment variables\n\n"
                    "Need help? Contact support!"
                )
            else:
                self.send_message(
                    chat_id,
                    "❌ Failed to send deployment file. Please try again later."
                )

        except Exception as e:
            logger.error(f"Error handling start command: {e}")
            self.send_message(
                chat_id,
                "❌ An error occurred while processing your request. Please try again."
            )

    def send_message(self, chat_id: int, text: str, auto_adapt_name: bool = True) -> bool:
        """Send text message to user with automatic bot name adaptation"""
        try:
            # Adapter automatiquement le nom du bot au canal si demandé
            if auto_adapt_name:
                try:
                    # Vérifier si c'est un canal/groupe (ID négatif) avant d'adapter le nom
                    if chat_id < 0:  
                        self.auto_adapt_bot_name(chat_id)
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'adapter le nom du bot pour le chat {chat_id}: {e}")
            
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"✅ Message envoyé avec succès au chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Échec envoi message: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur réseau envoi message: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur envoi message: {e}")
            return False

    def send_document(self, chat_id: int, file_path: str) -> bool:
        """Send document file to user"""
        try:
            url = f"{self.base_url}/sendDocument"

            with open(file_path, 'rb') as file:
                files = {
                    'document': (os.path.basename(file_path), file, 'application/zip')
                }
                data = {
                    'chat_id': chat_id,
                    'caption': '📦 Deployment Package for render.com'
                }

                response = requests.post(url, data=data, files=files, timeout=60)
                result = response.json()

                if result.get('ok'):
                    logger.info(f"Document sent successfully to chat {chat_id}")
                    return True
                else:
                    logger.error(f"Failed to send document: {result}")
                    return False

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending document: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False

    def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL for the bot"""
        try:
            url = f"{self.base_url}/setWebhook"
            data = {
                'url': webhook_url,
                'allowed_updates': ['message', 'edited_message']
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error setting webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=30)
            result = response.json()

            if result.get('ok'):
                return result.get('result', {})
            else:
                logger.error(f"Failed to get bot info: {result}")
                return {}

        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return {}
    
    def get_chat_info(self, chat_id: int) -> dict:
        """Récupérer les informations d'un canal/groupe"""
        try:
            # Vérifier le cache d'abord
            if chat_id in self.chat_names_cache:
                return self.chat_names_cache[chat_id]
            
            url = f"{self.base_url}/getChat"
            data = {'chat_id': chat_id}
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                chat_info = result.get('result', {})
                chat_title = chat_info.get('title', 'Canal')
                
                # Stocker dans le cache
                self.chat_names_cache[chat_id] = {
                    'title': chat_title,
                    'type': chat_info.get('type', 'unknown')
                }
                
                logger.info(f"📋 Informations canal récupérées: {chat_title} (ID: {chat_id})")
                return self.chat_names_cache[chat_id]
            else:
                logger.error(f"Impossible de récupérer les infos du chat {chat_id}: {result}")
                return {'title': 'Canal', 'type': 'unknown'}
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du chat {chat_id}: {e}")
            return {'title': 'Canal', 'type': 'unknown'}
    
    def set_bot_name(self, new_name: str) -> bool:
        """Changer le nom d'affichage du bot globalement"""
        try:
            url = f"{self.base_url}/setMyName"
            data = {
                'name': new_name[:64]  # Telegram limite à 64 caractères
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Nom du bot changé en: {new_name}")
                return True
            else:
                logger.error(f"❌ Impossible de changer le nom du bot: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du changement de nom du bot: {e}")
            return False
    
    def auto_adapt_bot_name(self, chat_id: int) -> bool:
        """Adapter automatiquement le nom du bot au nom du canal/groupe"""
        try:
            chat_info = self.get_chat_info(chat_id)
            chat_title = chat_info.get('title', 'Canal')
            
            # Créer un nom de bot basé sur le nom du canal
            # Limiter à environ 50 caractères pour éviter les problèmes
            if len(chat_title) > 45:
                adapted_name = f"🎭 {chat_title[:45]}..."
            else:
                adapted_name = f"🎭 {chat_title}"
            
            # Changer le nom du bot
            success = self.set_bot_name(adapted_name)
            
            if success:
                logger.info(f"🎭 Nom du bot adapté automatiquement pour {chat_title}: {adapted_name}")
            else:
                logger.warning(f"⚠️ Impossible d'adapter le nom du bot pour {chat_title}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'adaptation automatique du nom: {e}")
            return False