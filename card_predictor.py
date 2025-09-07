"""
Card prediction logic for Joker's Telegram Bot - webhook-safe version
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
CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️", "❤️"]
PREDICTION_MESSAGE = "🔵{numero} 🔵3K: statut :⏳"

TARGET_CHANNEL_ID = -1002682552255
PREDICTION_CHANNEL_IDS = [-1002646551216, -100254391536]


class CardPredictor:
    def __init__(self):
        self.predictions = {}
        self.processed_messages = set()
        self.sent_predictions = {}
        self.temporary_messages = {}
        self.pending_edits = {}

    def reset_predictions(self):
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        logger.info("Prediction system reset")

    # ---------- helpers ----------
    def extract_game_number(self, message: str) -> Optional[int]:
        m = re.search(r'#[nN](\d+)', message)
        return int(m.group(1)) if m else None

    def has_pending_indicators(self, text: str) -> bool:
        return any(ch in text for ch in ('⏰', '▶', '🕐', '➡️'))

    def has_completion_indicators(self, text: str) -> bool:
        return any(ch in text for ch in ('✅', '🔰'))

    def extract_card_symbols_from_parentheses(self, text: str) -> List[List[str]]:
        matches = re.findall(r' $([^)]+)$', text)
        out = []
        for m in matches:
            m = m.replace("❤️", "♥️")
            unique = {s for s in ("♠️", "♥️", "♦️", "♣️") if s in m}
            out.append(list(unique))
        return out

    # ---------- prediction rule ----------
    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None

        logger.debug("Analysis for game %s", game_number)

        next_game = game_number + 1
        if next_game in self.predictions and self.predictions[next_game].get('status') == 'pending':
            logger.info("Prediction for N%s already pending", next_game)
            return False, None, None

        sections = self.extract_card_symbols_from_parentheses(message)
        if not sections:
            logger.info("No parentheses found")
            return False, None, None

        first, second = sections[0], sections[1] if len(sections) > 1 else []
        if len(first) == 3 and len(second) != 3:
            combo = ''.join(sorted(first))
            msg_hash = hash(message)
            if msg_hash not in self.processed_messages:
                self.processed_messages.add(msg_hash)
                logger.info("Rule matched: first=3, second!=3 → predict")
                return True, game_number, combo
            else:
                logger.info("Already processed")
                return False, None, None
        else:
            logger.info("Rule NOT matched: first=%s, second=%s", len(first), len(second))
            return False, None, None

    # ---------- prediction ----------
    def make_prediction(self, game_number: int, combination: str) -> str:
        next_game = game_number + 1
        text = PREDICTION_MESSAGE.format(numero=next_game)
        self.predictions[next_game] = {
            'combination': combination,
            'status': 'pending',
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': text
        }
        logger.info("Prediction created for game %s", next_game)
        return text

    # ---------- verification ----------
    def count_cards_in_first_parentheses(self, message: str) -> int:
        m = re.search(r' $([^)]+)$', message)
        if not m:
            return 0
        content = m.group(1).replace("❤️", "♥️")
        return sum(content.count(s) for s in ("♠️", "♥️", "♦️", "♣️"))

    def _verify_prediction_common(self, message: str, is_edited: bool = False) -> Optional[Dict]:
        game_number = self.extract_game_number(message)
        if not game_number:
            return None

        logger.info("Verification for game %s (edited=%s)", game_number, is_edited)

        for predicted_game in sorted(self.predictions):
            pred = self.predictions[predicted_game]
            if pred.get('status') != 'pending':
                continue
            offset = game_number - predicted_game
            if 0 <= offset <= 3 and is_edited and self.has_completion_indicators(message):
                if self.count_cards_in_first_parentheses(message) >= 3:
                    status = ('✅0️⃣', '✅1️⃣', '✅2️⃣', '✅3️⃣')[offset]
                    original = f"🔵{predicted_game} 🔵3K: statut :⏳"
                    updated = f"🔵{predicted_game} 🔵3K: statut :{status}"
                    pred['status'] = 'correct'
                    pred['final_message'] = updated
                    logger.info("Prediction %s verified (offset %s)", predicted_game, offset)
                    return {
                        'type': 'update_message',
                        'predicted_game': predicted_game,
                        'new_message': updated,
                        'original_message': original
                    }
            elif offset >= 4:
                original = f"🔵{predicted_game} 🔵3K: statut :⏳"
                updated = f"🔵{predicted_game} 🔵3K: statut :⭕⭕"
                pred['status'] = 'failed'
                pred['final_message'] = updated
                logger.info("Prediction %s failed after 4 games", predicted_game)
                return {
                    'type': 'update_message',
                    'predicted_game': predicted_game,
                    'new_message': updated,
                    'original_message': original
                }
        return None

    def verify_prediction(self, message: str) -> Optional[Dict]:
        return self._verify_prediction_common(message, is_edited=False)

    def verify_prediction_from_edit(self, message: str) -> Optional[Dict]:
        return self._verify_prediction_common(message, is_edited=True)


# ---------- global instance ----------
card_predictor = CardPredictor()
        
