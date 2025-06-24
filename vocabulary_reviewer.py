import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
import vlc
import sys

class VocabularyReviewer:
    def __init__(self, vocab_list, word_tracker, generated_text=None, audio_path=None):
        # Handle both 2-tuple and 3-tuple formats, using generic terms
        self.vocab_list = []
        for vocab_entry in vocab_list:
            if len(vocab_entry) == 2:
                source, target = vocab_entry
                pronunciation = ""
            else:
                source, target, pronunciation = vocab_entry
            self.vocab_list.append((source, target, pronunciation))
        
        # Fix VLC initialization
        try:
            self.vlc_instance = vlc.Instance()
            if self.vlc_instance is None:
                raise Exception("VLC instance could not be created")
            # Test if we can create a media player
            test_player = self.vlc_instance.media_player_new()
            if test_player is None:
                raise Exception("VLC media player could not be created")
        except Exception as e:
            messagebox.showerror("Error", f"VLC media player is not installed or not working properly: {e}\nProgram will exit.")
            sys.exit(1)
            
        self.word_tracker = word_tracker
        self.generated_text = generated_text
        self.audio_path = audio_path
        self.difficult_words = set()
        self.review_complete = False
        self.tiles = []
        self.save_allowed = False
        self.root = tk.Tk()
        self.root.title("Vocabulary Review")
        self.root.geometry("1200x800")
        self.root.configure(bg='#ffffff')
        self.root.minsize(1000, 600)
        
        # Modern styling
        self.setup_modern_styles()

        # Main layout
        # Pack the audio controls at the bottom first, so they are not pushed out
        self.audio_controls_frame = ttk.Frame(self.root)
        self.audio_controls_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Pack the content frame to fill the rest of the space
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.setup_audio_controls() # Call once to set up audio controls
        self.setup_start_view()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_modern_styles(self):
        """Configure modern styling for the application"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern button styles
        style.configure('Modern.TButton', 
                       font=('Segoe UI', 11),
                       padding=(20, 12),
                       relief='flat',
                       borderwidth=0)
        
        style.configure('Accent.TButton', 
                       font=('Segoe UI', 12, 'bold'),
                       padding=(25, 15),
                       relief='flat',
                       borderwidth=0,
                       background='#0078d4',
                       foreground='white')
        
        style.map('Accent.TButton',
                 background=[('active', '#106ebe'),
                           ('pressed', '#005a9e')])
        
        style.configure('Tile.TButton', 
                       font=('Segoe UI', 11),
                       padding=(15, 10),
                       relief='flat',
                       borderwidth=1,
                       background='#f8f9fa',
                       foreground='#212529')
        
        style.map('Tile.TButton',
                 background=[('active', '#e9ecef'),
                           ('pressed', '#dee2e6')])
        
        style.configure('Selected.TButton', 
                       font=('Segoe UI', 11, 'bold'),
                       padding=(15, 10),
                       relief='flat',
                       borderwidth=2,
                       background='#fff3cd',
                       foreground='#856404')
        
        style.map('Selected.TButton',
                 background=[('active', '#ffeaa7'),
                           ('pressed', '#fdcb6e')])
        
        # Configure frame styles
        style.configure('Card.TFrame',
                       background='#ffffff',
                       relief='flat',
                       borderwidth=1)
        
        # Add style for LabelFrame
        style.configure('Card.TLabelFrame',
                        background='#ffffff')
        style.configure('Card.TLabelFrame.Label',
                        font=('Segoe UI', 10, 'bold'),
                        background='#ffffff',
                        foreground='#6c757d')

        # Configure label styles  
        style.configure('Heading.TLabel',
                       font=('Segoe UI', 20, 'bold'),
                       background='#ffffff',
                       foreground='#212529')
        
        style.configure('Subheading.TLabel',
                       font=('Segoe UI', 14),
                       background='#ffffff',
                       foreground='#6c757d')        
        style.configure('Body.TLabel',
                       font=('Segoe UI', 11),
                       background='#ffffff',
                       foreground='#495057')

    def setup_start_view(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Main container with padding
        main_frame = ttk.Frame(self.content_frame, style='Card.TFrame', padding="40")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Header row: Title (left), Action button (right)
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        title = ttk.Label(header_frame, text="Reading Practice", style='Heading.TLabel')
        title.pack(side=tk.LEFT)
        btn = ttk.Button(header_frame, text="Pass on to Vocabulary", command=self.setup_tile_view, style='Accent.TButton')
        btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        if self.generated_text:
            # Text section with modern styling (no 'Text' label)
            text_frame = ttk.Frame(main_frame, style='Card.TFrame')
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            # Scrollable text widget
            text_container = ttk.Frame(text_frame)
            text_container.pack(fill=tk.BOTH, expand=True)
            
            text_widget = tk.Text(text_container, 
                                wrap=tk.WORD, 
                                font=('Segoe UI', 12), 
                                bg='#fafafa', 
                                fg='#212529',
                                relief='flat', 
                                borderwidth=0,
                                selectbackground='#0078d4',
                                selectforeground='white',
                                padx=20, pady=15)
            
            scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget.insert('1.0', self.generated_text)
            text_widget.config(state='disabled')
        
        # Action button
        btn = ttk.Button(main_frame, text="Review Vocabulary", command=self.setup_tile_view, style='Accent.TButton')
        btn.pack(side=tk.BOTTOM, pady=20)
        
    def play_audio(self):
        if hasattr(self, 'vlc_player'):
            self.vlc_player.play()
            self.vlc_player.set_rate(self.audio_speed)
            self.update_audio_progress()

    def pause_audio(self):
        if hasattr(self, 'vlc_player'):
            self.vlc_player.pause()

    def stop_audio(self):
        if hasattr(self, 'vlc_player'):
            self.vlc_player.stop()
            self.audio_progress.set(0)

    def change_speed(self, delta):
        self.audio_speed = max(0.5, min(2.0, self.audio_speed + delta))
        if hasattr(self, 'vlc_player'):
            self.vlc_player.set_rate(self.audio_speed)
        if hasattr(self, 'play_btn'):
            self.play_btn.config(text=f"▶ Play ({int(self.audio_speed*100)}%)")

    def slider_seek_update(self, value):
        # Called while dragging the slider, just set dragging flag
        self._slider_dragging = True

    def slider_seek_commit(self, event=None):
        # Called when user releases the slider, perform seek
        if hasattr(self, 'vlc_player') and self.audio_length > 0:
            try:
                rel = self.audio_progress.get() / 100.0
                rel = min(max(rel, 0), 1)
                new_pos = rel * self.audio_length
                self.vlc_player.set_time(int(new_pos * 1000))
            except Exception:
                pass
        self._slider_dragging = False

    def update_audio_progress(self):
        if hasattr(self, 'vlc_player') and self.vlc_player.is_playing() and not self._slider_dragging:
            try:
                length = self.vlc_player.get_length() / 1000.0
                if length > 0:
                    self.audio_length = length
                pos = self.vlc_player.get_time() / 1000.0
                progress = min(100, (pos / self.audio_length) * 100)
                self.audio_progress.set(progress)
                
                # Update time display
                if hasattr(self, 'time_label'):
                    current_time = self.format_time(pos)
                    total_time = self.format_time(self.audio_length)
                    self.time_label.config(text=f"{current_time} / {total_time}")
            except:
                pass
        self.root.after(200, self.update_audio_progress)

    def format_time(self, seconds):
        """Format seconds into MM:SS format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def jump_audio(self, seconds):
        if hasattr(self, 'vlc_player') and self.audio_length > 0:
            try:
                cur_pos = self.vlc_player.get_time() / 1000.0
                new_pos = min(max(cur_pos + seconds, 0), self.audio_length)
                self.vlc_player.set_time(int(new_pos * 1000))
                self.audio_progress.set((new_pos / self.audio_length) * 100)
            except Exception:
                pass

    def seek_audio(self, event=None):
        if hasattr(self, 'vlc_player') and self.audio_length > 0:
            try:
                # Get the click or drag position
                widget = event.widget if event else self.audio_progress_bar
                x = event.x if event else 0
                width = widget.winfo_width()
                rel = x / width if width > 0 else self.audio_progress.get() / 100.0
                rel = min(max(rel, 0), 1)
                new_pos = rel * self.audio_length
                self.audio_progress.set(rel * 100)
                self.vlc_player.set_time(int(new_pos * 1000))
            except Exception as e:
                pass

    def setup_tile_view(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Main container
        main_frame = ttk.Frame(self.content_frame, style='Card.TFrame', padding="40")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Title section
        title = ttk.Label(main_frame, text="Select words you want to review again", style='Heading.TLabel')
        title.pack(pady=(0, 20))
        
        subtitle = ttk.Label(main_frame, text="Click on vocabulary items that need more practice", style='Subheading.TLabel')
        subtitle.pack(pady=(0, 30))
        
        # Scrollable tiles container
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
        
        canvas = tk.Canvas(canvas_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Tiles grid
        self.tiles = []
        cols = 2  # Two columns for better readability
        
        for i, (source, target, pronunciation) in enumerate(self.vocab_list):
            # Create tile text with pronunciation if available
            if pronunciation:
                tile_text = f"{source} [{pronunciation}] → {target}"
            else:
                tile_text = f"{source} → {target}"
            
            tile = ttk.Button(scrollable_frame, 
                            text=tile_text, 
                            width=50, 
                            style='Tile.TButton')
            
            row = i // cols
            col = i % cols
            tile.grid(row=row, column=col, padx=15, pady=10, sticky="ew")
            
            tile.config(command=lambda t=tile, w=(source, target): self.toggle_tile(t, w))
            self.tiles.append((tile, (source, target)))
        
        # Configure grid weights for responsive design
        for col in range(cols):
            scrollable_frame.columnconfigure(col, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
          # Action button
        btn = ttk.Button(main_frame, text="Continue", command=self.check_feedback, style='Accent.TButton')
        btn.pack(pady=20)

    def toggle_tile(self, tile, word):
        if word in self.difficult_words:
            self.difficult_words.remove(word)
            tile.config(style='Tile.TButton')
        else:
            self.difficult_words.add(word)
            tile.config(style='Selected.TButton')

    def check_feedback(self):
        self.save_allowed = True
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Main container
        main_frame = ttk.Frame(self.content_frame, style='Card.TFrame', padding="40")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Title
        title = ttk.Label(main_frame, text="Review Complete", style='Heading.TLabel')
        title.pack(pady=(0, 30))
        
        # Statistics
        total_words = len(self.vocab_list)
        words_to_repeat = len(self.difficult_words)
        words_known = total_words - words_to_repeat
        
        stats_frame = ttk.Frame(main_frame, style='Card.TFrame')
        stats_frame.pack(pady=(0, 30), fill=tk.X)
        
        # Stats grid
        stats_container = ttk.Frame(stats_frame)
        stats_container.pack(expand=True)
        
        # Known words
        known_frame = ttk.Frame(stats_container, style='Card.TFrame', padding="20")
        known_frame.pack(side=tk.LEFT, padx=(0, 20), fill=tk.BOTH, expand=True)
        
        ttk.Label(known_frame, text=str(words_known), font=('Segoe UI', 24, 'bold'), 
                 foreground='#28a745', background='#ffffff').pack()
        ttk.Label(known_frame, text="Words Known", style='Body.TLabel').pack()
        
        # Words to repeat
        repeat_frame = ttk.Frame(stats_container, style='Card.TFrame', padding="20")
        repeat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(repeat_frame, text=str(words_to_repeat), font=('Segoe UI', 24, 'bold'), 
                 foreground='#dc3545', background='#ffffff').pack()
        ttk.Label(repeat_frame, text="Need Review", style='Body.TLabel').pack()
        
        # Words to repeat list
        if self.difficult_words:
            ttk.Label(main_frame, text="Words that need more practice:", style='Subheading.TLabel').pack(pady=(20, 10), anchor='w')
            
            # Scrollable list
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
            
            listbox = tk.Listbox(list_frame, 
                               font=('Segoe UI', 11),
                               bg='#f8f9fa',
                               fg='#495057',
                               selectbackground='#0078d4',
                               selectforeground='white',
                               relief='flat',
                               borderwidth=0,
                               activestyle='none')
            
            scrollbar_list = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar_list.set)
            
            for (s, t) in self.difficult_words:
                listbox.insert(tk.END, f"  {s} → {t}")
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
          # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Finish", command=self.save_and_exit, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_frame, text="Generate New Text", command=self.generate_new_text, style='Modern.TButton').pack(side=tk.LEFT)

    def save_and_exit(self):
        if self.save_allowed:
            for (source, target, _) in self.vocab_list:
                if (source, target) in self.difficult_words:
                    self.word_tracker.mark_word_not_understood(source, target)
                else:
                    self.word_tracker.mark_word_used(source, target)
            self.word_tracker.save_tracking_data()
        self.review_complete = True
        self.root.quit()
        self.root.destroy()

    def generate_new_text(self):
        self.save_and_exit()

    def on_close(self):
        # If not checked in feedback, do not save
        self.review_complete = False
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        import sys
        sys.exit(0)
        return self.review_complete

    def setup_audio_controls(self):
        """Setup audio controls at the bottom of the interface"""
        for widget in self.audio_controls_frame.winfo_children():
            widget.destroy()

        # Always show the audio controls area, even if no audio file is present
        audio_frame = ttk.LabelFrame(self.audio_controls_frame, padding="15")
        audio_frame.pack(fill=tk.X, padx=10, pady=5)

        if self.audio_path and os.path.exists(self.audio_path):
            # Initialize VLC player
            self.vlc_player = self.vlc_instance.media_player_new() # type: ignore
            media = self.vlc_instance.media_new(self.audio_path) # type: ignore
            self.vlc_player.set_media(media)
            
            # Top row - Main playback controls
            controls_row = ttk.Frame(audio_frame)
            controls_row.pack(fill=tk.X, pady=(0, 10))
            
            # Playback controls (centered)
            playback_frame = ttk.Frame(controls_row)
            playback_frame.pack(expand=True)
            
            self.play_btn = ttk.Button(playback_frame, text="▶ Play", command=self.play_audio, style='Accent.TButton')
            self.play_btn.pack(side=tk.LEFT, padx=5)
            
            self.pause_btn = ttk.Button(playback_frame, text="⏸ Pause", command=self.pause_audio, style='Modern.TButton')
            self.pause_btn.pack(side=tk.LEFT, padx=5)
            
            self.stop_btn = ttk.Button(playback_frame, text="⏹ Stop", command=self.stop_audio, style='Modern.TButton')
            self.stop_btn.pack(side=tk.LEFT, padx=5)
            
            # Separator
            ttk.Separator(playback_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=15)
            
            # Jump controls (prominent)
            self.jump_back_btn = ttk.Button(playback_frame, text="⏪ -4s", command=lambda: self.jump_audio(-4), style='Modern.TButton')
            self.jump_back_btn.pack(side=tk.LEFT, padx=5)
            
            self.jump_forward_btn = ttk.Button(playback_frame, text="+4s ⏩", command=lambda: self.jump_audio(4), style='Modern.TButton')
            self.jump_forward_btn.pack(side=tk.LEFT, padx=5)
            
            # Separator
            ttk.Separator(playback_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=15)
            
            # Speed controls
            ttk.Label(playback_frame, text="Speed:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 5))
            self.slower_btn = ttk.Button(playback_frame, text="-5%", command=lambda: self.change_speed(-0.05), style='Modern.TButton')
            self.slower_btn.pack(side=tk.LEFT, padx=2)
            
            self.faster_btn = ttk.Button(playback_frame, text="+5%", command=lambda: self.change_speed(0.05), style='Modern.TButton')
            self.faster_btn.pack(side=tk.LEFT, padx=2)
            
            # Bottom row - Progress bar
            progress_row = ttk.Frame(audio_frame)
            progress_row.pack(fill=tk.X)
            
            ttk.Label(progress_row, style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 10))
            
            self.audio_progress = tk.DoubleVar()
            self.audio_progress_bar = ttk.Scale(progress_row, 
                                              variable=self.audio_progress, 
                                              length=500, 
                                              from_=0, 
                                              to=100, 
                                              orient=tk.HORIZONTAL, 
                                              command=self.slider_seek_update)
            self.audio_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            self.audio_progress_bar.bind('<ButtonRelease-1>', self.slider_seek_commit)
            
            # Time display
            self.time_label = ttk.Label(progress_row, text="00:00 / 00:00", style='Body.TLabel')
            self.time_label.pack(side=tk.LEFT, padx=(10, 0))
            
            # Initialize audio variables
            self.audio_length = 1
            self.audio_speed = 1.0
            self._slider_dragging = False
            self.update_audio_progress()
        else:
            # Show disabled controls if no audio available
            controls_row = ttk.Frame(audio_frame)
            controls_row.pack(fill=tk.X, pady=(0, 10))
            playback_frame = ttk.Frame(controls_row)
            playback_frame.pack(expand=True)
            ttk.Button(playback_frame, text="▶ Play", state=tk.DISABLED, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Button(playback_frame, text="⏸ Pause", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Button(playback_frame, text="⏹ Stop", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Separator(playback_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=15)
            ttk.Button(playback_frame, text="⏪ -4s", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Button(playback_frame, text="+4s ⏩", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=5)
            ttk.Separator(playback_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=15)
            ttk.Label(playback_frame, style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(playback_frame, text="-5%", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=2)
            ttk.Button(playback_frame, text="+5%", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=2)
            progress_row = ttk.Frame(audio_frame)
            progress_row.pack(fill=tk.X)
            ttk.Label(progress_row, text="Progress:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 10))
            ttk.Scale(progress_row, length=500, from_=0, to=100, orient=tk.HORIZONTAL, state=tk.DISABLED).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            ttk.Label(progress_row, text="00:00 / 00:00", style='Body.TLabel').pack(side=tk.LEFT, padx=(10, 0))
            # Message
            ttk.Label(audio_frame, text="No audio file available", style='Body.TLabel').pack(pady=10)

def run_vocabulary_review(vocab_list, word_tracker, generated_text=None, audio_path=None):
    app = VocabularyReviewer(vocab_list, word_tracker, generated_text, audio_path)
    return app.run()