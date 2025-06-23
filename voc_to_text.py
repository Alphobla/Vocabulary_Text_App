import csv
import random
import datetime
import json
import os
import glob
import re
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()


# --- Find the newest Favorites_YYYYMMDD.csv file ---
def get_latest_favorites_csv(folder):
    pattern = os.path.join(folder, 'Favorites_*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError('No Favorites_*.csv file found in the folder.')
    
    # Sort by date in filename (YYYYMMDD)
    def extract_date(f):
        import re
        m = re.search(r'Favorites_(\d{8})', os.path.basename(f))
        return m.group(1) if m else ''
    files = [f for f in files if extract_date(f)]
    if not files:
        raise FileNotFoundError('No Favorites_*.csv file with date in filename found.')
    files.sort(key=lambda f: extract_date(f), reverse=True)
    latest_file = files[0]
    print(f"✅ Found latest favorites file: {os.path.basename(latest_file)}")
    return latest_file


# --- Main logic ---
# Automatically detect Downloads folder for any user/computer
def get_downloads_folder():
    """Get the Downloads folder path for the current user"""
    import os
    from pathlib import Path
    
    # Try different methods to find Downloads folder
    downloads_paths = [
        # Windows - standard user Downloads folder
        os.path.join(os.path.expanduser("~"), "Downloads"),
        # Alternative Windows path
        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        # OneDrive Downloads (if synced)
        os.path.join(os.path.expanduser("~"), "OneDrive", "Downloads"),
    ]
    
    for path in downloads_paths:
        if os.path.exists(path):
            print(f"📁 Using Downloads folder: {path}")
            return path
    
    # Fallback to current directory if Downloads not found
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"⚠️ Downloads folder not found, using current directory: {current_dir}")
    return current_dir

csv_folder = get_downloads_folder()
csv_path = get_latest_favorites_csv(csv_folder)

