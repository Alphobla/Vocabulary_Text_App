#!/usr/bin/env python3
"""
Vocabulary Learning Application

This application loads vocabulary from CSV/XLSX files, uses spaced repetition
to select words for learning, generates contextual stories with OpenAI,
and provides an interactive review system.
"""

import csv
import random
import datetime
import json
import os
import glob
import re
from typing import List, Tuple, Optional
from dotenv import load_dotenv
import openai
import pandas as pd

# Load environment variables from .env file
load_dotenv()


class FileManager:
    """Handles file operations and path management."""
    
    @staticmethod
    def get_downloads_folder() -> str:
        """Get the Downloads folder path for the current user."""
        downloads_paths = [
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
            os.path.join(os.path.expanduser("~"), "OneDrive", "Downloads"),
        ]
        
        for path in downloads_paths:
            if os.path.exists(path):
                print(f"📁 Using Downloads folder: {path}")
                return path
        
        # Fallback to current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"⚠️ Downloads folder not found, using current directory: {current_dir}")
        return current_dir
    
    @staticmethod
    def get_latest_favorites_file(folder: str) -> str:
        """Find the newest Favorites_YYYYMMDD.csv or .xlsx file."""
        pattern_csv = os.path.join(folder, 'Favorites_*.csv')
        pattern_xlsx = os.path.join(folder, 'Favorites_*.xlsx')
        files = glob.glob(pattern_csv) + glob.glob(pattern_xlsx)
        
        if not files:
            raise FileNotFoundError('No Favorites_*.csv or Favorites_*.xlsx file found.')
        
        def extract_date(f):
            m = re.search(r'Favorites_(\d{8})', os.path.basename(f))
            return m.group(1) if m else ''
        
        files = [f for f in files if extract_date(f)]
        if not files:
            raise FileNotFoundError('No Favorites file with date in filename found.')
        
        files.sort(key=lambda f: extract_date(f), reverse=True)
        latest_file = files[0]
        print(f"✅ Found latest favorites file: {os.path.basename(latest_file)}")
        return latest_file


class VocabularyLoader:
    """Handles loading and parsing vocabulary from files."""
    
    @staticmethod
    def load_from_file(file_path: str) -> List[Tuple[str, str, str]]:
        """Read vocabulary from CSV or XLSX file with proper encoding support."""
        vocab = []
        
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.xlsx':
                print("📊 Reading Excel file...")
                df = pd.read_excel(file_path)
            elif file_extension == '.csv':
                print("📄 Reading CSV file...")
                df = VocabularyLoader._read_csv_with_encoding(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            rows = df.to_dict('records')
            
            for row in rows:
                vocab_entry = VocabularyLoader._process_row(row)
                if vocab_entry:
                    vocab.append(vocab_entry)
            
            VocabularyLoader._print_stats(vocab, file_path)
            return vocab
            
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            raise
    
    @staticmethod
    def _read_csv_with_encoding(file_path: str) -> pd.DataFrame:
        """Try multiple encodings to read CSV file."""
        encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1256', 'iso-8859-6']
        
        for encoding in encodings_to_try:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"✅ Successfully read with {encoding} encoding")
                return df
            except UnicodeDecodeError:
                print(f"⚠️ Failed with {encoding} encoding, trying next...")
                continue
        
        raise ValueError("Could not read file with any supported encoding")
    
    @staticmethod
    def _process_row(row: dict) -> Optional[Tuple[str, str, str]]:
        """Process a single row of vocabulary data."""
        columns = list(row.keys())
        
        # Handle NaN values from pandas
        for key in row:
            if pd.isna(row[key]):
                row[key] = ""
        
        # Extract source text
        source_text = (
            row.get("source") or row.get("Source") or
            row.get("Search text") or row.get("English") or 
            row.get("French") or row.get("German") or
            row.get("Text") or
            row.get(columns[0]) if columns else ""
        )
        
        # Extract target text
        target_text = (
            row.get("target") or row.get("Target") or
            row.get("Translation text") or row.get("Arabic") or 
            row.get("AR") or row.get("AREN") or
            row.get("Translation") or
            row.get(columns[1]) if len(columns) > 1 else ""
        )
        
        # Extract pronunciation
        pronunciation = (
            row.get("pronunciation") or row.get("Pronunciation") or
            row.get("phonetic") or row.get("Phonetic") or
            row.get("AREN") or row.get("Romanization") or
            row.get(columns[2]) if len(columns) > 2 else ""
        )
        
        # Clean up text
        source_text = str(source_text).strip() if source_text else ""
        target_text = str(target_text).strip() if target_text else ""
        pronunciation = str(pronunciation).strip() if pronunciation else ""
        
        # Only add if both source and target are present
        if source_text and target_text:
            return (source_text, target_text, pronunciation)
        
        return None
    
    @staticmethod
    def _print_stats(vocab: List[Tuple[str, str, str]], file_path: str):
        """Print statistics about loaded vocabulary."""
        print(f"Loaded {len(vocab)} vocabulary pairs from {os.path.basename(file_path)}")
        
        # Check if pronunciations are available
        pronunciations_available = any(len(entry) > 2 and entry[2] for entry in vocab)
        if pronunciations_available:
            print("✨ Pronunciation information detected and loaded!")
        else:
            print("ℹ️ No pronunciation information found in file.")
        
        # Check for Arabic text
        arabic_detected = any(
            any('\u0600' <= char <= '\u06FF' for char in entry[0] + entry[1]) 
            for entry in vocab
        )
        if arabic_detected:
            print("🌍 Arabic text detected - proper encoding applied!")


