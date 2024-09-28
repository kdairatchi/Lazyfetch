import os
import json
import time
import requests
import sqlite3
import tkinter as tk
from tkinter import scrolledtext, ttk
from bs4 import BeautifulSoup
import openai
import schedule
import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# OpenAI API and Telegram Token
openai.api_key = "YOUR_OPENAI_API_KEY"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# SQLite Database Setup
DATABASE = 'cybersecurity_data.db'

def setup_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payloads (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  payload TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS vulnerabilities (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT,
                  content TEXT
                )''')
    conn.commit()
    conn.close()

# Scraping Sources
SOURCES = {
    "xss_payloads": "https://portswigger.net/web-security/cross-site-scripting/cheat-sheet#onanimationstart",
    "directory_listing": [
        "https://portswigger.net/kb/issues/00600100_directory-listing",
        "https://www.invicti.com/learn/directory-listing/"
    ],
    "vulnerabilities": [
        "https://cwe.mitre.org/data/index.html",
        "https://www.cvedetails.com",
        "https://nvd.nist.gov/vuln/",
        "https://cve.mitre.org",
        "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
    ]
}

# GUI Setup with Tkinter
class CyberToolkitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cybersecurity Toolkit")
        
        self.tab_control = ttk.Notebook(root)
        
        # Tab 1: XSS Testing
        self.xss_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.xss_tab, text="XSS Testing")
        self.output = scrolledtext.ScrolledText(self.xss_tab, wrap=tk.WORD, width=100, height=20)
        self.output.grid(column=0, row=0, padx=10, pady=10)
        self.start_button = tk.Button(self.xss_tab, text="Start XSS Testing", command=self.run_tests)
        self.start_button.grid(column=0, row=1, pady=10)

        # Tab 2: Payload Management
        self.payload_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.payload_tab, text="Payload Management")
        self.payload_output = scrolledtext.ScrolledText(self.payload_tab, wrap=tk.WORD, width=100, height=20)
        self.payload_output.grid(column=0, row=0, padx=10, pady=10)
        self.load_payloads()

        # Tab 3: Vulnerability Updates
        self.vuln_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.vuln_tab, text="Vulnerability Updates")
        self.vuln_output = scrolledtext.ScrolledText(self.vuln_tab, wrap=tk.WORD, width=100, height=20)
        self.vuln_output.grid(column=0, row=0, padx=10, pady=10)

        # Add Tabs to Window
        self.tab_control.pack(expand=1, fill='both')

    def run_tests(self):
        payloads = self.get_payloads()
        for payload in payloads:
            response = requests.post(target_url, data={'input': payload}, headers=mobile_user_agent)
            soup = BeautifulSoup(response.text, 'html.parser')
            if payload in soup.text:
                result = f"Possible XSS vulnerability detected with payload: {payload}\n"
            else:
                result = f"Payload: {payload} did not trigger XSS\n"
            self.output.insert(tk.END, result)
            self.output.see(tk.END)
            self.root.update_idletasks()
            if "Possible XSS vulnerability" in result:
                self.generate_ai_analysis(payload, response.text)

    def generate_ai_analysis(self, payload, response):
        try:
            analysis_prompt = (
                f"The following response may contain an XSS vulnerability caused by the payload: {payload}\n"
                f"Response:\n{response}\n"
                "Explain the potential impact and possible fixes for this vulnerability."
            )
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=analysis_prompt,
                max_tokens=150
            )
            analysis_result = f"AI Analysis: {response.choices[0].text.strip()}\n"
            self.output.insert(tk.END, analysis_result)
            self.output.see(tk.END)
            self.root.update_idletasks()
        except Exception as e:
            self.output.insert(tk.END, f"Error with OpenAI API: {str(e)}\n")
            self.output.see(tk.END)
            self.root.update_idletasks()

    def get_payloads(self):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT payload FROM payloads')
        rows = c.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def load_payloads(self):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT id, payload FROM payloads')
        rows = c.fetchall()
        conn.close()
        self.payload_output.delete('1.0', tk.END)
        for row in rows:
            self.payload_output.insert(tk.END, f"ID: {row[0]}, Payload: {row[1][:100]}...\n")

# Telegram Bot Integration
def start(update: Update, _: CallbackContext) -> None:
    update.message.reply_text('Hello! I am your cybersecurity bot. Use /fetch to see vulnerabilities or /list_payloads to view XSS payloads.')

def fetch_command(update: Update, _: CallbackContext) -> None:
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, category, content FROM vulnerabilities')
    rows = c.fetchall()
    conn.close()

    response_text = "🔒 *Latest Cybersecurity Information* 🔒\n\n"
    for row in rows:
        response_text += f"ID: {row[0]}, *{row[1].capitalize()}*\n{row[2]}...\n\n"

    update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)

# Telegram Bot Setup
def main():
    setup_database()

    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("fetch", fetch_command))

    updater.start_polling()
    logging.info("Bot is now polling for commands...")
    updater.idle()

# Main Program Setup
if __name__ == "__main__":
    root = tk.Tk()
    app = CyberToolkitApp(root)
    main()  # Start the Telegram bot in parallel
    root.mainloop()
