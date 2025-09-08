"""
Event handlers for the Telegram bot - adapted for webhook deployment
"""

import logging
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Rate limiting storage
user_message_counts = defaultdict(list)

# Configuration constants
GREETING_MESSAGE = """
🎭 Salut ! Je suis le bot de Joker !
Ajoutez-moi à votre canal pour que je puisse saluer tout le monde ! 👋

🔮 Je peux analyser les combinaisons de cartes et faire des prédictions !
Utilisez /help pour voir toutes mes commandes.
"""

WELCOME_MESSAGE = """
🎭 Bienvenue dans le monde de Joker ! 

🎯 Commandes disponibles :
/start - Accueil
/help - Aide détaillée  
/about - À propos du bot
/dev - Informations développeur
/deploy - Obtenir le fichier de déploiement

🔮 Fonctionnalités spéciales :
- Prédictions de cartes automatiques
- Analyse des combinaisons
- Gestion des canaux et groupes
"""

HELP_MESSAGE = """
🎯 Guide d'utilisation du Bot Joker :

📝 Commandes de base :
/start - Message d'accueil
/help - Afficher cette aide
/about - Informations sur le bot
/dev - Contact développeur

🔮 Fonctionnalités avancées :
- Le bot analyse automatiquement les messages contenant des combinaisons de cartes
- Il fait des prédictions basées sur les patterns détectés
- Gestion intelligente des messages édités
- Support des canaux et groupes

🎴 Format des cartes :
Le bot reconnaît les symboles : ♠️ ♥️ ♦️ ♣️

📊 Le bot peut traiter les messages avec format #nXXX pour identifier les jeux.
"""

ABOUT_MESSAGE = """
🎭 Bot Joker - Prédicteur de Cartes

🤖 Version : 2.0
🛠️ Développé avec Python et l'API Telegram
🔮 Spécialisé dans l'analyse de combinaisons de cartes

✨ Fonctionnalités :
- Prédictions automatiques
- Analyse de patterns
- Support multi-canaux
- Interface intuitive

🌟 Créé pour améliorer votre expérience de jeu !
"""

DEV_MESSAGE = """
👨‍💻 Informations Développeur :

🔧 Technologies utilisées :
- Python 3.11+
- API Telegram Bot
- Flask pour les webhooks
- Déployé sur Render.com

📧 Contact : 
Pour le support technique ou les suggestions d'amélioration, 
contactez l'administrateur du bot.

🚀 Le bot est open source et peut être déployé facilement !
"""

MAX_MESSAGES_PER_MINUTE = 10
RATE_LIMIT_WINDOW = 60

def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    now = datetime.now()
    user_messages = user_message_counts[user_id]

    # Remove old messages outside the window
    user_messages[:] = [msg_time for msg_time in user_messages 
                       if now - msg_time < timedelta(seconds=RATE_LIMIT_WINDOW)]

    # Check if user exceeded limit
    if len(user_messages) >= MAX_MESSAGES_PER_MINUTE:
        return True

    # Add current message time
    user_messages.append(now)
    return False