class WordTracker:
    """Handles word tracking, priority calculation, and spaced repetition."""
    
    def __init__(self, tracking_file_path: str):
        self.tracking_file = tracking_file_path
        self.word_stats = self.load_tracking_data()
    
    def load_tracking_data(self) -> dict:
        """Load word usage statistics from JSON file."""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Validate and fix data structure
                    return self._validate_and_fix_data(data)
            except (json.JSONDecodeError, FileNotFoundError):
                print("Creating new tracking file...")
        return {}
    
    def _validate_and_fix_data(self, data: dict) -> dict:
        """Validate and fix the data structure if needed."""
        fixed_data = {}
        for key, value in data.items():
            if isinstance(value, dict) and 'occurrences' in value and isinstance(value['occurrences'], list):
                # Data structure is correct - keep as is
                fixed_data[key] = value
            else:
                # Only fix actually corrupted data
                print(f"⚠️ Fixing corrupted data for word: {key}")
                parts = key.split('|', 1)
                word = parts[0] if len(parts) > 0 else ""
                translation = parts[1] if len(parts) > 1 else ""
                
                fixed_data[key] = {
                    'word': word,
                    'translation': translation,
                    'occurrences': []
                }
        return fixed_data
    
    def save_tracking_data(self):
        """Save word usage statistics to JSON file."""
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(self.word_stats, f, ensure_ascii=False, indent=2)
    
    def calculate_word_priority(self, word: str, translation: str) -> int:
        """Calculate priority score for a word (higher = more likely to be selected)."""
        word_key = f"{word}|{translation}"
        
        if word_key not in self.word_stats:
            return 100  # New word - high priority
        
        stats = self.word_stats[word_key]
        
        # Ensure occurrences exists and is a list
        if 'occurrences' not in stats or not isinstance(stats['occurrences'], list):
            stats['occurrences'] = []
        
        # Calculate days since last use
        if stats['occurrences']:
            try:
                last_used_date = stats['occurrences'][-1]['date']
                days_since_last_use = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_used_date)).days
            except (KeyError, ValueError, TypeError):
                days_since_last_use = 999
        else:
            days_since_last_use = 999
        
        times_used = len(stats['occurrences'])
        times_not_understood = sum(1 for occ in stats['occurrences'] 
                                  if isinstance(occ, dict) and occ.get('repeat', False))
        
        # Priority formula
        base_priority = min(days_since_last_use * 5, 50)  # Max 50 points for age
        misunderstanding_bonus = times_not_understood * 20  # 20 points per misunderstanding
        frequency_penalty = min(times_used * 2, 30)  # Max 30 point penalty
        
        priority = base_priority + misunderstanding_bonus - frequency_penalty
        return max(priority, 1)  # Minimum priority of 1
    
    def mark_word_used(self, word: str, translation: str):
        """Mark a word as used in current session (not repeated)."""
        self._add_occurrence(word, translation, repeat=False)
    
    def mark_word_not_understood(self, word: str, translation: str):
        """Mark a word as not understood (to be repeated)."""
        self._add_occurrence(word, translation, repeat=True)
    
    def _add_occurrence(self, word: str, translation: str, repeat: bool):
        """Add an occurrence record for a word."""
        word_key = f"{word}|{translation}"
        now = datetime.datetime.now().isoformat()
        occurrence = {"date": now, "repeat": repeat}
        
        if word_key not in self.word_stats:
            self.word_stats[word_key] = {
                'word': word,
                'translation': translation,
                'occurrences': [occurrence]
            }
        else:
            # Ensure occurrences exists and is a list
            if 'occurrences' not in self.word_stats[word_key]:
                self.word_stats[word_key]['occurrences'] = []
            elif not isinstance(self.word_stats[word_key]['occurrences'], list):
                self.word_stats[word_key]['occurrences'] = []
            
            self.word_stats[word_key]['occurrences'].append(occurrence)

    def select_words_by_priority(self, vocab_list: List[Tuple[str, str, str]], count: int = 20) -> List[Tuple[str, str, str]]:
        """Select words based on priority (spaced repetition with randomness)."""
        
        if not vocab_list:
            print("⚠️ No vocabulary words available for selection")
            return []
        
        # Sample words for priority calculation
        sample_size = min(40, len(vocab_list))
        sampled_vocab = random.sample(vocab_list, sample_size)
        
        # Calculate priorities
        word_priorities = []
        for vocab_entry in sampled_vocab:
            word, translation = vocab_entry[0], vocab_entry[1]
            pronunciation = vocab_entry[2] if len(vocab_entry) > 2 else ""
            
            priority = self.calculate_word_priority(word, translation)
            word_priorities.append((word, translation, pronunciation, priority))
            
        # Sort by priority and show urgency bars
        word_priorities.sort(key=lambda x: x[3], reverse=True)
        self._print_urgency_bars(word_priorities, count)
        
        # Return selected words
        return [(w, t, pron) for w, t, pron, _ in word_priorities[:count]]
    
    def _print_urgency_bars(self, word_priorities: List[Tuple[str, str, str, int]], count: int):
        """Print urgency visualization bars."""
        if not word_priorities:
            return
            
        max_urgency = max(p for _, _, _, p in word_priorities)
        print("\n[ Vocabulary selection: Urgency bars (top 20 marked) ]")
        
        for i, (_, _, _, priority) in enumerate(word_priorities):
            bar_len = int((priority / max_urgency) * 40)
            bar = '█' * bar_len
            mark = '*' if i < count else ' '
            print(f"{bar:<40} {mark}")


