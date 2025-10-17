import customtkinter as ctk  # type: ignore
import os
import json
from tkinter import filedialog, PhotoImage
from .database import get_db_connection, create_table, add_entry, get_last_entry

# base64-encoded PNG icon - A simple, clean gradient square icon (64x64)
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAC"
    "O0lEQVR4nO2aTU8UQRCGn+qZXVhY+VhRoogfMRr/gCdPxqPGi0ej8eDVeBBvHo0/wYMnT3oRDxI1"
    "RqMxRiMqKCKwLOzuzE51e9llWXZneme6e5f0m0zSmalU9zt0dU0VaLVarVbb/zgAGmgADaAK1O3v"
    "VbteDaoAA1TsZ8X+rth1VbuvYvdX7P6K3V+x+yv2ecXuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9"
    "Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2"
    "f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y"
    "3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/"
    "bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nu"
    "L9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2"
    "+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX"
    "7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6y3V+2+8t2f9nuL9v9Zbu/bPeX7f6K3V+x+yt2f8Xur9j9"
    "Fbu/YvdX7P6K3V+x+yv257LdX7Y/l+3PZftz2f5ctj+X7c9l+3PZ/ly2P5ftz2X7c9n+XLY/l+3P"
    "ZftzyX4u2c8l+7lkP5fs55L9XLKfS/ZzyX4u2c8l+7lkP5fs55L9XLKfS/Zz2X4u2/OyPV+151V7"
    "XrXn1T+p+bL9veRZ/VarrdD6BRmFGxK9ygKcAAAAAElFTkSuQmCC"
)

# Define the path for the configuration file in the user's home directory
CONFIG_DIR = os.path.expanduser("~/.cuddly-potato")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_last_db_path():
    """Load the last used database path from the config file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("last_db_path")
    except (json.JSONDecodeError, IOError):
        return None


def save_last_db_path(db_path):
    """Save the given database path to the config file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"last_db_path": db_path}, f)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Basic Window Configuration
        self.title("Cuddly Potato")
        self.geometry("800x900")

        # Set App Icon
        try:
            self.iconphoto(True, PhotoImage(data=ICON_BASE64))
        except Exception:
            print("Icon could not be loaded.")

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(1, weight=1)

        last_db_path = load_last_db_path()
        self.db_path = last_db_path if last_db_path else "cuddly_potato.db"
        if not last_db_path and not os.path.isabs(self.db_path):
            save_last_db_path(os.path.abspath(self.db_path))

        # Widget Creation
        # Database Path Selection
        self.db_frame = ctk.CTkFrame(self)
        self.db_frame.grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew"
        )
        self.db_frame.grid_columnconfigure(0, weight=1)

        self.db_path_label = ctk.CTkLabel(
            self.db_frame, text=f"DB: {self.db_path}", wraplength=500
        )
        self.db_path_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.db_button = ctk.CTkButton(
            self.db_frame, text="Select Database", command=self.select_db
        )
        self.db_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")

        # Input Fields
        self.create_input_widgets()

        # Submit Button
        self.submit_button = ctk.CTkButton(
            self, text="Add Entry to Database", command=self.submit_data
        )
        self.submit_button.grid(
            row=7, column=0, columnspan=2, padx=20, pady=20, sticky="ew"
        )

        # Status Bar
        self.status_label = ctk.CTkLabel(
            self, text="Welcome! Fill in the fields and click add.", text_color="gray"
        )
        self.status_label.grid(
            row=8, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w"
        )

    def create_input_widgets(self):
        """Creates and places all the labels and input fields."""
        # Author
        self.author_label = ctk.CTkLabel(self, text="Author")
        self.author_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.author_entry = ctk.CTkEntry(self, placeholder_text="e.g., John Doe")
        self.author_entry.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Tags
        self.tags_label = ctk.CTkLabel(self, text="Tags")
        self.tags_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.tags_entry = ctk.CTkEntry(
            self, placeholder_text="e.g., python, data, analysis"
        )
        self.tags_entry.grid(row=2, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Context (large text box)
        self.context_label = ctk.CTkLabel(self, text="Context")
        self.context_label.grid(row=3, column=0, padx=20, pady=(20, 0), sticky="nw")
        self.context_textbox = ctk.CTkTextbox(self, height=100)
        self.context_textbox.grid(row=3, column=1, padx=20, pady=(20, 0), sticky="ew")

        # Question (large text box)
        self.question_label = ctk.CTkLabel(self, text="Question")
        self.question_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="nw")
        self.question_textbox = ctk.CTkTextbox(self, height=100)
        self.question_textbox.grid(row=4, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Reason (large text box)
        self.reason_label = ctk.CTkLabel(self, text="Reason")
        self.reason_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="nw")
        self.reason_textbox = ctk.CTkTextbox(self, height=100)
        self.reason_textbox.grid(row=5, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Answer (large text box)
        self.answer_label = ctk.CTkLabel(self, text="Answer")
        self.answer_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="nw")
        self.answer_textbox = ctk.CTkTextbox(self, height=150)
        self.answer_textbox.grid(row=6, column=1, padx=20, pady=(10, 0), sticky="ew")

    def select_db(self):
        """Opens a file dialog to select the database file."""
        path = filedialog.askopenfilename(
            title="Select or Create Database File",
            initialfile="cuddly_potato.db",
            defaultextension=".db",
            filetypes=[("SQLite Databases", "*.db"), ("All files", "*.*")],
        )
        if path:
            self.db_path = path
            save_last_db_path(self.db_path)
            display_path = self.db_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.db_path_label.configure(text=f"DB: {display_path}")
            self.status_label.configure(
                text=f"Database set to {self.db_path}", text_color="gray"
            )

    def submit_data(self):
        """Handles the logic for adding the data to the database."""
        author = self.author_entry.get()
        tags = self.tags_entry.get()
        context = self.context_textbox.get("1.0", "end-1c")
        question = self.question_textbox.get("1.0", "end-1c")
        reason = self.reason_textbox.get("1.0", "end-1c")
        answer = self.answer_textbox.get("1.0", "end-1c")

        if not all([author, question, answer]):
            self.status_label.configure(
                text="Error: Author, Question, and Answer are required.",
                text_color="red",
            )
            return

        try:
            conn = get_db_connection(self.db_path)
            create_table(conn)
            add_entry(conn, author, tags, context, question, reason, answer)

            # Get the last entry to auto-fill author and tags for next entry
            last_entry = get_last_entry(conn)
            conn.close()

            self.status_label.configure(
                text="Entry added successfully!", text_color="green"
            )

            # Clear only the fields that should not be auto-filled
            self.context_textbox.delete("1.0", "end")
            self.question_textbox.delete("1.0", "end")
            self.reason_textbox.delete("1.0", "end")
            self.answer_textbox.delete("1.0", "end")

            # Keep author and tags from the last entry (which is the one we just added)
            # They're already filled, so we don't need to do anything!

        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")


def launch_gui():
    """Initializes and runs the customtkinter application."""
    app = App()
    app.mainloop()
