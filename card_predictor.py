"""
Card prediction logic for Joker's Telegram Bot - simplified for webhook deployment
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Configuration constants
VALID_CARD_COMBINATIONS = [
    "♠️♥️♦️", "♠️♥️♣️", "♠️♦️♣️", "♥️♦️♣️"
]

CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️", "❤️"]  # Include both ♥️ and ❤️ variants

PREDICTION_MESSAGE = "🔵{numero} 🔵3K: statut :⏳"

# Target channel ID for Baccarat Kouamé
TARGET_CHANNEL_ID = -1002682552255

# Target channel ID for predictions and updates
PREDICTION_CHANNEL_ID = -1002891656360

class CardPredictor:
    """Handles card prediction logic for webhook deployment"""

    def __init__(self):
        self.predictions = {}  # Store predictions for verification
        self.processed_messages = set()  # Avoid duplicate processing
        self.sent_predictions = {}  # Store sent prediction messages for editing
        self.temporary_messages = {}  # Store temporary messages waiting for final edit
        self.pending_edits = {}  # Store messages waiting for edit with indicators

    def reset_predictions(self):
        """Reset all prediction states - useful for recalibration"""
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        logger.info("🔄 Système de prédictions réinitialisé")

    def extract_game_number(self, message: str) -> Optional[int]:
        """Extract game number from message like #n744 or #N744"""
        pattern = r'#[nN](\d+)'
        match = re.search(pattern, message)
        if match:
            return int(match.group(1))
        return None

    def extract_cards_from_parentheses(self, message: str) -> List[str]:
        """Extract cards from first and second parentheses"""
        # This method is deprecated, use extract_card_symbols_from_parentheses instead
        return []

    def has_pending_indicators(self, text: str) -> bool:
        """Check if message contains indicators suggesting it will be edited"""
        indicators = ['⏰', '▶', '🕐', '➡️']
        return any(indicator in text for indicator in indicators)

    def has_completion_indicators(self, text: str) -> bool:
        """Check if message contains completion indicators after edit"""
        completion_indicators = ['✅', '🔰']
        return any(indicator in text for indicator in completion_indicators)

    def should_wait_for_edit(self, text: str, message_id: int) -> bool:
        """Determine if we should wait for this message to be edited"""
        if self.has_pending_indicators(text):
            # Store this message as pending edit
            self.pending_edits[message_id] = {
                'original_text': text,
                'timestamp': datetime.now()
            }
            return True
        return False

    def extract_suits(self, parentheses_content: str) -> List[str]:
        """Extract unique card suits from parentheses content"""
        # Normalize ❤️ to ♥️ for consistency
        normalized_content = parentheses_content.replace("❤️", "♥️")
        
        # Extract only unique card symbols (costumes) from this section
        unique_symbols = []
        for symbol in ["♠️", "♥️", "♦️", "♣️"]:
            if symbol in normalized_content:
                unique_symbols.append(symbol)
        
        return unique_symbols

    def extract_card_symbols_from_parentheses(self, text: str) -> List[List[str]]:
        """Extract unique card symbols from each parentheses section"""
        # Find all parentheses content
        pattern = r'\(([^)]+)\)'
        matches = re.findall(pattern, text)

        all_sections = []
        for match in matches:
            # Normalize ❤️ to ♥️ for consistency
            normalized_content = match.replace("❤️", "♥️")

            # Extract only unique card symbols (costumes) from this section
            unique_symbols = set()
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                if symbol in normalized_content:
                    unique_symbols.add(symbol)

            all_sections.append(list(unique_symbols))

        return all_sections

    def has_three_different_cards(self, cards: List[str]) -> bool:
        """Check if there are exactly 3 different card symbols"""
        unique_cards = list(set(cards))
        logger.info(f"Checking cards: {cards}, unique: {unique_cards}, count: {len(unique_cards)}")
        return len(unique_cards) == 3

    def is_temporary_message(self, message: str) -> bool:
        """Check if message contains temporary progress emojis"""
        temporary_emojis = ['⏰', '▶', '🕐', '➡️']
        return any(emoji in message for emoji in temporary_emojis)

    def is_final_message(self, message: str) -> bool:
        """Check if message contains final completion emojis"""
        final_emojis = ['✅', '🔰']
        return any(emoji in message for emoji in final_emojis)

    def get_card_combination(self, cards: List[str]) -> Optional[str]:
        """Get the combination of 3 different cards"""
        unique_cards = list(set(cards))
        if len(unique_cards) == 3:
            combination = ''.join(sorted(unique_cards))
            logger.info(f"Card combination found: {combination} from cards: {unique_cards}")

            # Check if this combination matches any valid pattern
            for valid_combo in VALID_CARD_COMBINATIONS:
                if set(combination) == set(valid_combo):
                    logger.info(f"Valid combination matched: {valid_combo}")
                    return combination

            # Accept any 3 different cards as valid
            logger.info(f"Accepting 3 different cards as valid: {combination}")
            return combination
        return None

    def should_predict(self, text: str) -> tuple:
        """
        Determine if we should make a prediction based on the message content.
        NOUVELLE RÈGLE: Quand le PREMIER parenthèse contient exactement 3 costumes différents,
        génère une prédiction SEULEMENT si le DEUXIÈME parenthèse ne contient PAS 3 costumes différents.
        Returns tuple: (should_predict: bool, game_number: int or None, combination: str or None)
        """
        try:
            if not self.has_completion_indicators(text):
                return False, None, None

            game_number = self.extract_game_number(text)
            if game_number is None:
                return False, None, None

            logger.info(f"🔮 Jeu {game_number}: Message final détecté (✅ ou 🔰)")

            # Find all parentheses in the message
            parentheses_matches = re.findall(r'\(([^)]+)\)', text)
            if not parentheses_matches:
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Aucune parenthèse trouvée")
                return False, None, None

            if len(parentheses_matches) < 1:
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Pas assez de parenthèses")
                return False, None, None

            # Analyser le premier parenthèse
            first_parenthesis = parentheses_matches[0]
            first_suits = self.extract_suits(first_parenthesis)
            first_unique_suits = list(set(first_suits))
            logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Premier parenthèse a {len(first_unique_suits)} costumes: {first_unique_suits}")

            # Vérifier si le premier parenthèse a exactement 3 costumes
            if len(first_unique_suits) != 3:
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ❌ Premier parenthèse n'a pas exactement 3 costumes")
                return False, None, None

            logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ✅ Premier parenthèse a 3 costumes différents")

            # Vérifier s'il y a un deuxième parenthèse
            if len(parentheses_matches) >= 2:
                second_parenthesis = parentheses_matches[1]
                second_suits = self.extract_suits(second_parenthesis)
                second_unique_suits = list(set(second_suits))
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Deuxième parenthèse a {len(second_unique_suits)} costumes: {second_unique_suits}")

                if len(second_unique_suits) == 3:
                    logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ❌ BLOQUÉ - Les deux parenthèses ont 3 costumes différents")
                    return False, None, None
                else:
                    logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ✅ Deuxième parenthèse n'a pas 3 costumes, prédiction autorisée")
            else:
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ✅ Un seul parenthèse, prédiction autorisée")

            # Prevent duplicate predictions for the same game
            next_game = game_number + 1
            if next_game in self.predictions:
                logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: ⚠️ Prédiction déjà existante pour jeu {next_game}")
                return False, None, None

            logger.info(f"🔮 RÈGLE PRÉDICTION RESPECTÉE: Premier parenthèse avec 3 costumes ET deuxième parenthèse sans 3 costumes → génère prédiction pour jeu {next_game}")
            logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: GÉNÉRATION AUTORISÉE")
            combination = ''.join(first_unique_suits)
            return True, game_number, combination

        except Exception as e:
            logger.error(f"Error in should_predict: {e}")
            return False, None, None

    def make_prediction(self, game_number: int, combination: str) -> str:
        """Make a prediction for the next game"""
        next_game = game_number + 1
        prediction_text = PREDICTION_MESSAGE.format(numero=next_game)

        # Store the prediction for later verification
        self.predictions[next_game] = {
            'combination': combination,
            'status': 'pending',
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': prediction_text
        }

        logger.info(f"Made prediction for game {next_game} based on combination {combination}")
        return prediction_text

    def count_cards_in_winning_parentheses(self, message: str) -> int:
        """Count the number of card symbols in the parentheses that has the ✅ symbol"""
        # Split message at ✅ to find which section won
        if '✅' not in message:
            return 0

        # Find the parentheses after ✅
        checkmark_pos = message.find('✅')
        remaining_text = message[checkmark_pos:]

        # Extract parentheses content after ✅
        pattern = r'\(([^)]+)\)'
        match = re.search(pattern, remaining_text)

        if match:
            winning_content = match.group(1)
            # Normalize ❤️ to ♥️ for consistent counting
            normalized_content = winning_content.replace("❤️", "♥️")
            card_count = 0
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                card_count += normalized_content.count(symbol)
            logger.info(f"Found ✅ winning section: {winning_content}, card count: {card_count}")
            return card_count

        return 0

    def count_cards_in_first_parentheses(self, message: str) -> int:
        """Count the total number of card symbols in the first parentheses"""
        # Find first parentheses content
        pattern = r'\(([^)]+)\)'
        match = re.search(pattern, message)

        if match:
            first_content = match.group(1)
            # Normalize ❤️ to ♥️ for consistent counting
            normalized_content = first_content.replace("❤️", "♥️")
            card_count = 0
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                card_count += normalized_content.count(symbol)
            logger.info(f"Found first parentheses: {first_content}, card count: {card_count}")
            return card_count

        return 0

    def verify_prediction(self, message: str) -> Optional[Dict]:
        """Verify if a prediction was correct (regular messages)"""
        return self._verify_prediction_common(message, is_edited=False)

    def verify_prediction_from_edit(self, message: str) -> Optional[Dict]:
        """Verify if a prediction was correct from edited message (enhanced verification)"""
        return self._verify_prediction_common(message, is_edited=True)

    def _verify_prediction_common(self, message: str, is_edited: bool = False) -> Optional[Dict]:
        """Common verification logic - ONLY VERIFIES on EDITED messages, checks FIRST parentheses only"""
        game_number = self.extract_game_number(message)
        if not game_number:
            return None

        logger.info(f"🔍 VÉRIFICATION SEULEMENT - Jeu {game_number} (édité: {is_edited})")

        # Vérifier TOUTES les prédictions en attente, priorité au jeu exact puis séquentiellement
        predictions_to_check = []

        # Synchroniser sent_predictions avec predictions
        for predicted_game, message_info in self.sent_predictions.items():
            if predicted_game not in self.predictions:
                self.predictions[predicted_game] = {
                    'status': 'pending',
                    'message_info': message_info
                }
            predictions_to_check.append(predicted_game)

        # Ajouter prédictions existantes
        for predicted_game in self.predictions.keys():
            if predicted_game not in predictions_to_check:
                predictions_to_check.append(predicted_game)

        # Trier par ordre de priorité : jeu exact d'abord, puis séquentiel
        predictions_to_check = sorted(predictions_to_check)

        # VÉRIFICATION SÉQUENTIELLE - Continue jusqu'à trouver une correspondance
        for predicted_game in predictions_to_check:
            prediction = self.predictions.get(predicted_game, {})
            prediction_status = prediction.get('status', 'pending')

            # Passer les prédictions déjà traitées
            if prediction_status != 'pending':
                continue

            verification_offset = game_number - predicted_game
            logger.info(f"🔍 Vérification prédiction {predicted_game} vs jeu actuel {game_number}, décalage: {verification_offset}")

            # VÉRIFICATION DANS LA FENÊTRE 0-3 (jeu exact, +1, +2, +3)
            if 0 <= verification_offset <= 3:
                has_success_symbol = '✅' in message or '🔰' in message
                logger.info(f"🔍 VÉRIFICATION - Jeu {game_number}: Symbole succès: {has_success_symbol}, Édité: {is_edited}")
                logger.info(f"🔍 SYSTÈME DE VÉRIFICATION: Vérifie si jeu prédit {predicted_game} correspond au jeu actuel {game_number}")

                # SYSTÈME DE VÉRIFICATION: SEULEMENT sur messages édités avec symbole succès
                if has_success_symbol and is_edited:
                    # RÈGLE CRITIQUE: Vérifier UNIQUEMENT le PREMIER parenthèse pour exactement 3 CARTES (pas costumes)
                    first_parentheses_card_count = self.count_cards_in_first_parentheses(message)
                    first_parentheses_valid = first_parentheses_card_count == 3

                    logger.info(f"🔍 PREMIER parenthèse: {first_parentheses_card_count} cartes au total")

                    if first_parentheses_valid:
                        # Succès trouvé - déterminer le statut selon le décalage
                        status_map = {0: '✅0️⃣', 1: '✅1️⃣', 2: '✅2️⃣', 3: '✅3️⃣'}
                        new_status = status_map[verification_offset]

                        logger.info(f"🔍 ✅ VÉRIFICATION RÉUSSIE - PREMIER parenthèse a exactement 3 cartes")
                        logger.info(f"🔍 RÈGLE VÉRIFICATION RESPECTÉE: Prédiction {predicted_game} trouvée au jeu {game_number} (décalage {verification_offset}) → {new_status}")

                        original_message = f"🔵{predicted_game} 🔵3K: statut :⏳"
                        updated_message = f"🔵{predicted_game} 🔵3K: statut :{new_status}"

                        prediction['status'] = 'correct'
                        prediction['verification_count'] = verification_offset
                        prediction['final_message'] = updated_message

                        logger.info(f"🔍 ✅ Prédiction {predicted_game} VÉRIFIÉE avec succès (décalage {verification_offset})")
                        logger.info(f"🔍 📝 Message à mettre à jour: '{original_message}' → '{updated_message}'")
                        logger.info(f"🔍 🛑 ARRÊT de vérification - Succès trouvé pour prédiction {predicted_game}")

                        return {
                            'type': 'update_message',
                            'predicted_game': predicted_game,
                            'new_message': updated_message,
                            'original_message': original_message
                        }
                    else:
                        # Premier parenthèse n'a pas 3 cartes - continuer à vérifier jeux suivants
                        logger.info(f"🔍 ⏳ CONTINUE - PREMIER parenthèse a seulement {first_parentheses_card_count} cartes (besoin de 3)")
                        logger.info(f"🔍 SYSTÈME DE VÉRIFICATION: Prédiction {predicted_game} continue vers jeu suivant")
                else:
                    # Pas de symbole de succès ou pas édité - pas de vérification
                    logger.info(f"🔍 ⏸️ Pas de vérification - Symbole succès: {has_success_symbol}, Édité: {is_edited}")

            # Vérifier si on doit marquer comme échec après 4 jeux
            elif verification_offset >= 4:
                # Après 4 jeux (0,1,2,3) sans succès, marquer comme échec
                original_message = f"🔵{predicted_game} 🔵3K: statut :⏳"
                updated_message = f"🔵{predicted_game} 🔵3K: statut :⭕⭕"

                prediction['status'] = 'failed'
                prediction['final_message'] = updated_message

                logger.info(f"🔍 ❌ Prédiction {predicted_game} ÉCHOUÉE - Aucun succès trouvé après 4 jeux (décalages 0-3)")
                logger.info(f"🔍 🛑 ARRÊT de vérification - Échec confirmé pour prédiction {predicted_game}")
                return {
                    'type': 'update_message',
                    'predicted_game': predicted_game,
                    'new_message': updated_message,
                    'original_message': original_message
                }

        logger.info(f"🔍 Aucune prédiction à vérifier pour le jeu {game_number}")
        return None

# Global instance
card_predictor = CardPredictor()