class TextGenerator:
    """Handles text generation using OpenAI API."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    def generate_story(self, vocab_list: List[Tuple[str, str, str]], language: str = "French") -> str:
        """Generate a story incorporating the vocabulary words."""
        client = openai.OpenAI(api_key=self.api_key)
        
        vocab_strings = []
        for vocab_entry in vocab_list:
            word, translation = vocab_entry[0], vocab_entry[1]
            vocab_strings.append(f"{word} ({translation})")
        
        vocab_list_str = ", ".join(vocab_strings)
        
        prompt = f"""Write an engaging short story in {language} (about 300 words) that naturally incorporates these vocabulary words:

{vocab_list_str}

Requirements:
- Use ALL the vocabulary words naturally in context
- Make the story interesting and coherent  
- Use conversational, modern {language}
- The story should help reinforce the meaning of each word through context
- Include some dialogue if possible

Please write only the story in {language}, no other text."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return content.strip() if content else ""
    
    def generate_audio(self, text: str, output_path: str):
        """Generate TTS audio for the given text."""
        client = openai.OpenAI(api_key=self.api_key)
        
        print("🎵 Generating audio...")
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            response_format="mp3"
        )
        
        with open(output_path, "wb") as audio_file:
            audio_file.write(audio_response.content)
        
        print("🎵 Audio generated successfully!")