class TelegramHandlers:
    """Handlers for Telegram bot using webhook approach"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.deployment_file_path = "deployment.zip"
        
    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle incoming Telegram update"""
        try:
            if 'message' in update:
                message = update['message']
                self._handle_message(message)
            elif 'edited_message' in update:
                message = update['edited_message']
                self._handle_edited_message(message)
                
        except Exception as e:
            logger.error(f"Error handling update: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle regular messages"""
        try:
            chat_id = message['chat']['id']
            user_id = message.get('from', {}).get('id')
            
            # Rate limiting check
            if user_id and is_rate_limited(user_id):
                self.send_message(chat_id, "⏰ Veuillez patienter avant d'envoyer une autre commande.")
                return
            
            # Handle commands
            if 'text' in message:
                text = message['text'].strip()
                
                if text == '/start':
                    self._handle_start_command(chat_id)
                elif text == '/help':
                    self.send_message(chat_id, HELP_MESSAGE)
                elif text == '/about':
                    self.send_message(chat_id, ABOUT_MESSAGE)
                elif text == '/dev':
                    self.send_message(chat_id, DEV_MESSAGE)
                elif text == '/deploy':
                    self._handle_deploy_command(chat_id)
                else:
                    # Handle regular messages
                    self._handle_regular_message(message)
            
            # Handle new chat members
            if 'new_chat_members' in message:
                self._handle_new_chat_members(message)
                        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _handle_edited_message(self, message: Dict[str, Any]) -> None:
        """Handle edited messages"""
        try:
            chat_id = message['chat']['id']
            user_id = message.get('from', {}).get('id')
            
            # Rate limiting check
            if user_id and is_rate_limited(user_id):
                return
            
            # Process edited messages for card predictions
            if 'text' in message:
                # Here you could add card prediction logic
                logger.info(f"Edited message in chat {chat_id}: {message['text'][:50]}...")
                
        except Exception as e:
            logger.error(f"Error handling edited message: {e}")
    
    def _handle_start_command(self, chat_id: int) -> None:
        """Handle /start command"""
        try:
            self.send_message(chat_id, WELCOME_MESSAGE)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            self.send_message(chat_id, "❌ Une erreur s'est produite. Veuillez réessayer.")
    
    def _handle_deploy_command(self, chat_id: int) -> None:
        """Handle /deploy command by sending deployment zip file"""
        try:
            # Send initial message
            self.send_message(
                chat_id, 
                "🚀 Préparation du fichier de déploiement... Veuillez patienter."
            )
            
            # Check if deployment file exists
            if not os.path.exists(self.deployment_file_path):
                self.send_message(
                    chat_id,
                    "❌ Fichier de déploiement non trouvé. Contactez l'administrateur."
                )
                logger.error(f"Deployment file {self.deployment_file_path} not found")
                return
            
            # Send the file
            success = self.send_document(chat_id, self.deployment_file_path)
            
            if success:
                self.send_message(
                    chat_id,
                    "✅ Fichier de déploiement envoyé avec succès !\n\n"
                    "📋 Instructions de déploiement :\n"
                    "1. Téléchargez le fichier zip\n"
                    "2. Créez un nouveau service sur render.com\n"
                    "3. Uploadez le zip ou connectez votre repository\n"
                    "4. Configurez les variables d'environnement :\n"
                    "   - BOT_TOKEN : Votre token de bot\n"
                    "   - WEBHOOK_URL : https://votre-app.onrender.com\n"
                    "   - PORT : 10000\n\n"
                    "🎯 Votre bot sera déployé automatiquement !"
                )
            else:
                self.send_message(
                    chat_id,
                    "❌ Échec de l'envoi du fichier. Réessayez plus tard."
                )
                
        except Exception as e:
            logger.error(f"Error handling deploy command: {e}")
            self.send_message(
                chat_id,
                "❌ Une erreur s'est produite lors du traitement de votre demande."
            )
    
    def _handle_regular_message(self, message: Dict[str, Any]) -> None:
        """Handle regular text messages"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')
            text = message.get('text', '')
            
            # In private chats, provide help
            if chat_type == 'private':
                self.send_message(
                    chat_id,
                    "🎭 Salut ! Je suis le bot de Joker.\n"
                    "Utilisez /help pour voir mes commandes disponibles.\n\n"
                    "Ajoutez-moi à un canal pour que je puisse analyser les cartes ! 🎴"
                )
            
            # In groups/channels, analyze for card patterns
            elif chat_type in ['group', 'supergroup', 'channel']:
                # Here you could add card prediction logic
                # For now, just log the activity
                logger.info(f"Group message in {chat_id}: {text[:50]}...")
                
        except Exception as e:
            logger.error(f"Error handling regular message: {e}")
    
    def _handle_new_chat_members(self, message: Dict[str, Any]) -> None:
        """Handle when bot is added to a channel or group"""
        try:
            chat_id = message['chat']['id']
            chat_title = message['chat'].get('title', 'ce chat')
            
            for member in message['new_chat_members']:
                # Check if our bot was added (we can't know our own ID easily in webhook mode)
                # So we'll just send greeting when any bot is added
                if member.get('is_bot', False):
                    logger.info(f"Bot added to chat {chat_id}: {chat_title}")
                    self.send_message(chat_id, GREETING_MESSAGE)
                    break
                    
        except Exception as e:
            logger.error(f"Error handling new chat members: {e}")
    
    def send_message(self, chat_id: int, text: str) -> bool:
        """Send text message to user"""
        try:
            import requests
            
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Message sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_document(self, chat_id: int, file_path: str) -> bool:
        """Send document file to user"""
        try:
            import requests
            
            url = f"{self.base_url}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {
                    'document': (os.path.basename(file_path), file, 'application/zip')
                }
                data = {
                    'chat_id': chat_id,
                    'caption': '📦 Package de déploiement pour render.com\n\n🎯 Tout est inclus pour déployer votre bot !'
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
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False