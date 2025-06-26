import tkinter as tk
from vocabulary_reviewer import VocabularyReviewer

# Mock word tracker class for testing
class MockWordTracker:
    def __init__(self):
        # Mock tracking data for testing urgency chart - create varied urgency levels
        self.word_stats = {
            ("excuse me", "perdón"): {"times_seen": 1, "times_not_understood": 1, "last_used": "2024-06-01"},  # Very urgent
            ("please", "por favor"): {"times_seen": 2, "times_not_understood": 1, "last_used": "2024-06-05"},  # High urgency
            ("goodbye", "adiós"): {"times_seen": 3, "times_not_understood": 2, "last_used": "2024-06-10"},  # High urgency
            ("car", "coche"): {"times_seen": 3, "times_not_understood": 1, "last_used": "2024-06-15"},  # Medium-high
            ("food", "comida"): {"times_seen": 4, "times_not_understood": 0, "last_used": "2024-06-18"},  # Medium
            ("hello", "hola"): {"times_seen": 5, "times_not_understood": 0, "last_used": "2024-06-20"},  # Medium-low
            ("friend", "amigo"): {"times_seen": 6, "times_not_understood": 0, "last_used": "2024-06-22"},  # Low
            ("house", "casa"): {"times_seen": 8, "times_not_understood": 0, "last_used": "2024-06-24"},  # Lower
            ("water", "agua"): {"times_seen": 10, "times_not_understood": 0, "last_used": "2024-06-25"},  # Very low
            ("thank you", "gracias"): {"times_seen": 15, "times_not_understood": 0, "last_used": "2024-06-26"}  # Lowest
        }
    
    def calculate_word_priority(self, word, translation):
        """Mock priority calculation to simulate urgency levels"""
        # Return fixed urgency values to create a clear dropping pattern
        urgency_map = {
            ("excuse me", "perdón"): 95,     # Very urgent
            ("please", "por favor"): 85,    # High urgency  
            ("goodbye", "adiós"): 75,       # High urgency
            ("car", "coche"): 65,           # Medium-high
            ("food", "comida"): 55,         # Medium
            ("hello", "hola"): 45,          # Medium-low
            ("friend", "amigo"): 35,        # Low
            ("house", "casa"): 25,          # Lower
            ("water", "agua"): 15,          # Very low
            ("thank you", "gracias"): 10    # Lowest
        }
        
        key = (word, translation)
        return urgency_map.get(key, 50)  # Default to 50 if not found
    
    def mark_word_used(self, source, target):
        pass
    
    def mark_word_not_understood(self, source, target):
        pass
    
    def save_tracking_data(self):
        pass

# Sample vocabulary data for testing with example sentences
test_vocab = [
    ("hello", "hola", "OH-lah"),
    ("goodbye", "adiós", "ah-THYOHS"),
    ("thank you", "gracias", "GRAH-thyahs"),
    ("please", "por favor", "por fah-BOHR"),
    ("excuse me", "perdón", "per-DOHN"),
    ("water", "agua", "AH-gwah"),
    ("food", "comida", "ko-MEE-dah"),
    ("house", "casa", "KAH-sah"),
    ("car", "coche", "KO-cheh"),
    ("friend", "amigo", "ah-MEE-go")
]

# Example sentences for each word (mock CSV-like data)
example_sentences = {
    ("hello", "hola"): "Hola, ¿cómo estás hoy?",
    ("goodbye", "adiós"): "Adiós, nos vemos mañana.",
    ("thank you", "gracias"): "Gracias por tu ayuda con esto.",
    ("please", "por favor"): "¿Puedes ayudarme, por favor?",
    ("excuse me", "perdón"): "Perdón, ¿dónde está el baño?",
    ("water", "agua"): "Necesito un vaso de agua fría.",
    ("food", "comida"): "La comida en este restaurante es deliciosa.",
    ("house", "casa"): "Mi casa está cerca del parque.",
    ("car", "coche"): "Mi coche es rojo y muy rápido.",
    ("friend", "amigo"): "Mi mejor amigo vive en Madrid."
}

test_text = """This is a sample text for testing the vocabulary reviewer interface. 
It contains some of the vocabulary words like hello, goodbye, and thank you. 
You can use this to test the reading practice view and then move on to the vocabulary selection tiles."""

# Create and run the test
if __name__ == "__main__":
    mock_tracker = MockWordTracker()
    app = VocabularyReviewer(test_vocab, mock_tracker, test_text, None, example_sentences)
    
    # Override the check_feedback method to ensure tiles show up
    original_check_feedback = app.check_feedback
    def debug_check_feedback():
        # Add some words to difficult_words if empty (for testing)
        if not app.difficult_words:
            app.difficult_words = {
                ("excuse me", "perdón"),
                ("please", "por favor"),
                ("goodbye", "adiós")
            }
            print(f"Debug: Added test difficult words: {app.difficult_words}")
        else:
            print(f"Debug: Found difficult words: {app.difficult_words}")
        
        return original_check_feedback()
    
    app.check_feedback = debug_check_feedback
    app.run()