class VocabularyApp:
    """Main application class that coordinates all components."""
    
    def __init__(self):
        self.file_manager = FileManager()
        self.vocabulary_loader = VocabularyLoader()
        self.downloads_folder = self.file_manager.get_downloads_folder()
        self.tracking_file = os.path.join(os.getcwd(), "word_tracking.json")
        self.word_tracker = WordTracker(self.tracking_file)
        
        try:
            self.text_generator = TextGenerator()
        except ValueError as e:
            print(f"❌ Error: {e}")
            print("Please add your OpenAI API key to the .env file")
            self.text_generator = None
    
    def load_vocabulary(self) -> List[Tuple[str, str, str]]:
        """Load vocabulary from the latest favorites file."""
        csv_path = self.file_manager.get_latest_favorites_file(self.downloads_folder)
        return self.vocabulary_loader.load_from_file(csv_path)
    
    def run_session(self):
        """Run a complete vocabulary learning session."""
        try:
            # Load vocabulary
            vocab = self.load_vocabulary()
            
            print(f"📊 Word tracking file: {self.tracking_file}")
            print(f"📈 Currently tracking {len(self.word_tracker.word_stats)} words")
            
            # Select words using priority system
            selected_vocab = self.word_tracker.select_words_by_priority(vocab, 20)
            
            if not selected_vocab:
                print("❌ No vocabulary words selected")
                return
            
            # Mark words as used
            for vocab_entry in selected_vocab:
                word, translation = vocab_entry[0], vocab_entry[1]
                self.word_tracker.mark_word_used(word, translation)
            
            # Generate and review
            if self.text_generator:
                self._generate_and_review(selected_vocab)
            else:
                self._review_only(selected_vocab)
                
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print("\n📋 To use this app:")
            print("1. Export your Reverso favorites as CSV")
            print("2. Save it as 'Favorites_YYYYMMDD.csv' in your Downloads folder")
            print("3. Run this script again")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    def _generate_and_review(self, selected_vocab: List[Tuple[str, str, str]]):
        """Generate text with AI and run vocabulary review."""
        if not self.text_generator:
            print("❌ Text generator not available")
            return
            
        print(f"\n📝 Generating text with {len(selected_vocab)} vocabulary words...")
        
        try:
            # Generate story
            generated_text = self.text_generator.generate_story(selected_vocab)
            
            print(f"\n📖 Generated Text:")
            print("=" * 50)
            print(generated_text)
            print("=" * 50)
            
            # Generate audio
            audio_path = os.path.join(self.downloads_folder, "generated_text.mp3")
            self.text_generator.generate_audio(generated_text, audio_path)
            
            # Save text file
            text_path = os.path.join(self.downloads_folder, "generated_text.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(generated_text)
            
            print("\n🚀 Launching vocabulary review...")
            self._run_vocabulary_review(selected_vocab, generated_text, audio_path)
            
        except Exception as e:
            print(f"❌ Error generating content: {e}")
            self._review_only(selected_vocab)
    
    def _review_only(self, selected_vocab: List[Tuple[str, str, str]]):
        """Run vocabulary review without AI-generated content."""
        print(f"\n🎯 Selected vocabulary for this session:")
        for i, (word, translation, _) in enumerate(selected_vocab, 1):
            print(f"{i:2}. {word} → {translation}")
        
        print(f"\n📚 Vocabulary Reference:")
        for word, translation, pronunciation in selected_vocab:
            display = f"• {word} → {translation}"
            if pronunciation:
                display += f" [{pronunciation}]"
            print(display)
        
        input("\nPress Enter to start vocabulary review...")
        self._run_vocabulary_review(selected_vocab)
    
    def _run_vocabulary_review(self, selected_vocab: List[Tuple[str, str, str]], 
                              generated_text: Optional[str] = None, audio_path: Optional[str] = None):
        """Launch the vocabulary review interface."""
        try:
            from vocabulary_reviewer import run_vocabulary_review
            
            if generated_text and audio_path:
                review_completed = run_vocabulary_review(
                    selected_vocab, self.word_tracker, generated_text, audio_path
                )
            else:
                review_completed = run_vocabulary_review(selected_vocab, self.word_tracker)
            
            if review_completed:
                print("✅ Vocabulary review completed and saved!")
            else:
                print("⏹️ Review was cancelled")
                
        except ImportError:
            print("❌ Error: vocabulary_reviewer module not found")
        except Exception as e:
            print(f"❌ Error running review: {e}")


def main():
    """Main entry point of the application."""
    app = VocabularyApp()
    app.run_session()


if __name__ == "__main__":
    main()
