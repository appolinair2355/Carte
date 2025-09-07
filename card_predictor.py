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

# Target channel IDs for predictions and updates (supports multiple channels)
PREDICTION_CHANNEL_IDS = [-1002646551216, -100254391536]


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
            self.pending_edits[message_id] = {
                'original_text': text,
                'timestamp': datetime.now()
            }
            return True
        return False

    def extract_card_symbols_from_parentheses(self, text: str) -> List[List[str]]:
        """Extract unique card symbols from each parentheses section"""
        pattern = r' $([^)]+)$'
        matches = re.findall(pattern, text)

        all_sections = []
        for match in matches:
            normalized_content = match.replace("❤️", "♥️")
            unique_symbols = set()
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                if symbol in normalized_content:
                    unique_symbols.add(symbol)
            all_sections.append(list(unique_symbols))

        return all_sections

    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        NOUVELLE RÈGLE :
        - Prédire uniquement si le premier parenthèse contient exactement 3 cartes différentes
        - ET que le deuxième parenthèse (s’il existe) n’en contient pas 3
        """
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None

        logger.debug(f🔍 Analyse pour le jeu {game_number}")

        next_game = game_number + 1
        if next_game in self.predictions and self.predictions[next_game].get('status') == 'pending':
            logger.info(f"🔍 Prédiction pour N{next_game} déjà en cours, annulation")
            return False, None, None

        sections = self.extract_card_symbols_from_parentheses(message)
        if not sections:
            logger.info(f"🔍 Aucune section entre parenthèses trouvée")
            return False, None, None

        first = sections[0]
        second = sections[1] if len(sections) > 1 else []

        if len(first) == 3 and len(second) != 3:
            combination = ''.join(sorted(first))
            logger.info(f"✅ Règle respectée : 1er parenthèse = 3 cartes différentes, 2e ≠ 3 → Prédiction autorisée")
            message_hash = hash(message)
            if message_hash not in self.processed_messages:
                self.processed_messages.add(message_hash)
                return True, game_number, combination
            else:
                logger.info("⚠️ Message déjà traité")
                return False, None, None
        else:
            logger.info(f"❌ Règle non respectée : 1er={len(first)} cartes, 2e={len(second)} cartes → Pas de prédiction")
            return False, None, None

    def make_prediction(self, game_number: int, combination: str) -> str:
        """Make a prediction for the next game"""
        next_game = game_number + 1
        prediction_text = PREDICTION_MESSAGE.format(numero=next_game)

        self.predictions[next_game] = {
            'combination': combination,
            'status': 'pending',
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': prediction_text
        }

        logger.info(f"🔮 Prédiction lancée pour le jeu {next_game} basée sur combinaison {combination}")
        return prediction_text

    def count_cards_in_first_parentheses(self, message: str) -> int:
        """Count the total number of card symbols in the first parentheses"""
        pattern = r' $([^)]+)$'
        match = re.search(pattern, message)
        if match:
            content = match.group(1).replace("❤️", "♥️")
            return sum(content.count(s) for s in ["♠️", "♥️", "♦️", "♣️"])
        return 0

    def verify_prediction(self, message: str) -> Optional[Dict]:
        return self._verify_prediction_common(message, is_edited=False)

    def verify_prediction_from_edit(self, message: str) -> Optional[Dict]:
        return self._verify_prediction_common(message, is_edited=True)

    def _verify_prediction_common(self, message: str, is_edited: bool = False) -> Optional[Dict]:
        """Vérifie si une prédiction est correcte (uniquement sur messages édités avec ✅ ou 🔰)"""
        game_number = self.extract_game_number(message)
        if not game_number:
            return None

        logger.info(f"🔍 Vérification pour jeu {game_number} (édité: {is_edited})")

        all_predictions = set(self.predictions.keys()) | set(self.sent_predictions.keys())
        predictions_to_check = sorted(all_predictions)

        for predicted_game in predictions_to_check:
            prediction = self.predictions.get(predicted_game, {})
            if prediction.get('status') != 'pending':
                continue

            offset = game_number - predicted_game
            if 0 <= offset <= 3 and is_edited and (self.has_completion_indicators(message)):
                if self.count_cards_in_first_parentheses(message) >= 3:
                    status = ['✅0️⃣', '✅1️⃣', '✅2️⃣', '✅3️⃣'][offset]
                    original = f"🔵{predicted_game} 🔵3K: statut :⏳"
                    updated = f"🔵{predicted_game} 🔵3K: statut :{status}"
                    prediction['status'] = 'correct'
                    prediction['final_message'] = updated
                    logger.info(f"✅ Prédiction {predicted_game} validée avec succès (décalage {offset})")
                    return {
                        'type': 'update_message',
                        'predicted_game': predicted_game,
                        'new_message': updated,
                        'original_message': original
                    }
            elif offset >= 4:
                original = f"🔵{predicted_game} 🔵3K: statut :⏳"
                updated = f"🔵{predicted_game} 🔵3K: statut :⭕⭕"
                prediction['status'] = 'failed'
                prediction['final_message'] = updated
                logger.info(f"❌ Prédiction {predicted_game} échouée après 4 jeux sans succès")
                return {
                    'type': 'update_message',
                    'predicted_game': predicted_game,
                    'new_message': updated,
                    'original_message': original
                }

        return None


# Global instance
card_predictor = CardPredictor()
