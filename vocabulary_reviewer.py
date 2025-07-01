import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
import vlc
import sys
import subprocess
import threading

class VocabularyReviewer:
    def __init__(self, vocab_list, word_tracker, generated_text=None, audio_path=None, example_sentences=None):
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
        self.example_sentences = example_sentences or {}
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
        
        # Pull latest changes from Git on startup
        print("🔄 Syncing with Git repository...")
        self.sync_git_async("pull")
        
        self.setup_start_view()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def git_pull(self):
        """Pull latest changes from Git repository"""
        try:
            # Get the directory containing the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Run git pull in the script directory
            result = subprocess.run(['git', 'pull'], 
                                  cwd=script_dir, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            if result.returncode == 0:
                print("✅ Successfully pulled latest changes from Git")
                return True
            else:
                # Check for authentication failures
                error_msg = result.stderr.lower()
                if any(auth_error in error_msg for auth_error in [
                    'authentication failed', 'access denied', 'permission denied',
                    'could not read username', 'could not read password',
                    'repository not found', '403', '401', 'unauthorized'
                ]):
                    print("🔐 Git authentication failed. Please check your credentials:")
                    print("   • For HTTPS: Update stored credentials in Windows Credential Manager")
                    print("   • For SSH: Ensure your SSH keys are set up correctly")
                    print("   • Consider using a Personal Access Token for GitHub")
                else:
                    print(f"⚠️ Git pull warning: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Git pull timed out - this might indicate network or authentication issues")
            return False
        except FileNotFoundError:
            print("⚠️ Git not found. Make sure Git is installed and in PATH")
            return False
        except Exception as e:
            print(f"⚠️ Git pull error: {e}")
            return False
    
    def git_commit_and_push(self, message="Update vocabulary tracking data"):
        """Commit and push changes to Git repository"""
        try:
            # Get the directory containing the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Add all changes
            add_result = subprocess.run(['git', 'add', '.'], 
                          cwd=script_dir, 
                          capture_output=True, 
                          text=True, 
                          timeout=30)
            
            if add_result.returncode != 0:
                print(f"⚠️ Git add failed: {add_result.stderr}")
                return False
            
            # Commit changes
            commit_result = subprocess.run(['git', 'commit', '-m', message], 
                                         cwd=script_dir, 
                                         capture_output=True, 
                                         text=True, 
                                         timeout=30)
            
            if commit_result.returncode == 0:
                # Push changes
                push_result = subprocess.run(['git', 'push'], 
                                           cwd=script_dir, 
                                           capture_output=True, 
                                           text=True, 
                                           timeout=30)
                
                if push_result.returncode == 0:
                    print("✅ Successfully committed and pushed changes to Git")
                    return True
                else:
                    # Check for authentication failures in push
                    error_msg = push_result.stderr.lower()
                    if any(auth_error in error_msg for auth_error in [
                        'authentication failed', 'access denied', 'permission denied',
                        'could not read username', 'could not read password',
                        'repository not found', '403', '401', 'unauthorized',
                        'support for password authentication was removed'
                    ]):
                        print("🔐 Git push authentication failed. Common solutions:")
                        print("   • GitHub: Use Personal Access Token instead of password")
                        print("   • Run: git config --global credential.helper manager-core")
                        print("   • Or switch to SSH: git remote set-url origin git@github.com:user/repo.git")
                    else:
                        print(f"⚠️ Git push error: {push_result.stderr}")
                    return False
            else:
                # Check if there were no changes to commit
                if "nothing to commit" in commit_result.stdout:
                    print("ℹ️ No changes to commit")
                    return True
                else:
                    print(f"⚠️ Git commit error: {commit_result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            print("⚠️ Git operation timed out - check network connection and authentication")
            return False
        except FileNotFoundError:
            print("⚠️ Git not found. Make sure Git is installed and in PATH")
            return False
        except Exception as e:
            print(f"⚠️ Git operation error: {e}")
            return False
    
    def sync_git_async(self, operation="pull"):
        """Run Git operations in a separate thread to avoid blocking UI"""
        def run_git():
            if operation == "pull":
                self.git_pull()
            elif operation == "push":
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.git_commit_and_push(f"Update vocabulary tracking - {timestamp}")
        
        thread = threading.Thread(target=run_git, daemon=True)
        thread.start()
        
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
        
        # White frame style for feedback view
        style.configure('White.TFrame',
                       background='#ffffff',
                       relief='flat',
                       borderwidth=0)

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
        
        # Tiles grid (4 columns x 5 rows, max 20 items, no scrolling)
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(expand=True)
        
        self.tiles = []
        cols = 4
        rows = 5
        max_tiles = cols * rows
        vocab_to_show = self.vocab_list[:max_tiles]
        
        for i, (source, target, pronunciation) in enumerate(vocab_to_show):
            if pronunciation:
                tile_text = f"{source} [{pronunciation}] → {target}"
            else:
                tile_text = f"{source} → {target}"
            tile = ttk.Button(grid_frame, text=tile_text, width=30, style='Tile.TButton')
            row = i // cols
            col = i % cols
            tile.grid(row=row, column=col, padx=15, pady=10, sticky="ew")
            tile.config(command=lambda t=tile, w=(source, target): self.toggle_tile(t, w))
            self.tiles.append((tile, (source, target)))
        
        for col in range(cols):
            grid_frame.columnconfigure(col, weight=1)
        
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
        print("DEBUG: check_feedback called")
        # DEBUG: Check and populate difficult_words for testing purposes
        print(f"--- Entering check_feedback ---")
        print(f"Initial difficult_words: {self.difficult_words}")
        if not self.difficult_words:
            print("DEBUG: difficult_words is empty. Populating with test data for display.")
            # Using a sample of words that exist in the test_vocab
            self.difficult_words = {
                ('hello', 'hola'),
                ('goodbye', 'adiós'),
                ('please', 'por favor')
            }

        self.save_allowed = True
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
        # Set root background to white
        self.root.configure(bg='white')
        
        # Main container - use tk.Frame for explicit white background
        main_frame = tk.Frame(self.content_frame, bg='white')
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Header row: Title (left), Action buttons (right)
        header_frame = tk.Frame(main_frame, bg='white')
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        title = tk.Label(header_frame, text="Review Complete", font=('Segoe UI', 20, 'bold'), 
                        bg='white', fg='#212529')
        title.pack(side=tk.LEFT)
        
        # Action buttons on the right
        btn_frame = tk.Frame(header_frame, bg='white')
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Generate New Text", command=self.generate_new_text, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_frame, text="Finish", command=self.save_and_exit, style='Accent.TButton').pack(side=tk.LEFT)
        
        # Statistics visualization (skip for now)
        # stats_frame = ttk.Frame(main_frame, style='Card.TFrame')
        # stats_frame.pack(pady=(0, 30), fill=tk.X)
        
        # Content area with horizontal layout (white background)
        content_frame = tk.Frame(main_frame, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 20))
        
        # Left section: Two-column grid of tiles (narrower)
        tiles_section = tk.Frame(content_frame, bg='white')
        tiles_section.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        tiles_label = tk.Label(tiles_section, text="Words that need more practice:", 
                              font=('Segoe UI', 14), bg='white', fg='#6c757d')
        tiles_label.pack(anchor='w', pady=(0, 10))
        
        # Grid container for tiles (fixed width)
        grid_frame = tk.Frame(tiles_section, bg='white', width=400)
        grid_frame.pack(fill=tk.Y)
        grid_frame.pack_propagate(False)  # Maintain fixed width
        
        # Create tiles in 2-column grid
        if self.difficult_words:
            tile_list = list(self.difficult_words)
            for idx, (source, target) in enumerate(tile_list):
                row = idx // 2
                col = idx % 2
                tile = self.create_compact_tile(grid_frame, source, target)
                tile.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            
            # Configure grid weights
            grid_frame.columnconfigure(0, weight=1)
            grid_frame.columnconfigure(1, weight=1)
        
        # Right section: Larger chart 
        chart_section = tk.Frame(content_frame, bg='white')
        chart_section.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, anchor='n')
        
        # Add some vertical space to align under buttons
        spacer = tk.Label(chart_section, text="", bg='white')
        spacer.pack(pady=(60, 0))
        
        self.create_urgency_chart(chart_section, width=300, height=200, minimal=True)

    def create_compact_tile(self, parent, source, target):
        """Create a compact tile widget with thin border"""
        tile_frame = tk.Frame(parent, bg='white', relief='solid', bd=1)
        
        # Inner padding frame
        inner_frame = tk.Frame(tile_frame, bg='white')
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Word row
        word_frame = tk.Frame(inner_frame, bg='white')
        word_frame.pack(fill=tk.X, pady=(0, 3))
        
        tk.Label(word_frame, text=source, font=('Segoe UI', 10, 'bold'), 
                fg='#2c3e50', bg='white').pack(side=tk.LEFT)
        tk.Label(word_frame, text=" → ", font=('Segoe UI', 9), 
                fg='#7f8c8d', bg='white').pack(side=tk.LEFT)
        tk.Label(word_frame, text=target, font=('Segoe UI', 10), 
                fg='#e74c3c', bg='white').pack(side=tk.LEFT)
        
        # Example sentence
        key = (source, target)
        if hasattr(self, 'example_sentences') and key in self.example_sentences:
            sentence = self.example_sentences[key]
            sentence_frame = tk.Frame(inner_frame, bg='white')
            sentence_frame.pack(fill=tk.X)
            
            tk.Label(sentence_frame, text="Example:", font=('Segoe UI', 7, 'italic'), 
                    fg='#95a5a6', bg='white').pack(anchor='w')
            tk.Label(sentence_frame, text=sentence, font=('Segoe UI', 8), 
                    fg='#34495e', bg='white', wraplength=150, justify='left').pack(anchor='w')
        
        return tile_frame


    def create_word_tile(self, parent, source, target, index, compact=False, extra_small=False):
        """Create a tile for a word that needs practice"""
        pad = "4" if extra_small else ("8" if compact else "20")
        font_main = ('Segoe UI', 9, 'bold') if extra_small else (('Segoe UI', 12, 'bold') if compact else ('Segoe UI', 16, 'bold'))
        font_arrow = ('Segoe UI', 8) if extra_small else (('Segoe UI', 11) if compact else ('Segoe UI', 14))
        font_target = ('Segoe UI', 9) if extra_small else (('Segoe UI', 12) if compact else ('Segoe UI', 16))
        font_example = ('Segoe UI', 7, 'italic') if extra_small else (('Segoe UI', 8, 'italic') if compact else ('Segoe UI', 10, 'italic'))
        font_sentence = ('Segoe UI', 8) if extra_small else (('Segoe UI', 9) if compact else ('Segoe UI', 11))
        wrap = 150 if extra_small else (250 if compact else 600)
        tile_frame = ttk.Frame(parent, style='Card.TFrame', padding=pad)
        tile_frame.pack(fill=tk.X, padx=2, pady=2)
        word_frame = ttk.Frame(tile_frame)
        word_frame.pack(fill=tk.X, pady=(0, 2) if extra_small else ((0, 4) if compact else (0, 10)))
        source_label = ttk.Label(word_frame, text=source, font=font_main, foreground='#2c3e50')
        source_label.pack(side=tk.LEFT)
        arrow_label = ttk.Label(word_frame, text=" → ", font=font_arrow, foreground='#7f8c8d')
        arrow_label.pack(side=tk.LEFT)
        target_label = ttk.Label(word_frame, text=target, font=font_target, foreground='#e74c3c')
        target_label.pack(side=tk.LEFT)
        key = (source, target)
        if hasattr(self, 'example_sentences') and key in self.example_sentences:
            sentence = self.example_sentences[key]
            sentence_frame = ttk.Frame(tile_frame)
            sentence_frame.pack(fill=tk.X, pady=(1, 0) if extra_small else ((2, 0) if compact else (5, 0)))
            example_label = ttk.Label(sentence_frame, text="Example:", font=font_example, foreground='#95a5a6')
            example_label.pack(side=tk.LEFT)
            sentence_label = ttk.Label(sentence_frame, text=sentence, font=font_sentence, foreground='#34495e', wraplength=wrap)
            sentence_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_urgency_chart(self, parent_frame, width=350, height=120, minimal=False):
        import tkinter as tk
        chart_canvas = tk.Canvas(parent_frame, width=width, height=height, bg='white', highlightthickness=1, highlightbackground='#dee2e6')
        chart_canvas.pack()
        # Create set of session words (vocab_list) for quick lookup
        session_words = set((source, target) for source, target, _ in self.vocab_list)
        
        # Collect before/after data for all words
        word_data = []
        
        # Use all words from word_tracker's data (JSON file), not just vocab_list
        if hasattr(self.word_tracker, 'word_stats') and self.word_tracker.word_stats:
            # Parse keys from JSON tracking data (format: "source|target")
            for word_key in self.word_tracker.word_stats.keys():
                if '|' in word_key:
                    source, target = word_key.split('|', 1)
                    before_urgency = self.word_tracker.calculate_word_priority(source, target)
                    
                    # Only apply -20 for session words that are not difficult_words
                    if (source, target) in session_words and (source, target) not in self.difficult_words:
                        after_urgency = max(0, before_urgency - 20)
                    elif (source, target) in self.difficult_words:
                        after_urgency = min(100, before_urgency + 5)
                    else:
                        # All other words keep their original urgency
                        after_urgency = before_urgency
                    
                    word_data.append((before_urgency, after_urgency))
                else:
                    print(f"DEBUG: Invalid word key format: {word_key}. Expected 'source|target'. Skipping.")
        else:
            print("DEBUG: No tracking data found, using vocab_list for urgency chart.")
            # Fallback to vocab_list if no tracking data exists
            for source, target, _ in self.vocab_list:
                before_urgency = self.word_tracker.calculate_word_priority(source, target)
                after_urgency = max(0, before_urgency - 20) if (source, target) not in self.difficult_words else min(100, before_urgency + 5)
                word_data.append((before_urgency, after_urgency))
        
        # Sort before and after separately by urgency (highest first)
        before_urgencies = sorted([x[0] for x in word_data], reverse=True)
        after_urgencies = sorted([x[1] for x in word_data], reverse=True)
        
        margin = 10
        chart_width = width - margin
        chart_height = height - margin
        # Minimal axes
        chart_canvas.create_line(margin, margin, margin, height - margin, fill='#bbb', width=1)
        chart_canvas.create_line(margin, height - margin, width - margin, height - margin, fill='#bbb', width=1)
        if len(before_urgencies) > 1:
            x_step = chart_width / (len(before_urgencies) - 1)
            before_points = []
            after_points = []
            for i, (before, after) in enumerate(zip(before_urgencies, after_urgencies)):
                x = margin + i * x_step
                y_before = height - margin - (before / 100) * chart_height
                y_after = height - margin - (after / 100) * chart_height
                before_points.extend([x, y_before])
                after_points.extend([x, y_after])
            if len(before_points) >= 4:
                chart_canvas.create_line(before_points, fill='#dc3545', width=2, smooth=True)
            if len(after_points) >= 4:
                chart_canvas.create_line(after_points, fill='#28a745', width=2, smooth=True)
        # No labels, no title, just axes and lines

    def save_and_exit(self):
        if self.save_allowed:
            for (source, target, _) in self.vocab_list:
                if (source, target) in self.difficult_words:
                    self.word_tracker.mark_word_not_understood(source, target)
                else:
                    self.word_tracker.mark_word_used(source, target)
            print("💾 Saving new vocabulary tracking data...")
            self.word_tracker.save_tracking_data()
            
            # Commit and push changes to Git after saving
            print("🔄 Saving changes to Git repository...")
            self.sync_git_async("push")
            
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
            self.slower_btn = ttk.Button(playback_frame, text="🐌 -5%", command=lambda: self.change_speed(-0.05), style='Modern.TButton')
            self.slower_btn.pack(side=tk.LEFT, padx=2)
            
            self.faster_btn = ttk.Button(playback_frame, text="🐇 +5%", command=lambda: self.change_speed(0.05), style='Modern.TButton')
            self.faster_btn.pack(side=tk.LEFT, padx=2)
            
            # Bottom row - Progress bar
            progress_row = ttk.Frame(audio_frame)
            progress_row.pack(fill=tk.X)
            
            
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
            
            
            # Initialize audio variables
            self.audio_length = 1
            self.audio_speed = .9
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
            ttk.Button(playback_frame, text="🐌 -5%", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=2)
            ttk.Button(playback_frame, text="🐇 +5%", state=tk.DISABLED, style='Modern.TButton').pack(side=tk.LEFT, padx=2)
            progress_row = ttk.Frame(audio_frame)
            progress_row.pack(fill=tk.X)
            ttk.Scale(progress_row, length=500, from_=0, to=100, orient=tk.HORIZONTAL, state=tk.DISABLED).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            # Message
            ttk.Label(audio_frame, text="No audio file available", style='Body.TLabel').pack(pady=10)

def run_vocabulary_review(vocab_list, word_tracker, generated_text=None, audio_path=None, example_sentences=None):
    app = VocabularyReviewer(vocab_list, word_tracker, generated_text, audio_path, example_sentences)
    return app.run()