# Read vocabulary from CSV
vocab = []
with open(csv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Handle both Reverso export format and custom format
        source_text = row.get("source") or row.get("Search text", "")
        target_text = row.get("target") or row.get("Translation text", "")
        
        if source_text and target_text:
            vocab.append((source_text.strip(), target_text.strip()))

print(f"Loaded {len(vocab)} vocabulary pairs from {os.path.basename(csv_path)}")

# --- Word tracking system ---
class WordTracker:
    def __init__(self, tracking_file_path):
        self.tracking_file = tracking_file_path
        self.word_stats = self.load_tracking_data()
    
    def load_tracking_data(self):
        """Load word usage statistics from JSON file"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("Creating new tracking file...")
        return {}
    
    def save_tracking_data(self):
        """Save word usage statistics to JSON file"""
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(self.word_stats, f, ensure_ascii=False, indent=2)
    
    def calculate_word_priority(self, word, translation):
        """Calculate priority score for a word (higher = more likely to be selected)"""
        word_key = f"{word}|{translation}"
        
        if word_key not in self.word_stats:
            # New word - high priority
            return 100
        
        stats = self.word_stats[word_key]
        # Use last occurrence date for priority
        if stats['occurrences']:
            last_used_date = stats['occurrences'][-1]['date']
            days_since_last_use = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_used_date)).days
        else:
            days_since_last_use = 999
        times_used = len(stats['occurrences'])
        times_not_understood = sum(1 for occ in stats['occurrences'] if occ['repeat'])
        
        # Priority formula: 
        base_priority = min(days_since_last_use * 5, 50)  # Max 50 points for age
        misunderstanding_bonus = times_not_understood * 20  # 20 points per misunderstanding
        frequency_penalty = min(times_used * 2, 30)  # Max 30 point penalty
        
        priority = base_priority + misunderstanding_bonus - frequency_penalty
        return max(priority, 1)  # Minimum priority of 1
    
    def mark_word_used(self, word, translation):
        """Mark a word as used in current session (not repeated)"""
        word_key = f"{word}|{translation}"
        now = datetime.datetime.now().isoformat()
        occurrence = {"date": now, "repeat": False}
        if word_key not in self.word_stats:
            self.word_stats[word_key] = {
                'word': word,
                'translation': translation,
                'occurrences': [occurrence]
            }
        else:
            self.word_stats[word_key]['occurrences'].append(occurrence)
    
    def mark_word_not_understood(self, word, translation):
        """Mark a word as not understood (to be repeated)"""
        word_key = f"{word}|{translation}"
        now = datetime.datetime.now().isoformat()
        occurrence = {"date": now, "repeat": True}
        if word_key not in self.word_stats:
            self.word_stats[word_key] = {
                'word': word,
                'translation': translation,
                'occurrences': [occurrence]
            }
        else:
            self.word_stats[word_key]['occurrences'].append(occurrence)
    
    def select_words_by_priority(self, vocab_list, count=20):
        """Select words based on priority (spaced repetition with randomness) and print urgency bars to terminal"""
        # Randomly sample 40 words from vocab_list (or all if less)
        sample_size = min(40, len(vocab_list))
        sampled_vocab = random.sample(vocab_list, sample_size)
        # Calculate priorities for sampled words
        word_priorities = []
        for word, translation in sampled_vocab:
            priority = self.calculate_word_priority(word, translation)
            word_priorities.append((word, translation, priority))
        # Sort by priority (highest first)
        word_priorities.sort(key=lambda x: x[2], reverse=True)
        # Print urgency bars to terminal (no words, just bars)
        max_urgency = max([p for _, _, p in word_priorities]) if word_priorities else 1
        print("\n[ Vocabulary selection: Urgency bars (top 20 marked) ]")
        for i, (_, _, p) in enumerate(word_priorities):
            bar_len = int((p / max_urgency) * 40)
            bar = '█' * bar_len
            mark = '*' if i < count else ' '
            print(f"{bar:<40} {mark}")
        # Select top N
        selected = [(w, t) for w, t, _ in word_priorities[:count]]
        return selected

# Initialize word tracker
tracking_file = os.path.join(os.getcwd(), "word_tracking.json")
word_tracker = WordTracker(tracking_file)

# Select words using priority system (spaced repetition)
selected = word_tracker.select_words_by_priority(vocab, 20)
french_words = [pair[0] for pair in selected]

# Remove printout of selected words and priorities
# print(f"Selected {len(selected)} words based on learning priorities:")
# for i, (word, translation) in enumerate(selected[:5], 1):
#     priority = word_tracker.calculate_word_priority(word, translation)
#     print(f"  {i}. {word} ({translation}) - Priority: {priority}")
# if len(selected) > 5:
#     print(f"  ... and {len(selected) - 5} more words")

# Generate text and audio, then launch desktop app
def generate_and_launch_app(selected_vocab, word_tracker):
    """Generate text and audio, then launch the desktop application"""
  
    
    print(f"\n📝 Generating French text with {len(selected_vocab)} vocabulary words...")
    
    # Get OpenAI API key from environment
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("❌ Error: openai_key not found in .env file")
        print("Please add your OpenAI API key to the .env file")
        return
    
    try:
        # Generate text using OpenAI
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        vocab_list_str = ", ".join([f"{word} ({translation})" for word, translation in selected_vocab])
        
        prompt = f"""Write an engaging short story in French (about 300 words, also more if needed) that naturally incorporates these vocabulary words:

{vocab_list_str}

Requirements:
- Use ALL the vocabulary words naturally in context
- Make the story interesting and coherent  
- Use conversational, modern French
- The story should help reinforce the meaning of each word through context
- Include some dialogue if possible

Please write only the French story, no other text."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content
        if not generated_text:
            raise ValueError("Failed to generate text from OpenAI API")
        
        print("\n📖 Generated French text successfully!")
        
        # Generate TTS audio
        print("🎵 Generating audio...")
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=generated_text,
            response_format="mp3"
        )
        
        # Save audio file
        audio_path = os.path.join(csv_folder, "generated_text.mp3")
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_response.content)
        
        print("🎵 Audio generated successfully!")
        
        # Save text file for reference
        text_path = os.path.join(csv_folder, "generated_text.txt")
        with open(text_path, "w", encoding="utf-8") as text_file:
            text_file.write(generated_text)
        
        print("\n🚀 Launching desktop app...")
        
        # Import and run the vocabulary reviewer with text and audio
        from vocabulary_reviewer import run_vocabulary_review
        review_completed = run_vocabulary_review(
            selected_vocab, 
            word_tracker, 
            generated_text, 
            audio_path
        )
        
        if review_completed:
            print("✅ Vocabulary review completed and saved!")
        else:
            print("ℹ️ Session ended")
            
    except ImportError as e:
        print(f"❌ Error: Missing package - {e}")
        print("Please install required packages:")
        print("  pip install openai pygame")
    except Exception as e:
        print(f"❌ Error: {e}")

