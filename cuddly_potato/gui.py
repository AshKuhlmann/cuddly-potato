import customtkinter as ctk  # type: ignore
import os
import json
from tkinter import filedialog, PhotoImage
from .database import get_db_connection, create_table, add_entry

# base64-encoded PNG icon used for the application window
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABRklEQVR4nO2aQQ7CMAwEAZUbT+c5vIS3"
    "cAMJThaoKoqdJh1H3TkXMh4ChZbj/XZ9H3bMiRagUQBagEYBaAEaBaAFaBSAFqBRAFqARgFoARoFoAVo"
    "pi0Xu0xP97GP17mjyZduASLDeh/fI0rzAGsH9zx3yxDNAvQc/N9aLUKsDrDl4P/WXhOiOgA5+Jw1IapO"
    "g5mG/6XGKxwg6/BG1C8UIPvwRsTTHWCU4Q2v7+6/CrsCjPbqGx5v7YDSAaO++kbJXzuAFqBRAFqARgFo"
    "AZpigK2uzfWi5K8d4Dlo1F3g8dYO8B442i7w+oZ2wCgRIp7ht0D2CFG/qs+ArBFqvKovi9tiGX4uI/cF"
    "5osTIVLcGTK2DJHy3qDRM8QQd4eNJdld/T9giYxnD30VpgVoFIAWoFEAWoBGAWgBGgWgBWgUgBagUQBa"
    "gOYDSKBZnljcWAkAAAAASUVORK5CYII="
)

# --- Start of New Code ---
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


# --- End of New Code ---


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Basic Window Configuration ---
        self.title("Cuddly Potato \U0001f954")
        self.geometry("700x750")

        # --- Set App Icon ---
        try:
            self.iconphoto(True, PhotoImage(data=ICON_BASE64))
        except Exception:
            print("Icon could not be loaded.")

        ctk.set_appearance_mode("System")  # "Dark", "Light", "System"
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(1, weight=1)

        last_db_path = load_last_db_path()
        self.db_path = last_db_path if last_db_path else "cuddly_potato.db"
        if not last_db_path and not os.path.isabs(self.db_path):
            save_last_db_path(os.path.abspath(self.db_path))

        # --- Widget Creation ---

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
            row=6, column=0, columnspan=2, padx=20, pady=20, sticky="ew"
        )

        # Status Bar
        self.status_label = ctk.CTkLabel(
            self, text="Welcome! Fill in the fields and click add.", text_color="gray"
        )
        self.status_label.grid(
            row=7, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w"
        )

    def create_input_widgets(self):
        """Creates and places all the labels and input fields."""
        # --- Model ---
        self.model_label = ctk.CTkLabel(self, text="Model")
        self.model_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model_entry = ctk.CTkEntry(self, placeholder_text="e.g., Gemma3 27B")
        self.model_entry.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="ew")

        # --- Domain & Subdomain ---
        self.domain_label = ctk.CTkLabel(self, text="Domain")
        self.domain_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.domain_entry = ctk.CTkEntry(self, placeholder_text="e.g., Math")
        self.domain_entry.grid(row=2, column=1, padx=20, pady=(10, 0), sticky="ew")

        self.subdomain_label = ctk.CTkLabel(self, text="Subdomain")
        self.subdomain_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.subdomain_entry = ctk.CTkEntry(self, placeholder_text="e.g., Basic Math")
        self.subdomain_entry.grid(row=3, column=1, padx=20, pady=(10, 0), sticky="ew")

        # --- Question (large text box) ---
        self.question_label = ctk.CTkLabel(self, text="Question")
        self.question_label.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="nw")
        self.question_textbox = ctk.CTkTextbox(self, height=150)
        self.question_textbox.grid(row=4, column=1, padx=20, pady=(20, 0), sticky="ew")

        # --- Answer (large text box) ---
        self.answer_label = ctk.CTkLabel(self, text="Answer")
        self.answer_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="nw")
        self.answer_textbox = ctk.CTkTextbox(self, height=200)
        self.answer_textbox.grid(row=5, column=1, padx=20, pady=(10, 0), sticky="ew")

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
            save_last_db_path(self.db_path)  # Save the new path
            display_path = self.db_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.db_path_label.configure(text=f"DB: {display_path}")
            self.status_label.configure(
                text=f"Database set to {self.db_path}", text_color="gray"
            )

    def submit_data(self):
        """Handles the logic for adding the data to the database."""
        question = self.question_textbox.get("1.0", "end-1c")
        model = self.model_entry.get()
        answer = self.answer_textbox.get("1.0", "end-1c")
        domain = self.domain_entry.get() or None
        subdomain = self.subdomain_entry.get() or None

        if not all([question, model, answer]):
            self.status_label.configure(
                text="Error: Question, Model, and Answer are required.",
                text_color="red",
            )
            return

        try:
            conn = get_db_connection(self.db_path)
            create_table(conn)
            add_entry(conn, question, model, answer, domain, subdomain, comments=None)
            conn.close()

            self.status_label.configure(
                text="Entry added successfully!", text_color="green"
            )
            self.question_textbox.delete("1.0", "end")
            self.answer_textbox.delete("1.0", "end")
            self.model_entry.delete(0, "end")
        except Exception as e:  # pragma: no cover - handle runtime errors
            self.status_label.configure(text=f"Error: {e}", text_color="red")


def launch_gui():
    """Initializes and runs the customtkinter application."""
    app = App()
    app.mainloop()
