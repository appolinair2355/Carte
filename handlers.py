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

# Target channel ID for Baccarat Kouamé
TARGET_CHANNEL_ID = -1002682552255

# Target channel ID for predictions and updates
PREDICTION_CHANNEL_ID = -1002891656360

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

MAX_MESSAGES_PER_MINUTE = 30
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
        self.deployment_file_path = "deployer20.zip"
        # Import card_predictor locally to avoid circular imports
        try:
            from card_predictor import card_predictor
            self.card_predictor = card_predictor
        except ImportError:
            logger.error("Failed to import card_predictor")
            self.card_predictor = None

    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle incoming Telegram update with enhanced webhook support"""
        try:
            if 'message' in update:
                message = update['message']
                logger.info(f"🔄 Handlers - Traitement message normal")
                self._handle_message(message)
            elif 'edited_message' in update:
                message = update['edited_message']
                logger.info(f"🔄 Handlers - Traitement message édité pour prédictions/vérifications")
                self._handle_edited_message(message)
            else:
                logger.info(f"⚠️ Type d'update non géré: {list(update.keys())}")

        except Exception as e:
            logger.error(f"Error handling update: {e}")

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle regular messages"""
        try:
            chat_id = message['chat']['id']
            user_id = message.get('from', {}).get('id')

            # Rate limiting check (skip for channels/groups)
            chat_type = message['chat'].get('type', 'private')
            if user_id and chat_type == 'private' and is_rate_limited(user_id):
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
                elif text.startswith('/redirect'):
                    self._handle_redirect_command(chat_id, text)
                else:
                    # Handle regular messages - check for card predictions even in regular messages
                    self._handle_regular_message(message)

                    # Also process for card prediction in channels/groups (for polling mode)
                    if chat_type in ['group', 'supergroup', 'channel'] and self.card_predictor:
                        self._process_card_message(message)

            # Handle new chat members
            if 'new_chat_members' in message:
                self._handle_new_chat_members(message)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _handle_edited_message(self, message: Dict[str, Any]) -> None:
        """Handle edited messages with enhanced webhook processing for predictions and verification"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')
            user_id = message.get('from', {}).get('id')
            message_id = message.get('message_id')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id')

            logger.info(f"✏️ WEBHOOK - Message édité reçu ID:{message_id} | Chat:{chat_id} | Sender:{sender_chat_id}")

            # Rate limiting check (skip for channels/groups)
            if user_id and chat_type == 'private' and is_rate_limited(user_id):
                return

            # Process edited messages
            if 'text' in message:
                text = message['text']
                logger.info(f"✏️ WEBHOOK - Contenu édité: {text[:100]}...")

                # Skip card prediction if card_predictor is not available
                if not self.card_predictor:
                    logger.warning("❌ Card predictor not available")
                    return

                # Vérifier que c'est du canal autorisé
                if sender_chat_id != TARGET_CHANNEL_ID:
                    logger.info(f"🚫 Message édité ignoré - Canal non autorisé: {sender_chat_id}")
                    return

                logger.info(f"✅ WEBHOOK - Message édité du canal autorisé: {TARGET_CHANNEL_ID}")

                # TRAITEMENT MESSAGES ÉDITÉS - Les deux systèmes fonctionnent ici
                if self.card_predictor.has_completion_indicators(text):
                    logger.info(f"🎯 ÉDITION - Message finalisé détecté, traitement des deux systèmes")

                    # SYSTÈME 1: PRÉDICTION AUTOMATIQUE (SEULEMENT sur messages édités)
                    should_predict, game_number, combination = self.card_predictor.should_predict(text)

                    if should_predict and game_number is not None and combination is not None:
                        prediction = self.card_predictor.make_prediction(game_number, combination)
                        logger.info(f"🔮 PRÉDICTION depuis ÉDITION: {prediction}")

                        # Envoyer la prédiction au canal spécifique et stocker pour futures vérifications
                        sent_message_info = self.send_message(PREDICTION_CHANNEL_ID, prediction)
                        if sent_message_info and isinstance(sent_message_info, dict) and 'message_id' in sent_message_info:
                            next_game = game_number + 1
                            self.card_predictor.sent_predictions[next_game] = {
                                'chat_id': PREDICTION_CHANNEL_ID,
                                'message_id': sent_message_info['message_id']
                            }
                            logger.info(f"📝 Prédiction stockée pour jeu {next_game}")

                    # SYSTÈME 2: VÉRIFICATION (SEULEMENT sur messages édités)
                    verification_result = self.card_predictor.verify_prediction_from_edit(text)
                    if verification_result:
                        logger.info(f"🔍 VÉRIFICATION depuis ÉDITION: {verification_result}")
                        if verification_result['type'] == 'update_message':
                            # Essayer d'éditer le message original de prédiction
                            predicted_game = verification_result['predicted_game']
                            if predicted_game in self.card_predictor.sent_predictions:
                                message_info = self.card_predictor.sent_predictions[predicted_game]
                                edit_success = self.edit_message(
                                    PREDICTION_CHANNEL_ID,
                                    message_info['message_id'],
                                    verification_result['new_message']
                                )
                                if edit_success:
                                    logger.info(f"✅ Message de prédiction édité pour jeu {predicted_game}")
                                else:
                                    self.send_message(PREDICTION_CHANNEL_ID, verification_result['new_message'])
                            else:
                                self.send_message(PREDICTION_CHANNEL_ID, verification_result['new_message'])

                # Gestion des messages temporaires
                elif self.card_predictor.has_pending_indicators(text):
                    logger.info(f"⏰ WEBHOOK - Message temporaire détecté, en attente de finalisation")
                    if message_id:
                        self.card_predictor.pending_edits[message_id] = {
                            'original_text': text,
                            'timestamp': datetime.now()
                        }

        except Exception as e:
            logger.error(f"❌ Error handling edited message via webhook: {e}")

    def _process_card_message(self, message: Dict[str, Any]) -> None:
        """Process message for card prediction (works for both regular and edited messages)"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id')

            # Only process messages from Baccarat Kouamé channel
            if sender_chat_id != TARGET_CHANNEL_ID:
                logger.info(f"🚫 Message ignoré - Canal non autorisé: {sender_chat_id} (attendu: {TARGET_CHANNEL_ID})")
                return

            if not text or not self.card_predictor:
                return

            logger.info(f"🎯 Traitement message CANAL AUTORISÉ pour prédiction: {text[:50]}...")
            logger.info(f"📍 Canal source: {sender_chat_id} | Chat destination: {chat_id}")

            # IMPORTANT: Les messages normaux ne font PAS de prédiction ni de vérification
            # Seuls les messages ÉDITÉS déclenchent les systèmes de prédiction et vérification
            logger.info(f"📨 Message normal - AUCUNE ACTION (prédiction et vérification se font SEULEMENT sur messages édités)")

            # Store temporary messages with pending indicators
            if self.card_predictor.has_pending_indicators(text):
                message_id = message.get('message_id')
                if message_id:
                    self.card_predictor.temporary_messages[message_id] = text
                    logger.info(f"⏰ Message temporaire stocké: {message_id}")

        except Exception as e:
            logger.error(f"Error processing card message: {e}")

    def _process_completed_edit(self, message: Dict[str, Any]) -> None:
        """Process a message that was edited and now contains completion indicators"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')
            text = message['text']

            # Only process in groups/channels
            if chat_type in ['group', 'supergroup', 'channel'] and self.card_predictor:
                # Check if we should make a prediction from this completed edit
                should_predict, game_number, combination = self.card_predictor.should_predict(text)

                if should_predict and game_number is not None and combination is not None:
                    prediction = self.card_predictor.make_prediction(game_number, combination)
                    logger.info(f"Making prediction from completed edit: {prediction}")

                    # Send prediction to the chat
                    self.send_message(chat_id, prediction)

                # Also check for verification with enhanced logic for edited messages
                verification_result = self.card_predictor.verify_prediction_from_edit(text)
                if verification_result:
                    logger.info(f"Verification from completed edit: {verification_result}")

                    if verification_result['type'] == 'update_message':
                        self.send_message(chat_id, verification_result['new_message'])

        except Exception as e:
            logger.error(f"Error processing completed edit: {e}")

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
            self.send_message(chat_id, "❌ Une erreur s'est produite lors du déploiement.")

    def _handle_redirect_command(self, chat_id: int, text: str) -> None:
        """Handle /redirect command to set prediction channel"""
        try:
            parts = text.split()
            if len(parts) < 2:
                self.send_message(chat_id, "❌ Usage: /redirect <canal_id>\nExemple: /redirect -1002891656360")
                return
            
            try:
                channel_id = int(parts[1])
                # Update prediction channel in card_predictor
                if self.card_predictor:
                    # Import the module to update the global variable
                    import card_predictor as cp
                    cp.PREDICTION_CHANNEL_ID = channel_id
                    self.send_message(chat_id, f"✅ Canal de prédiction mis à jour vers: {channel_id}")
                    logger.info(f"Prediction channel updated to: {channel_id}")
                else:
                    self.send_message(chat_id, "❌ Système de prédiction non disponible")
            except ValueError:
                self.send_message(chat_id, "❌ ID de canal invalide. Utilisez un nombre entier.")
                
        except Exception as e:
            logger.error(f"Error handling redirect command: {e}")
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
            message_id = message.get('message_id')

            # In private chats, provide help
            if chat_type == 'private':
                self.send_message(
                    chat_id,
                    "🎭 Salut ! Je suis le bot de Joker.\n"
                    "Utilisez /help pour voir mes commandes disponibles.\n\n"
                    "Ajoutez-moi à un canal pour que je puisse analyser les cartes ! 🎴"
                )

            # In groups/channels, analyze for card patterns
            elif chat_type in ['group', 'supergroup', 'channel'] and self.card_predictor:
                # Check if this message has pending indicators
                if message_id and self.card_predictor.should_wait_for_edit(text, message_id):
                    logger.info(f"Message {message_id} has pending indicators, waiting for edit: {text[:50]}...")
                    # Don't process for predictions yet, wait for the edit
                    return

                # Les messages normaux dans les groupes/canaux ne font PAS de prédiction ni vérification
                # Seuls les messages ÉDITÉS déclenchent les systèmes
                logger.info(f"📨 Message normal groupe/canal - AUCUNE ACTION (systèmes actifs seulement sur éditions)")
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

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Message sent successfully to chat {chat_id}")
                return result.get('result', {})  # Return message info including message_id
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

    def edit_message(self, chat_id: int, message_id: int, new_text: str) -> bool:
        """Edit an existing message"""
        try:
            import requests

            url = f"{self.base_url}/editMessageText"
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': new_text,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Message edited successfully in chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to edit message: {result}")
                return False

        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False