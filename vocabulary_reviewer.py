import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import datetime
import webbrowser
import threading
import pygame

class VocabularyReviewer:
    def __init__(self, vocab_list, word_tracker, generated_text=None, audio_path=None):
        self.vocab_list = vocab_list
        self.word_tracker = word_tracker
        self.generated_text = generated_text
        self.audio_path = audio_path
        self.current_index = 0
        self.difficult_words = []
        self.review_complete = False
        self.showing_text = True  # Start by showing the text
        
        # Initialize pygame mixer for audio
        try:
            pygame.mixer.init()
            self.audio_available = True
        except:
            self.audio_available = False
            print("⚠️ Audio not available - pygame not installed")
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("French Vocabulary Learning App")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        if self.generated_text:
            self.setup_text_view()
        else:
            self.setup_vocab_review()
        
    def setup_text_view(self):
        """Setup the initial text reading view"""
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="📖 French Reading Practice", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Audio controls (if available)
        if self.audio_available and self.audio_path and os.path.exists(self.audio_path):
            audio_frame = ttk.Frame(main_frame)
            audio_frame.grid(row=1, column=0, columnspan=2, pady=(0, 20))
            
            self.play_btn = ttk.Button(
                audio_frame, 
                text="▶️ Play Audio", 
                command=self.play_audio
            )
            self.play_btn.grid(row=0, column=0, padx=5)
            
            self.pause_btn = ttk.Button(
                audio_frame, 
                text="⏸️ Pause", 
                command=self.pause_audio
            )
            self.pause_btn.grid(row=0, column=1, padx=5)
            
            self.stop_btn = ttk.Button(
                audio_frame, 
                text="⏹️ Stop", 
                command=self.stop_audio
            )
            self.stop_btn.grid(row=0, column=2, padx=5)
        
        # Text display with scroll
        text_frame = ttk.LabelFrame(main_frame, text="French Text", padding="15")
        text_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=70,
            height=15,
            font=('Arial', 12),
            bg='#fafafa',
            relief='flat',
            borderwidth=0
        )
        self.text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Insert and format the text
        self.text_widget.insert('1.0', self.generated_text)
        self.text_widget.config(state='disabled')
        
        # Vocabulary reference
        vocab_frame = ttk.LabelFrame(main_frame, text="Vocabulary Reference", padding="15")
        vocab_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        vocab_text = scrolledtext.ScrolledText(
            vocab_frame,
            wrap=tk.WORD,
            width=70,
            height=8,
            font=('Arial', 10),
            bg='#f9f9f9'
        )
        vocab_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Add vocabulary list
        vocab_content = "Vocabulary used in this text:\n\n"
        for i, (french, german) in enumerate(self.vocab_list, 1):
            vocab_content += f"{i:2}. {french} → {german}\n"
        
        vocab_text.insert('1.0', vocab_content)
        vocab_text.config(state='disabled')
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame, 
            text="📚 Start Vocabulary Review", 
            command=self.start_vocab_review,
            style='Accent.TButton'
        ).grid(row=0, column=0, padx=10)
        
        ttk.Button(
            button_frame, 
            text="✅ I'm Done", 
            command=self.finish_session
        ).grid(row=0, column=1, padx=10)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        vocab_frame.columnconfigure(0, weight=1)
        
        # Configure button style
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 11, 'bold'))
    
    def play_audio(self):
        """Play the audio file"""
        if self.audio_available and self.audio_path and os.path.exists(self.audio_path):
            try:
                pygame.mixer.music.load(self.audio_path)
                pygame.mixer.music.play()
                self.play_btn.config(text="🔄 Playing...")
            except Exception as e:
                messagebox.showerror("Audio Error", f"Could not play audio: {e}")
    
    def pause_audio(self):
        """Pause the audio"""
        if self.audio_available:
            try:
                pygame.mixer.music.pause()
                self.play_btn.config(text="▶️ Resume")
            except:
                pass
    
    def stop_audio(self):
        """Stop the audio"""
        if self.audio_available:
            try:
                pygame.mixer.music.stop()
                self.play_btn.config(text="▶️ Play Audio")
            except:
                pass
    
    def start_vocab_review(self):
        """Transition to vocabulary review"""
        self.showing_text = False
        self.setup_vocab_review()
    
    def setup_vocab_review(self):
        """Setup the vocabulary review interface"""
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="📚 Vocabulary Review", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=len(self.vocab_list),
            length=500
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Progress label
        self.progress_label = ttk.Label(main_frame, text="", font=('Arial', 10))
        self.progress_label.grid(row=2, column=0, columnspan=3, pady=(0, 20))
        
        # Word display frame
        word_frame = ttk.LabelFrame(main_frame, text="Vocabulary", padding="30")
        word_frame.grid(row=3, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        
        # French word
        ttk.Label(word_frame, text="French:", font=('Arial', 14, 'bold')).grid(row=0, column=0, sticky=tk.W)
        self.french_label = ttk.Label(word_frame, text="", font=('Arial', 18), foreground='#0066cc')
        self.french_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # German translation
        ttk.Label(word_frame, text="German:", font=('Arial', 14, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(15, 0))
        self.german_label = ttk.Label(word_frame, text="", font=('Arial', 18), foreground='#cc6600')
        self.german_label.grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(15, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=30)
        
        # Difficulty buttons
        self.easy_btn = ttk.Button(
            button_frame, 
            text="✅ Easy - I know this well", 
            command=self.mark_easy,
            style='Easy.TButton'
        )
        self.easy_btn.grid(row=0, column=0, padx=15, ipadx=20, ipady=10)
        
        self.difficult_btn = ttk.Button(
            button_frame, 
            text="❌ Difficult - Need more practice", 
            command=self.mark_difficult,
            style='Difficult.TButton'
        )
        self.difficult_btn.grid(row=0, column=1, padx=15, ipadx=20, ipady=10)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.prev_btn = ttk.Button(nav_frame, text="← Previous", command=self.previous_word)
        self.prev_btn.grid(row=0, column=0, padx=10)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self.next_word)
        self.next_btn.grid(row=0, column=1, padx=10)
        
        # Summary frame (initially hidden)
        self.summary_frame = ttk.LabelFrame(main_frame, text="Review Summary", padding="20")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Configure button styles
        style = ttk.Style()
        style.configure('Easy.TButton', font=('Arial', 12, 'bold'))
        style.configure('Difficult.TButton', font=('Arial', 12, 'bold'))
        
        # Start showing vocabulary
        self.show_current_word()
    
    def show_current_word(self):
        if self.current_index < len(self.vocab_list):
            french, german = self.vocab_list[self.current_index]
            self.french_label.config(text=french)
            self.german_label.config(text=german)
            
            # Update progress
            self.progress_var.set(self.current_index)
            self.progress_label.config(
                text=f"Word {self.current_index + 1} of {len(self.vocab_list)}"
            )
            
            # Update button states
            self.prev_btn.config(state='normal' if self.current_index > 0 else 'disabled')
            
            # Mark word as used
            self.word_tracker.mark_word_used(french, german)
        else:
            self.show_summary()
    
    def mark_easy(self):
        self.next_word()
    
    def mark_difficult(self):
        if self.current_index < len(self.vocab_list):
            french, german = self.vocab_list[self.current_index]
            self.difficult_words.append(f"{french} - {german}")
            # Mark word as not understood in tracker
            self.word_tracker.mark_word_not_understood(french, german)
        self.next_word()
    
    def next_word(self):
        if self.current_index < len(self.vocab_list) - 1:
            self.current_index += 1
            self.show_current_word()
        else:
            self.show_summary()
    
    def previous_word(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_word()
    
    def show_summary(self):
        # Hide word display
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if hasattr(child, 'grid_forget'):
                    child.grid_forget()
        
        # Show summary
        self.summary_frame.grid(row=2, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Summary content
        summary_text = f"""
🎉 Vocabulary Review Complete!

📊 Statistics:
• Total words reviewed: {len(self.vocab_list)}
• Words marked as difficult: {len(self.difficult_words)}
• Words you know well: {len(self.vocab_list) - len(self.difficult_words)}

"""
        
        if self.difficult_words:
            summary_text += "\n❌ Words to review again:\n"
            for word in self.difficult_words:
                summary_text += f"  • {word}\n"
        else:
            summary_text += "\n✅ Great job! You knew all the words!"
        
        summary_label = ttk.Label(self.summary_frame, text=summary_text, font=('Arial', 11))
        summary_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Action buttons
        button_frame = ttk.Frame(self.summary_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame, 
            text="🔄 Generate New Text", 
            command=self.generate_new_text
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame, 
            text="✅ Exit", 
            command=self.save_and_exit
        ).grid(row=0, column=1, padx=5)
        
        # Save tracking data
        self.word_tracker.save_tracking_data()
        self.review_complete = True
    
    def finish_session(self):
        """Finish session without vocabulary review"""
        self.save_and_exit()
    
    def generate_new_text(self):
        self.save_and_exit()
        # The caller can handle restarting if needed
    
    def save_and_exit(self):
        self.word_tracker.save_tracking_data()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()
        return self.review_complete

def run_vocabulary_review(vocab_list, word_tracker, generated_text=None, audio_path=None):
    """Run the vocabulary review application"""
    app = VocabularyReviewer(vocab_list, word_tracker, generated_text, audio_path)
    return app.run()