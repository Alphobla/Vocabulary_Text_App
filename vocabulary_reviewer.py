import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
import vlc

class VocabularyReviewer:
    def __init__(self, vocab_list, word_tracker, generated_text=None, audio_path=None):
        self.vocab_list = vocab_list
        self.word_tracker = word_tracker
        self.generated_text = generated_text
        self.audio_path = audio_path
        self.difficult_words = set()
        self.review_complete = False
        self.tiles = []
        self.save_allowed = False
        self.root = tk.Tk()
        self.root.title("French Vocabulary Review")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        self.setup_start_view()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_start_view(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True)
        title = ttk.Label(main_frame, text="French Reading Practice", font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 20))
        if self.generated_text:
            text_frame = ttk.LabelFrame(main_frame, text="French Text", padding="15")
            text_frame.pack(pady=(0, 20))
            text_widget = tk.Text(text_frame, wrap=tk.WORD, width=70, height=15, font=('Arial', 12), bg='#fafafa', relief='flat', borderwidth=0)
            text_widget.pack()
            text_widget.insert('1.0', self.generated_text)
            text_widget.config(state='disabled')
        if self.audio_path and os.path.exists(self.audio_path):
            self.vlc_instance = vlc.Instance()
            self.vlc_player = self.vlc_instance.media_player_new()
            media = self.vlc_instance.media_new(self.audio_path)
            self.vlc_player.set_media(media)
            audio_frame = ttk.Frame(main_frame)
            audio_frame.pack(pady=(0, 20))
            self.play_btn = ttk.Button(audio_frame, text="▶️ Play Audio", command=self.play_audio)
            self.play_btn.pack(side=tk.LEFT, padx=5)
            self.pause_btn = ttk.Button(audio_frame, text="⏸️ Pause", command=self.pause_audio)
            self.pause_btn.pack(side=tk.LEFT, padx=5)
            self.stop_btn = ttk.Button(audio_frame, text="⏹️ Stop", command=self.stop_audio)
            self.stop_btn.pack(side=tk.LEFT, padx=5)
            self.slower_btn = ttk.Button(audio_frame, text="-5%", command=lambda: self.change_speed(-0.05))
            self.slower_btn.pack(side=tk.LEFT, padx=5)
            self.faster_btn = ttk.Button(audio_frame, text="+5%", command=lambda: self.change_speed(0.05))
            self.faster_btn.pack(side=tk.LEFT, padx=5)
            self.audio_progress = tk.DoubleVar()
            self.audio_progress_bar = ttk.Scale(audio_frame, variable=self.audio_progress, length=300, from_=0, to=100, orient=tk.HORIZONTAL, command=self.slider_seek_update)
            self.audio_progress_bar.pack(side=tk.LEFT, padx=10)
            self.audio_progress_bar.bind('<ButtonRelease-1>', self.slider_seek_commit)
            # Add -2s and +2s jump buttons
            self.jump_back_btn = ttk.Button(audio_frame, text="-2s", command=lambda: self.jump_audio(-2))
            self.jump_back_btn.pack(side=tk.LEFT, padx=2)
            self.jump_forward_btn = ttk.Button(audio_frame, text="+2s", command=lambda: self.jump_audio(2))
            self.jump_forward_btn.pack(side=tk.LEFT, padx=2)
            self.audio_length = 1
            self.audio_speed = 1.0
            self._slider_dragging = False
            self.update_audio_progress()
        btn = ttk.Button(main_frame, text="Check Vocabulary", command=self.setup_tile_view, style='Accent.TButton')
        btn.pack(pady=30)

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
        self.play_btn.config(text=f"▶️ Play Audio ({int(self.audio_speed*100)}%)")

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
            except:
                pass
        self.root.after(200, self.update_audio_progress)

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
        for widget in self.root.winfo_children():
            widget.destroy()
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)
        title = ttk.Label(main_frame, text="Click words you want to repeat", font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 20))
        tiles_frame = ttk.Frame(main_frame)
        tiles_frame.pack(pady=10)
        self.tiles = []
        for i, (french, german) in enumerate(self.vocab_list):
            tile = ttk.Button(tiles_frame, text=f"{french} → {german}", width=25, style='Tile.TButton')
            tile.grid(row=i//3, column=i%3, padx=10, pady=10)
            tile.config(command=lambda t=tile, w=(french, german): self.toggle_tile(t, w))
            self.tiles.append((tile, (french, german)))
        btn = ttk.Button(main_frame, text="Check in Feedback", command=self.check_feedback, style='Accent.TButton')
        btn.pack(pady=30)

    def toggle_tile(self, tile, word):
        if word in self.difficult_words:
            self.difficult_words.remove(word)
            tile.state(['!selected'])
            tile.config(style='Tile.TButton')
        else:
            self.difficult_words.add(word)
            tile.state(['selected'])
            tile.config(style='SelectedTile.TButton')

    def check_feedback(self):
        self.save_allowed = True
        for widget in self.root.winfo_children():
            widget.destroy()
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True)
        summary = ttk.Label(main_frame, text=f"Words to repeat: {len(self.difficult_words)}\nWords known: {len(self.vocab_list) - len(self.difficult_words)}", font=('Arial', 14))
        summary.pack(pady=20)
        if self.difficult_words:
            words = '\n'.join([f"• {f} → {g}" for (f, g) in self.difficult_words])
            lbl = ttk.Label(main_frame, text=f"To repeat:\n{words}", font=('Arial', 12))
            lbl.pack(pady=10)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Close", command=self.save_and_exit).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Generate New Text", command=self.generate_new_text).pack(side=tk.LEFT, padx=10)

    def save_and_exit(self):
        if self.save_allowed:
            for (french, german) in self.vocab_list:
                if (french, german) in self.difficult_words:
                    self.word_tracker.mark_word_not_understood(french, german)
                else:
                    self.word_tracker.mark_word_used(french, german)
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
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 12, 'bold'))
        style.configure('Tile.TButton', font=('Arial', 11), background='#e0e0e0')
        style.configure('SelectedTile.TButton', font=('Arial', 11, 'bold'), background='#ffcccc')
        self.root.mainloop()
        import sys
        sys.exit(0)
        return self.review_complete

def run_vocabulary_review(vocab_list, word_tracker, generated_text=None, audio_path=None):
    app = VocabularyReviewer(vocab_list, word_tracker, generated_text, audio_path)
    return app.run()