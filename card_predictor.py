"""
Card prediction logic for Joker's Telegram Bot - simplified for webhook deployment
"""

import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Configuration constants
VALID_CARD_COMBINATIONS = [
    "♠️♥️♦️", "♠️♥️♣️", "♠️♦️♣️", "♥️♦️♣️"
]

CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️", "❤️"]  # Include both ♥️ and ❤️ variants

PREDICTION_MESSAGE = "🔵{numero} 🔵3K: statut :⏳"

class CardPredictor:
    """Handles card prediction logic for webhook deployment"""
    
    def __init__(self):
        self.predictions = {}  # Store predictions for verification
        self.processed_messages = set()  # Avoid duplicate processing
        self.sent_predictions = {}  # Store sent prediction messages for editing
        self.temporary_messages = {}  # Store temporary messages waiting for final edit
    
    def extract_game_number(self, message: str) -> Optional[int]:
        """Extract game number from message like #n744 or #N744"""
        pattern = r'#[nN](\d+)'
        match = re.search(pattern, message)
        if match:
            return int(match.group(1))
        return None
    
    def extract_cards_from_parentheses(self, message: str) -> List[str]:
        """Extract cards from first and second parentheses"""
        pattern = r'\(([^)]+)\)'
        matches = re.findall(pattern, message)
        
        card_groups = []
        for match in matches[:2]:  # Only first two parentheses
            cards = self.extract_card_symbols(match)
            if cards:
                card_groups.extend(cards)
        
        return card_groups
    
    def extract_card_symbols(self, text: str) -> List[str]:
        """Extract card symbols from text"""
        cards = []
        # Normalize ❤️ to ♥️ for consistency
        normalized_text = text.replace("❤️", "♥️")
        
        for symbol in ["♠️", "♥️", "♦️", "♣️"]:  # Use normalized symbols
            count = normalized_text.count(symbol)
            cards.extend([symbol] * count)
        return cards
    
    def has_three_different_cards(self, cards: List[str]) -> bool:
        """Check if there are exactly 3 different card symbols"""
        unique_cards = list(set(cards))
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
    
    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Determine if we should make a prediction based on message content
        Returns: (should_predict, game_number, card_combination)
        """
        # Extract game number
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None
        
        # Check if this is a temporary message (should wait for final edit)
        if self.is_temporary_message(message):
            logger.info(f"Game {game_number}: Temporary message detected")
            self.temporary_messages[game_number] = message
            return False, None, None
        
        # Check if this is a final message
        if self.is_final_message(message) and game_number in self.temporary_messages:
            logger.info(f"Game {game_number}: Final message detected")
            del self.temporary_messages[game_number]
        
        # Extract cards from parentheses
        pattern = r'\(([^)]+)\)'
        matches = re.findall(pattern, message)
        
        if len(matches) < 1:
            return False, None, None
        
        # Check first parentheses
        if len(matches) >= 1:
            first_cards = self.extract_card_symbols(matches[0])
            if self.has_three_different_cards(first_cards):
                combination = self.get_card_combination(first_cards)
                if combination:
                    message_hash = hash(message)
                    if message_hash not in self.processed_messages:
                        self.processed_messages.add(message_hash)
                        return True, game_number, combination
        
        # Check second parentheses
        if len(matches) >= 2:
            second_cards = self.extract_card_symbols(matches[1])
            if self.has_three_different_cards(second_cards):
                combination = self.get_card_combination(second_cards)
                if combination:
                    message_hash = hash(message)
                    if message_hash not in self.processed_messages:
                        self.processed_messages.add(message_hash)
                        return True, game_number, combination
        
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
    
    def count_cards_in_first_parentheses(self, message: str) -> int:
        """Count the number of card symbols in first parentheses"""
        pattern = r'\(([^)]+)\)'
        matches = re.findall(pattern, message)
        
        if matches:
            first_content = matches[0]
            # Normalize ❤️ to ♥️ for consistent counting
            normalized_content = first_content.replace("❤️", "♥️")
            card_count = 0
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                card_count += normalized_content.count(symbol)
            return card_count
        
        return 0
    
    def verify_prediction(self, message: str) -> Optional[Dict]:
        """Verify if a prediction was correct"""
        game_number = self.extract_game_number(message)
        if not game_number:
            return None
        
        logger.info(f"Verifying prediction for game {game_number}")
        logger.info(f"Message content: {message}")
        
        # Check all pending predictions
        for predicted_game, prediction in self.predictions.items():
            if prediction['status'] != 'pending':
                continue
                
            verification_offset = game_number - predicted_game
            logger.info(f"Checking prediction {predicted_game} vs game {game_number}, offset: {verification_offset}")
            
            if 0 <= verification_offset <= 3:
                has_success_symbol = '✅' in message or '🔰' in message
                card_count = self.count_cards_in_first_parentheses(message)
                logger.info(f"Has success symbol: {has_success_symbol}, Card count: {card_count}")
                
                if has_success_symbol and card_count >= 3:
                    status_map = {0: '✅0️⃣', 1: '✅1️⃣', 2: '✅2️⃣', 3: '✅3️⃣'}
                    new_status = status_map[verification_offset]
                    
                    updated_message = prediction['message_text'].replace('statut :⏳', f'statut :{new_status}')
                    
                    prediction['status'] = 'correct'
                    prediction['verification_count'] = verification_offset
                    prediction['final_message'] = updated_message
                    
                    logger.info(f"Prediction verified for game {predicted_game} at offset {verification_offset}")
                    return {
                        'type': 'update_message',
                        'predicted_game': predicted_game,
                        'new_message': updated_message,
                        'original_message': prediction['message_text']
                    }
                    
                elif verification_offset == 3:
                    # Failed after maximum attempts
                    updated_message = prediction['message_text'].replace('statut :⏳', 'statut :❌⭕')
                    
                    prediction['status'] = 'failed'
                    prediction['final_message'] = updated_message
                    
                    logger.info(f"Prediction failed for game {predicted_game}")
                    return {
                        'type': 'update_message',
                        'predicted_game': predicted_game,
                        'new_message': updated_message,
                        'original_message': prediction['message_text']
                    }
        
        return None

# Global instance
card_predictor = CardPredictor()