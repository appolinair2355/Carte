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

# Target channel IDs for predictions and updates (supports multiple channels)
PREDICTION_CHANNEL_IDS = [-1002646551216]

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
/deploy - Obtenir le fichier de déploiement

🔧 Commandes de gestion des prédictions :
/redirect <chat_id> - Rediriger prédictions vers un canal spécifique
/redirect reset - Restaurer la configuration par défaut
/status - Afficher l'état du système de prédictions
/test - Tester l'envoi vers les canaux configurés

🔮 Fonctionnalités avancées :
- Analyse automatique des messages avec combinaisons de cartes
- Prédictions basées sur les patterns détectés (3 costumes différents)
- Gestion intelligente des messages édités
- Support multi-canaux avec redirection flexible
- Adaptation automatique du nom du bot par canal

🎴 Format des cartes :
Le bot reconnaît les symboles : ♠️ ♥️ ♦️ ♣️

📊 Détection automatique :
Messages avec format #NXXX → Analyse pour prédictions automatiques
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
        self.deployment_file_path = "deployment.zip"
        # Import card_predictor locally to avoid circular imports
        try:
            from card_predictor import card_predictor
            self.card_predictor = card_predictor
        except ImportError:
            logger.error("Failed to import card_predictor")
            self.card_predictor = None
        
        # Cache pour stocker les noms des canaux/groupes
        self.chat_names_cache = {}
        # Nom par défaut du bot si impossible de récupérer le nom du canal
        self.default_bot_name = "🎭 Bot Joker"
        # Redirection temporaire des prédictions (remplace la configuration globale)
        self.temp_prediction_targets = None
        
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
                elif text == '/status':
                    self._handle_status_command(chat_id)
                elif text == '/test':
                    self._handle_test_command(chat_id)
                elif text == '/cleanup':
                    self._handle_cleanup_command(chat_id)
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
                
                # TRAITEMENT MESSAGES ÉDITÉS - PRÉDICTION RAPIDE + VÉRIFICATION
                logger.info(f"🎯 ÉDITION - Message édité détecté, traitement PRÉDICTION RAPIDE + VÉRIFICATION")
                
                # SYSTÈME 1: PRÉDICTION AUTOMATIQUE RAPIDE (dès qu'il y a 3 costumes dans premier parenthèse)
                should_predict, game_number, combination = self.card_predictor.should_predict(text)
                
                if should_predict and game_number is not None and combination is not None:
                    prediction = self.card_predictor.make_prediction(game_number, combination)
                    logger.info(f"🔮 PRÉDICTION RAPIDE depuis ÉDITION: {prediction}")
                    
                    # Envoyer la prédiction à tous les canaux de destination configurés
                    sent_messages = self.send_prediction_to_all_channels(prediction)
                    if sent_messages:
                        next_game = game_number + 1
                        self.card_predictor.sent_predictions[next_game] = sent_messages
                        logger.info(f"📝 Prédictions stockées pour jeu {next_game} dans {len(sent_messages)} canaux")
                
                # SYSTÈME 2: VÉRIFICATION (sur tous les messages édités, pas seulement ceux avec indicateurs)
                verification_result = self.card_predictor.verify_prediction_from_edit(text)
                if verification_result:
                    logger.info(f"🔍 VÉRIFICATION depuis ÉDITION: {verification_result}")
                    if verification_result['type'] == 'update_message':
                        # Mettre à jour la prédiction dans tous les canaux
                        predicted_game = verification_result['predicted_game']
                        
                        # Debug: Afficher l'état des prédictions stockées
                        logger.info(f"🔍 DEBUG - Prédictions stockées: {list(self.card_predictor.sent_predictions.keys())}")
                        logger.info(f"🔍 DEBUG - État predictions dict: {list(self.card_predictor.predictions.keys())}")
                        
                        update_success = self.update_prediction_in_all_channels(
                            predicted_game,
                            verification_result['new_message']
                        )
                        if update_success:
                            logger.info(f"✅ Messages de prédiction mis à jour pour jeu {predicted_game}")
                        else:
                            logger.warning(f"⚠️ Problème mise à jour prédiction pour jeu {predicted_game}")
                
                # Gestion des messages temporaires
                if self.card_predictor.has_pending_indicators(text):
                    logger.info(f"⏰ WEBHOOK - Message temporaire détecté (mais prédiction rapide peut avoir eu lieu)")
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
            self.send_message(
                chat_id,
                "❌ Une erreur s'est produite lors du traitement de votre demande."
            )
    
    def _handle_redirect_command(self, chat_id: int, text: str) -> None:
        """Gérer la commande /redirect pour rediriger les prédictions"""
        try:
            parts = text.split()
            
            if len(parts) == 1:  # Juste /redirect
                help_text = """
🔄 <b>Commande de Redirection des Prédictions</b>

<b>Usage :</b>
• <code>/redirect &lt;chat_id&gt;</code> - Rediriger vers un seul canal
• <code>/redirect &lt;chat_id1&gt;,&lt;chat_id2&gt;</code> - Rediriger vers plusieurs canaux
• <code>/redirect reset</code> - Restaurer la configuration par défaut
• <code>/redirect status</code> - Voir la configuration actuelle

<b>Exemples :</b>
• <code>/redirect -100254391536</code>
• <code>/redirect -100254391536,-1002646551216</code>
• <code>/redirect reset</code>

📍 <b>Note :</b> La redirection est temporaire et ne persiste pas après redémarrage.
                """
                self.send_message(chat_id, help_text)
                return
            
            command = parts[1].strip()
            
            if command == "reset":
                self.temp_prediction_targets = None
                self.send_message(chat_id, 
                    f"✅ Redirection réinitialisée\n"
                    f"📍 Configuration par défaut restaurée : {PREDICTION_CHANNEL_IDS}")
            
            elif command == "status":
                active_targets = self.get_active_prediction_targets()
                is_redirected = self.temp_prediction_targets is not None
                
                status_text = f"📊 <b>État actuel des prédictions :</b>\n\n"
                
                if is_redirected:
                    status_text += f"🔄 <b>Mode :</b> Redirection temporaire\n"
                    status_text += f"📍 <b>Cibles actives :</b> {active_targets}\n"
                    status_text += f"📍 <b>Configuration par défaut :</b> {PREDICTION_CHANNEL_IDS}\n"
                else:
                    status_text += f"⚙️ <b>Mode :</b> Configuration par défaut\n"
                    status_text += f"📍 <b>Cibles actives :</b> {active_targets}\n"
                
                # Tester l'accessibilité de chaque canal
                status_text += f"\n🔍 <b>Test d'accessibilité :</b>\n"
                for i, target_id in enumerate(active_targets, 1):
                    chat_info = self.get_chat_info(target_id)
                    channel_name = chat_info.get('title', f'Canal {target_id}')
                    status = "✅ Accessible" if chat_info.get('title') != 'Canal' else "⚠️ Non accessible"
                    status_text += f"  {i}. {channel_name} (ID: {target_id}) - {status}\n"
                
                self.send_message(chat_id, status_text)
            
            else:
                # Parse chat IDs
                try:
                    if ',' in command:
                        # Multiple chat IDs
                        chat_ids = [int(id.strip()) for id in command.split(',')]
                    else:
                        # Single chat ID
                        chat_ids = [int(command)]
                    
                    # Valider les chat IDs
                    if len(chat_ids) > 5:
                        self.send_message(chat_id, "❌ Maximum 5 canaux de destination autorisés")
                        return
                    
                    # Tester l'accessibilité
                    test_results = []
                    for target_id in chat_ids:
                        chat_info = self.get_chat_info(target_id)
                        channel_name = chat_info.get('title', f'Canal {target_id}')
                        accessible = chat_info.get('title') != 'Canal'
                        test_results.append({
                            'id': target_id,
                            'name': channel_name,
                            'accessible': accessible
                        })
                    
                    # Appliquer la redirection
                    self.temp_prediction_targets = chat_ids
                    
                    # Rapport de succès
                    success_text = f"✅ <b>Redirection configurée avec succès !</b>\n\n"
                    success_text += f"📍 <b>Nouvelles cibles :</b> {chat_ids}\n"
                    success_text += f"📊 <b>Nombre de destinations :</b> {len(chat_ids)}\n\n"
                    success_text += f"🔍 <b>Test d'accessibilité :</b>\n"
                    
                    for i, result in enumerate(test_results, 1):
                        status = "✅ Accessible" if result['accessible'] else "⚠️ Non accessible"
                        success_text += f"  {i}. {result['name']} (ID: {result['id']}) - {status}\n"
                    
                    success_text += f"\n⚠️ <b>Note :</b> Configuration temporaire, utiliser <code>/redirect reset</code> pour restaurer les paramètres par défaut."
                    
                    self.send_message(chat_id, success_text)
                    
                except ValueError:
                    self.send_message(chat_id, "❌ Format invalide. Utilisez des ID numériques (ex: -100254391536)")
                
        except Exception as e:
            logger.error(f"Error in redirect command: {e}")
            self.send_message(chat_id, f"❌ Erreur lors de la redirection: {e}")
    
    def _handle_status_command(self, chat_id: int) -> None:
        """Afficher le statut complet du système de prédictions"""
        try:
            active_targets = self.get_active_prediction_targets()
            
            status_text = "📊 **État du Système de Prédictions**\n\n"
            
            # Configuration actuelle
            status_text += f"⚙️ **Configuration :**\n"
            status_text += f"  • Canal source : -1002682552255 (Baccarat Kouamé)\n"
            status_text += f"  • Destinations actives : {len(active_targets)} canaux\n"
            status_text += f"  • Mode redirection : {'✅ Actif' if self.temp_prediction_targets else '❌ Inactif'}\n\n"
            
            # Détails des destinations
            status_text += f"📍 **Canaux de destination :**\n"
            for i, target_id in enumerate(active_targets, 1):
                chat_info = self.get_chat_info(target_id)
                channel_name = chat_info.get('title', f'Canal {target_id}')
                status = "✅ Opérationnel" if chat_info.get('title') != 'Canal' else "⚠️ Inaccessible"
                status_text += f"  {i}. {channel_name}\n"
                status_text += f"     ID: {target_id} - {status}\n"
            
            # Statistiques
            if hasattr(self.card_predictor, 'sent_predictions'):
                predictions_count = len(self.card_predictor.sent_predictions)
                status_text += f"\n📈 **Statistiques :**\n"
                status_text += f"  • Prédictions stockées : {predictions_count}\n"
            
            status_text += f"\n🔧 **Commandes disponibles :**\n"
            status_text += f"  • `/redirect <id>` - Rediriger prédictions\n"
            status_text += f"  • `/test` - Tester envoi de prédiction\n"
            status_text += f"  • `/status` - Afficher ce statut\n"
            
            self.send_message(chat_id, status_text)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            self.send_message(chat_id, f"❌ Erreur lors de l'affichage du statut: {e}")
    
    def _handle_test_command(self, chat_id: int) -> None:
        """Tester l'envoi d'une prédiction vers les canaux configurés"""
        try:
            active_targets = self.get_active_prediction_targets()
            
            # Message de test
            test_prediction = f"🧪 **TEST DE PRÉDICTION** 🧪\n🔵TEST 🔵3K: statut :⏳\n📅 {datetime.now().strftime('%H:%M:%S')}"
            
            # Informer l'utilisateur du test
            self.send_message(chat_id, 
                f"🧪 **Lancement du test de prédiction...**\n"
                f"📍 Envoi vers {len(active_targets)} canaux : {active_targets}")
            
            # Envoyer le test
            sent_messages = self.send_prediction_to_all_channels(test_prediction)
            
            # Rapport des résultats
            success_count = len(sent_messages)
            total_targets = len(active_targets)
            
            result_text = f"📊 **Résultats du test :**\n\n"
            result_text += f"✅ **Succès :** {success_count}/{total_targets} canaux\n\n"
            
            # Détails par canal
            for i, target_id in enumerate(active_targets, 1):
                chat_info = self.get_chat_info(target_id)
                channel_name = chat_info.get('title', f'Canal {target_id}')
                
                if target_id in sent_messages:
                    msg_info = sent_messages[target_id]
                    result_text += f"  {i}. ✅ {channel_name}\n"
                    result_text += f"     Message ID: {msg_info.get('message_id', 'N/A')}\n"
                else:
                    result_text += f"  {i}. ❌ {channel_name}\n"
                    result_text += f"     Erreur d'envoi\n"
            
            if success_count == total_targets:
                result_text += f"\n🎉 **Test réussi !** Tous les canaux sont opérationnels."
            elif success_count > 0:
                result_text += f"\n⚠️ **Test partiel.** Vérifiez les permissions du bot dans les canaux en échec."
            else:
                result_text += f"\n❌ **Test échoué.** Aucun canal accessible. Vérifiez la configuration."
            
            self.send_message(chat_id, result_text)
            
        except Exception as e:
            logger.error(f"Error in test command: {e}")
            self.send_message(chat_id, f"❌ Erreur lors du test: {e}")
    
    def _handle_cleanup_command(self, chat_id: int) -> None:
        """Nettoyer automatiquement les canaux inaccessibles de la configuration"""
        try:
            active_targets = self.get_active_prediction_targets()
            accessible_targets = []
            removed_targets = []
            
            self.send_message(chat_id, "🧹 **Nettoyage en cours...**\nVérification de l'accessibilité des canaux...")
            
            # Tester chaque canal
            for target_id in active_targets:
                chat_info = self.get_chat_info(target_id)
                if chat_info.get('title') != 'Canal' or target_id == chat_id:
                    accessible_targets.append(target_id)
                else:
                    removed_targets.append(target_id)
            
            # Rapport des résultats
            result_text = f"📊 **Résultats du nettoyage :**\n\n"
            
            if removed_targets:
                result_text += f"🗑️ **Canaux retirés ({len(removed_targets)}) :**\n"
                for target_id in removed_targets:
                    result_text += f"  • {target_id} (inaccessible)\n"
                result_text += f"\n"
            
            if accessible_targets:
                result_text += f"✅ **Canaux conservés ({len(accessible_targets)}) :**\n"
                for target_id in accessible_targets:
                    chat_info = self.get_chat_info(target_id)
                    channel_name = chat_info.get('title', f'Canal {target_id}')
                    result_text += f"  • {channel_name} ({target_id})\n"
            else:
                result_text += f"⚠️ **Aucun canal accessible trouvé !**\n"
            
            # Appliquer le nettoyage si nécessaire
            if removed_targets:
                if self.temp_prediction_targets is not None:
                    # Mode redirection actif
                    self.temp_prediction_targets = accessible_targets
                    result_text += f"\n🔄 **Redirection mise à jour**\n"
                    result_text += f"Nouvelles cibles : {accessible_targets}\n"
                else:
                    # Suggérer de mettre à jour la configuration par défaut
                    result_text += f"\n💡 **Recommandation :**\n"
                    result_text += f"Utilisez `/redirect {','.join(map(str, accessible_targets))}` pour utiliser uniquement les canaux accessibles.\n"
            else:
                result_text += f"\n🎉 **Tous les canaux sont accessibles !**\n"
            
            self.send_message(chat_id, result_text)
            
        except Exception as e:
            logger.error(f"Error in cleanup command: {e}")
            self.send_message(chat_id, f"❌ Erreur lors du nettoyage: {e}")
    
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
    
    def send_message(self, chat_id: int, text: str, auto_adapt_name: bool = True) -> bool:
        """Send text message to user with automatic bot name adaptation"""
        try:
            import requests
            
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
                return result.get('result', {})  # Return message info including message_id
            else:
                logger.error(f"❌ Échec envoi message: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur envoi message: {e}")
            return False
    
    def send_document(self, chat_id: int, file_path: str, auto_adapt_name: bool = True) -> bool:
        """Send document file to user with automatic bot name adaptation"""
        try:
            import requests
            
            # Adapter automatiquement le nom du bot au canal si demandé
            if auto_adapt_name:
                try:
                    # Vérifier si c'est un canal/groupe (ID négatif) avant d'adapter le nom
                    if chat_id < 0:  
                        self.auto_adapt_bot_name(chat_id)
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'adapter le nom du bot pour le chat {chat_id}: {e}")
            
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
                    logger.info(f"✅ Document envoyé avec succès au chat {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Échec envoi document: {result}")
                    return False
                    
        except FileNotFoundError:
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur envoi document: {e}")
            return False
    
    def get_active_prediction_targets(self) -> list:
        """Obtenir la liste des canaux de destination actifs"""
        if self.temp_prediction_targets is not None:
            return self.temp_prediction_targets
        return PREDICTION_CHANNEL_IDS
    
    def send_prediction_to_all_channels(self, prediction_text: str) -> Dict:
        """Envoyer les prédictions à tous les canaux de destination configurés"""
        sent_messages = {}
        active_targets = self.get_active_prediction_targets()
        
        for channel_id in active_targets:
            try:
                logger.info(f"📤 Envoi prédiction vers canal {channel_id}")
                sent_message_info = self.send_message(channel_id, prediction_text)
                
                if sent_message_info and isinstance(sent_message_info, dict) and 'message_id' in sent_message_info:
                    sent_messages[channel_id] = sent_message_info
                    logger.info(f"✅ Prédiction envoyée avec succès vers {channel_id}")
                else:
                    logger.warning(f"⚠️ Échec envoi prédiction vers {channel_id}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur envoi prédiction vers {channel_id}: {e}")
        
        return sent_messages
    
    def update_prediction_in_all_channels(self, game_number: int, new_text: str) -> bool:
        """Mettre à jour une prédiction dans tous les canaux où elle a été envoyée"""
        success_count = 0
        
        if game_number in self.card_predictor.sent_predictions:
            prediction_data = self.card_predictor.sent_predictions[game_number]
            logger.info(f"🔄 Mise à jour prédiction {game_number} dans les canaux stockés: {prediction_data}")
            
            # Si c'est un dictionnaire avec plusieurs canaux
            if isinstance(prediction_data, dict):
                for channel_id, message_info in prediction_data.items():
                    if isinstance(message_info, dict) and 'message_id' in message_info:
                        try:
                            logger.info(f"🔄 Tentative mise à jour canal {channel_id}, message ID {message_info['message_id']}")
                            edit_success = self.edit_message(
                                channel_id,
                                message_info['message_id'],
                                new_text
                            )
                            if edit_success:
                                success_count += 1
                                logger.info(f"✅ Prédiction mise à jour dans canal {channel_id}")
                            else:
                                # Fallback: envoyer nouveau message DANS LE MÊME CANAL
                                logger.warning(f"⚠️ Échec édition message dans canal {channel_id}, envoi nouveau message")
                                fallback_sent = self.send_message(channel_id, new_text)
                                if fallback_sent:
                                    success_count += 1
                                    logger.info(f"📤 Nouveau message envoyé dans canal {channel_id}")
                        except Exception as e:
                            logger.error(f"❌ Erreur mise à jour canal {channel_id}: {e}")
                            # Fallback: envoyer nouveau message DANS LE MÊME CANAL
                            try:
                                fallback_sent = self.send_message(channel_id, new_text)
                                if fallback_sent:
                                    success_count += 1
                                    logger.info(f"📤 Message de fallback envoyé dans canal {channel_id}")
                            except Exception as fallback_error:
                                logger.error(f"❌ Erreur fallback canal {channel_id}: {fallback_error}")
            else:
                # Ancien format pour compatibilité - maintenir la redirection
                logger.warning("⚠️ Format ancien détecté pour la prédiction")
                if hasattr(prediction_data, 'get') and 'chat_id' in prediction_data:
                    # Format ancien avec un seul canal
                    old_channel = prediction_data.get('chat_id')
                    old_message_id = prediction_data.get('message_id')
                    
                    if old_channel and old_message_id:
                        try:
                            edit_success = self.edit_message(old_channel, old_message_id, new_text)
                            if edit_success:
                                success_count += 1
                                logger.info(f"✅ Prédiction mise à jour dans ancien format canal {old_channel}")
                            else:
                                # Fallback dans le même canal
                                fallback_sent = self.send_message(old_channel, new_text)
                                if fallback_sent:
                                    success_count += 1
                                    logger.info(f"📤 Nouveau message envoyé dans ancien format canal {old_channel}")
                        except Exception as e:
                            logger.error(f"❌ Erreur ancien format canal {old_channel}: {e}")
                else:
                    # Vraiment aucune info, utiliser les canaux actifs actuels
                    logger.info("📤 Aucune info de canal stockée, utilisation canaux actifs")
                    sent_messages = self.send_prediction_to_all_channels(new_text)
                    success_count = len(sent_messages)
        else:
            # Pas de prédiction stockée, envoyer vers les canaux configurés actuellement
            logger.info(f"📤 Aucune prédiction stockée pour jeu {game_number}, envoi vers canaux actifs")
            sent_messages = self.send_prediction_to_all_channels(new_text)
            success_count = len(sent_messages)
        
        logger.info(f"📊 Résultat mise à jour prédiction {game_number}: {success_count} canaux traités avec succès")
        return success_count > 0
    
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
    
    def get_chat_info(self, chat_id: int) -> dict:
        """Récupérer les informations d'un canal/groupe"""
        try:
            import requests
            
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
                error_msg = result.get('description', 'Erreur inconnue')
                if 'chat not found' in error_msg.lower():
                    logger.warning(f"Canal {chat_id} non trouvé ou inaccessible")
                else:
                    logger.error(f"Impossible de récupérer les infos du chat {chat_id}: {result}")
                return {'title': 'Canal', 'type': 'unknown'}
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du chat {chat_id}: {e}")
            return {'title': 'Canal', 'type': 'unknown'}
    
    def set_bot_name(self, new_name: str, chat_id: int = None) -> bool:
        """Changer le nom d'affichage du bot pour un canal/groupe spécifique ou globalement"""
        try:
            import requests
            
            # Pour changer le nom dans un chat spécifique, on utilise setChatMenuButton
            # ou mieux encore, on peut utiliser le first_name du bot
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
            success = self.set_bot_name(adapted_name, chat_id)
            
            if success:
                logger.info(f"🎭 Nom du bot adapté automatiquement pour {chat_title}: {adapted_name}")
            else:
                logger.warning(f"⚠️ Impossible d'adapter le nom du bot pour {chat_title}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'adaptation automatique du nom: {e}")
            return False