# Mark selected words as used in this session
for word, translation in selected:
    word_tracker.mark_word_used(word, translation)

# Launch the desktop application
generate_and_launch_app(selected, word_tracker)

# Add this import at the top
import csv
import random
import datetime
import json
import os
import glob
from dotenv import load_dotenv

# Add this function to replace the HTML generation
def generate_and_review_text(selected_vocab, word_tracker):
    """Generate text and run vocabulary review"""
    print("\n🎯 Selected vocabulary for this session:")
    for i, (word, translation) in enumerate(selected_vocab, 1):
        print(f"{i:2}. {word} → {translation}")
    
    print(f"\n📝 Generating text with {len(selected_vocab)} vocabulary words...")
    
    # Get OpenAI API key from environment
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        return
    
    # Generate text using OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        vocab_list_str = ", ".join([f"{word} ({translation})" for word, translation in selected_vocab])
        
        prompt = f"""Write an engaging short story in French (about 200-300 words) that naturally incorporates these vocabulary words and their meanings:

{vocab_list_str}

Requirements:
- Use ALL the vocabulary words naturally in context
- Verbs can appear in any form
- Nouns can be used in any form
- Adjectives can be used in any form
- Make the story interesting and coherent
- Use conversational, modern French
- The story should help reinforce the meaning of each word through context
- Include some dialogue if possible

Please write only the French story, no other text."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content.strip();
        print(f"\n📖 Generated French Text:")
        print("=" * 50)
        print(generated_text)
        print("=" * 50)
        
        # Show vocabulary reference
        print(f"\n📚 Vocabulary Reference:")
        for word, translation in selected_vocab:
            print(f"• {word} → {translation}")
        
        # Ask if user wants to review vocabulary
        print(f"\n🎯 Ready to review vocabulary?")
        input("Press Enter to start vocabulary review...")
        
        # Import and run the vocabulary reviewer
        from vocabulary_reviewer import run_vocabulary_review
        review_completed = run_vocabulary_review(selected_vocab, word_tracker)
        
        if review_completed:
            print("✅ Vocabulary review completed and saved!")
        else:
            print("⏹️ Review was cancelled")
            
    except ImportError:
        print("❌ Error: openai package not installed. Install with: pip install openai")
    except Exception as e:
        print(f"❌ Error generating text: {e}")

# Replace the main execution section at the bottom of the file
if __name__ == "__main__":
    try:
        # Initialize word tracker
        downloads_folder = get_downloads_folder()
        tracking_file = os.path.join(downloads_folder, "word_tracking.json")
        word_tracker = WordTracker(tracking_file)
        
        print(f"📊 Word tracking file: {tracking_file}")
        print(f"📈 Currently tracking {len(word_tracker.word_stats)} words")
        
        # Select words using priority system
        selected_vocab = word_tracker.select_words_by_priority(vocab, 20)
        
        # Generate text and run review
        generate_and_review_text(selected_vocab, word_tracker)
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n📋 To use this app:")
        print("1. Export your Reverso favorites as CSV")
        print("2. Save it as 'Favorites_YYYYMMDD.csv' in your Downloads folder")
        print("3. Run this script again")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")