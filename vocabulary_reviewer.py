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
                print(f"⚠️ Git pull warning: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Git pull timed out")
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
            subprocess.run(['git', 'add', '.'], 
                          cwd=script_dir, 
                          capture_output=True, 
                          text=True, 
                          timeout=30)
            
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
            print("⚠️ Git operation timed out")
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
    
        # Main container
        main_frame = ttk.Frame(self.content_frame, style='Card.TFrame', padding="40")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Header row: Title (left), Action buttons (right)
        header_frame = ttk.Frame(main_frame, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        title = ttk.Label(header_frame, text="Review Complete", style='Heading.TLabel')
        title.pack(side=tk.LEFT)
        
        # Action buttons on the right
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Generate New Text", command=self.generate_new_text, style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_frame, text="Finish", command=self.save_and_exit, style='Accent.TButton').pack(side=tk.LEFT)
        
        # Statistics visualization
        stats_frame = ttk.Frame(main_frame, style='Card.TFrame')
        stats_frame.pack(pady=(0, 30), fill=tk.X)
        
        # Create urgency visualization
        self.create_urgency_chart(stats_frame)
        
        # Words to repeat tiles with example sentences
        if self.difficult_words:
            ttk.Label(main_frame, text="Words that need more practice:", style='Subheading.TLabel').pack(pady=(20, 10), anchor='w')
            
            # Scrollable frame for tiles
            canvas_frame = ttk.Frame(main_frame)
            canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
            
            canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Create tiles for difficult words
            for i, (source, target) in enumerate(self.difficult_words):
                self.create_word_tile(scrollable_frame, source, target, i)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Bind mousewheel to canvas
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def create_word_tile(self, parent, source, target, index):
        """Create a tile for a word that needs practice"""
        # Tile container
        tile_frame = ttk.Frame(parent, style='Card.TFrame', padding="20")
        tile_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Word and translation
        word_frame = ttk.Frame(tile_frame)
        word_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Source word
        source_label = ttk.Label(word_frame, text=source, 
                                font=('Segoe UI', 16, 'bold'), 
                                foreground='#2c3e50')
        source_label.pack(side=tk.LEFT)
        
        # Arrow
        arrow_label = ttk.Label(word_frame, text=" → ", 
                               font=('Segoe UI', 14), 
                               foreground='#7f8c8d')
        arrow_label.pack(side=tk.LEFT)
        
        # Target word
        target_label = ttk.Label(word_frame, text=target, 
                                font=('Segoe UI', 16), 
                                foreground='#e74c3c')
        target_label.pack(side=tk.LEFT)
        
        # Example sentence (if available)
        key = (source, target)
        if key in self.example_sentences:
            sentence = self.example_sentences[key]
            sentence_frame = ttk.Frame(tile_frame)
            sentence_frame.pack(fill=tk.X, pady=(5, 0))
            
            # Example label
            example_label = ttk.Label(sentence_frame, text="Example: ", 
                                     font=('Segoe UI', 10, 'italic'), 
                                     foreground='#95a5a6')
            example_label.pack(side=tk.LEFT)
            
            # Sentence text
            sentence_label = ttk.Label(sentence_frame, text=sentence, 
                                      font=('Segoe UI', 11), 
                                      foreground='#34495e',
                                      wraplength=600)
            sentence_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_urgency_chart(self, parent_frame):
        """Create a line chart showing urgency levels before and after review"""
        import tkinter as tk
        
        # Chart frame
        chart_frame = ttk.Frame(parent_frame, style='Card.TFrame', padding="20")
        chart_frame.pack(fill=tk.X, pady=10)
        
        # Title
        ttk.Label(chart_frame, text="Vocabulary Urgency Progress", style='Subheading.TLabel').pack(pady=(0, 15))
        
        # Canvas for drawing the chart
        canvas_width = 800
        canvas_height = 300
        chart_canvas = tk.Canvas(chart_frame, width=canvas_width, height=canvas_height, bg='white', highlightthickness=1, highlightbackground='#dee2e6')
        chart_canvas.pack()
        
        # Get urgency data for all words using existing priority system
        before_urgencies = []
        after_urgencies = []
        
        for source, target, _ in self.vocab_list:
            # Get current urgency using WordTracker's calculate_word_priority
            before_urgency = self.word_tracker.calculate_word_priority(source, target)
            
            # Calculate after urgency based on whether word was marked difficult
            if (source, target) in self.difficult_words:
                # If marked as difficult, urgency stays high or increases slightly
                after_urgency = min(100, before_urgency + 10)
            else:
                # If not marked as difficult, urgency decreases significantly
                after_urgency = max(5, before_urgency - 25)
            
            before_urgencies.append(before_urgency)
            after_urgencies.append(after_urgency)
        
        # Sort by before urgency (descending) to create the dropping line effect
        word_data = list(zip(before_urgencies, after_urgencies))
        word_data.sort(key=lambda x: x[0], reverse=True)
        before_urgencies = [x[0] for x in word_data]
        after_urgencies = [x[1] for x in word_data]
        
        # Drawing parameters
        margin = 50
        chart_width = canvas_width - 2 * margin
        chart_height = canvas_height - 2 * margin
        
        # Draw axes
        # Y-axis (0-100)
        chart_canvas.create_line(margin, margin, margin, canvas_height - margin, fill='#6c757d', width=2)
        # X-axis
        chart_canvas.create_line(margin, canvas_height - margin, canvas_width - margin, canvas_height - margin, fill='#6c757d', width=2)
        
        # Y-axis labels and grid
        for i in range(0, 101, 25):
            y = canvas_height - margin - (i / 100) * chart_height
            chart_canvas.create_text(margin - 15, y, text=str(i), fill='#6c757d', font=('Segoe UI', 9))
            # Grid lines
            chart_canvas.create_line(margin, y, canvas_width - margin, y, fill='#e9ecef', width=1)
        
        # Y-axis title
        chart_canvas.create_text(15, canvas_height // 2, text='Urgency', fill='#6c757d', font=('Segoe UI', 10), angle=90)
        
        # X-axis label
        chart_canvas.create_text(canvas_width // 2, canvas_height - 10, text='Words (sorted by urgency)', fill='#6c757d', font=('Segoe UI', 10))
        
        if len(before_urgencies) > 1:
            # Calculate points for lines
            x_step = chart_width / (len(before_urgencies) - 1)
            
            before_points = []
            after_points = []
            
            for i, (before, after) in enumerate(zip(before_urgencies, after_urgencies)):
                x = margin + i * x_step
                y_before = canvas_height - margin - (before / 100) * chart_height
                y_after = canvas_height - margin - (after / 100) * chart_height
                
                before_points.extend([x, y_before])
                after_points.extend([x, y_after])
            
            # Draw BEFORE line (red)
            if len(before_points) >= 4:
                chart_canvas.create_line(before_points, fill='#dc3545', width=3, smooth=True)
            
            # Draw AFTER line (green)  
            if len(after_points) >= 4:
                chart_canvas.create_line(after_points, fill='#28a745', width=3, smooth=True)
        
        # Legend
        legend_frame = ttk.Frame(chart_frame)
        legend_frame.pack(pady=10)
        
        # Before legend
        before_legend = tk.Frame(legend_frame, bg='white')
        before_legend.pack(side=tk.LEFT, padx=(0, 20))
        before_color = tk.Canvas(before_legend, width=20, height=3, bg='#dc3545', highlightthickness=0)
        before_color.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(before_legend, text="Before this text", style='Body.TLabel').pack(side=tk.LEFT)
        
        # After legend
        after_legend = tk.Frame(legend_frame, bg='white')
        after_legend.pack(side=tk.LEFT)
        after_color = tk.Canvas(after_legend, width=20, height=3, bg='#28a745', highlightthickness=0)
        after_color.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(after_legend, text="After this text", style='Body.TLabel').pack(side=tk.LEFT)

    def save_and_exit(self):
        if self.save_allowed:
            for (source, target, _) in self.vocab_list:
                if (source, target) in self.difficult_words:
                    self.word_tracker.mark_word_not_understood(source, target)
                else:
                    self.word_tracker.mark_word_used(source, target)
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