import tkinter as tk
from tkinter import messagebox

from config import API_BASE_URL
from server.enroll import enroll


class EnrollmentWindow:
    def __init__(self):
        self.root = tk.Tk()

        self.root.title("SLMS Client Agent")
        self.root.geometry("500x360")
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.create_widgets()

    def create_widgets(self):
        # Main container
        frame = tk.Frame(
            self.root,
            padx=35,
            pady=25,
        )
        frame.pack(fill="both", expand=True)

        # Title
        title = tk.Label(
            frame,
            text="SLMS Client Agent",
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(pady=(0, 5))

        subtitle = tk.Label(
            frame,
            text="Register this computer with the Smart Lab Management System",
            font=("Segoe UI", 9),
            wraplength=400,
        )
        subtitle.pack(pady=(0, 25))

        # Server URL
        server_label = tk.Label(
            frame,
            text="Server URL",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        server_label.pack(fill="x")

        self.server_entry = tk.Entry(
            frame,
            font=("Segoe UI", 10),
        )
        self.server_entry.pack(
            fill="x",
            ipady=7,
            pady=(5, 15),
        )

        self.server_entry.insert(0, API_BASE_URL)

        # Enrollment key
        key_label = tk.Label(
            frame,
            text="Enrollment Key",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        key_label.pack(fill="x")

        self.key_entry = tk.Entry(
            frame,
            font=("Segoe UI", 10),
            show="*",
        )
        self.key_entry.pack(
            fill="x",
            ipady=7,
            pady=(5, 20),
        )

        # Enroll button
        self.enroll_button = tk.Button(
            frame,
            text="Enroll Computer",
            font=("Segoe UI", 10, "bold"),
            command=self.handle_enrollment,
            padx=20,
            pady=8,
        )
        self.enroll_button.pack()

        # Status
        self.status_label = tk.Label(
            frame,
            text="",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(pady=(15, 0))

    def handle_enrollment(self):
        server_url = self.server_entry.get().strip()
        enrollment_key = self.key_entry.get().strip()

        if not server_url:
            messagebox.showerror(
                "Invalid Server URL",
                "Please enter the SLMS server URL.",
                parent=self.root,
            )
            return

        if not enrollment_key:
            messagebox.showerror(
                "Missing Enrollment Key",
                "Please enter the enrollment key.",
                parent=self.root,
            )
            return

        self.enroll_button.config(
            state="disabled",
            text="Enrolling...",
        )

        self.status_label.config(
            text="Connecting to SLMS server..."
        )

        self.root.update_idletasks()

        try:
            result = enroll(
                enrollment_key=enrollment_key,
                server_url=server_url,
            )

            self.status_label.config(
                text="Enrollment successful."
            )

            messagebox.showinfo(
                "Enrollment Successful",
                (
                    "This computer has been successfully registered "
                    "with SLMS.\n\n"
                    f"Computer ID: {result['computer_id']}"
                ),
                parent=self.root,
            )

            self.root.destroy()

        except Exception as error:
            self.status_label.config(
                text="Enrollment failed."
            )

            messagebox.showerror(
                "Enrollment Failed",
                str(error),
                parent=self.root,
            )

            self.enroll_button.config(
                state="normal",
                text="Enroll Computer",
            )

    def close(self):
        self.root.destroy()


def show_enrollment_window():
    window = EnrollmentWindow()
    window.root.mainloop()