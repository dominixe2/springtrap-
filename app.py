"""Springtrap Windows desktop prototype. Python 3.10+, Windows 10/11, standard library only."""
import os
import queue
import subprocess
import threading
import webbrowser
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
from pathlib import Path

from brain.gemini_brain import GeminiBrain, GeminiBrainError
from key_store import load_key, save_key

APP_DIR = Path(__file__).resolve().parent
PS = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def powershell(script, timeout=60):
    return subprocess.run(
        PS + [script], capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


class SpringtrapApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.root.title("Springtrap")
        self.root.geometry("1000x760")
        self.root.minsize(620, 560)
        self.root.configure(bg="#101612")
        self.api_key = load_key()
        if not self.api_key:
            self.api_key = self._api_key_dialog(startup=True)
        if not self.api_key:
            self.root.destroy()
            raise SystemExit("Springtrap potřebuje Gemini API klíč pro spuštění.")
        self.events = queue.Queue()
        self.history = []
        self.busy = False
        self.speech_enabled = tk.BooleanVar(value=True)
        self.active_character = "Springtrap"
        self._build_ui()
        self.root.state("zoomed")
        self.root.deiconify()
        self.root.after(100, self._poll_events)
        self._append("Springtrap", "Jsem vzhůru. Napiš mi, nebo použij hlas. Zatím jde o první Windows prototyp.")
        self._append("Systém", "API klíč je uložen šifrovaně pro tento účet Windows. Změnit ho můžeš tlačítkem 🔑 API klíč.")

    def _build_ui(self):
        top = tk.Frame(self.root, bg="#101612")
        top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(top, text="SPRINGTRAP", font=("Segoe UI", 18, "bold"),
                 fg="#b8e986", bg="#101612").pack(side="left")
        self.character_label = tk.Label(top, text="Postava: Springtrap", font=("Segoe UI", 9),
                                         fg="#d8e4d7", bg="#101612")
        self.character_label.pack(side="right", padx=(8, 12))
        tk.Button(top, text="🔑 API klíč", command=self.change_api_key,
                  bg="#293a2c", fg="white", relief="flat", padx=10, pady=5).pack(side="right", padx=(0, 6))
        tk.Button(top, text="🦾 3D avatar", command=self.open_3d_avatar,
                  bg="#426d3d", fg="white", relief="flat", padx=10, pady=5).pack(side="right", padx=(0, 6))
        tk.Button(top, text="🎮 Knihovna postav", command=self.open_character_library,
                  bg="#293a2c", fg="white", relief="flat", padx=10, pady=5).pack(side="right")
        tk.Checkbutton(top, text="Přečíst odpovědi nahlas", variable=self.speech_enabled,
                       fg="#d8e4d7", bg="#101612", selectcolor="#25352a",
                       activebackground="#101612", activeforeground="#ffffff").pack(side="right", padx=(0, 10))

        self.canvas = tk.Canvas(self.root, height=190, bg="#18221b", highlightthickness=0)
        self.canvas.pack(fill="x", padx=16, pady=8)
        self._draw_avatar()

        self.chat = scrolledtext.ScrolledText(
            self.root, wrap="word", state="disabled", font=("Segoe UI", 10),
            bg="#0d120e", fg="#e6eee5", insertbackground="white",
            relief="flat", padx=10, pady=10
        )
        self.chat.pack(fill="both", expand=True, padx=16, pady=8)
        self.chat.tag_config("name", foreground="#b8e986", font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("system", foreground="#e8c77a", font=("Segoe UI", 9, "italic"))

        controls = tk.Frame(self.root, bg="#101612")
        controls.pack(fill="x", padx=16, pady=(4, 16))
        self.entry = tk.Entry(controls, font=("Segoe UI", 11), bg="#202b22",
                              fg="#ffffff", insertbackground="white", relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.entry.bind("<Return>", lambda _event: self.send_text())
        self.send_button = tk.Button(controls, text="Odeslat", command=self.send_text,
                                     bg="#426d3d", fg="white", relief="flat", padx=14, pady=8)
        self.send_button.pack(side="left", padx=(0, 6))
        tk.Button(controls, text="🎙 Mluvit", command=self.listen,
                  bg="#293a2c", fg="white", relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 6))
        tk.Button(controls, text="📸 Analyzovat obrazovku", command=self.analyze_screen,
                  bg="#293a2c", fg="white", relief="flat", padx=10, pady=8).pack(side="left")

    def open_3d_avatar(self):
        """Open the local interactive Three.js avatar viewer in the default browser."""
        candidates = [
            APP_DIR / "avatar-3d.html",
            Path(getattr(sys, "_MEIPASS", APP_DIR)) / "avatar-3d.html",
        ]
        avatar_file = next((p for p in candidates if p.exists()), None)
        if avatar_file is None:
            messagebox.showerror(
                "3D avatar není nalezen",
                "Soubor avatar-3d.html chybí. Stáhni kompletní složku springtrap z větve springtrap-rewrite."
            )
            return
        webbrowser.open(avatar_file.resolve().as_uri())
        self._append("Systém", "Otevřel jsem 3D laboratoř v prohlížeči. Pro vykreslení je potřeba internetové připojení k načtení Three.js.")

    def _api_key_dialog(self, startup=False):
        """Large first-run/API-key window; the key is encrypted with Windows DPAPI."""
        win = tk.Toplevel(self.root)
        win.title("Nastavení Gemini API klíče")
        win.configure(bg="#101612")
        win.transient(self.root)
        win.state("zoomed")
        result = {"key": None}
        tk.Label(win, text="SPRINGTRAP", font=("Segoe UI", 28, "bold"),
                 fg="#b8e986", bg="#101612").pack(pady=(70, 8))
        tk.Label(win, text="Vlož svůj Google Gemini API klíč",
                 font=("Segoe UI", 19, "bold"), fg="#ffffff",
                 bg="#101612").pack(pady=(10, 8))
        tk.Label(win, text="Klíč se uloží šifrovaně pro tvůj účet Windows. Neukládej ho do GitHubu ani ho nikomu neposílej.",
                 font=("Segoe UI", 11), fg="#a7b7a4", bg="#101612",
                 wraplength=1000).pack(pady=(0, 28))
        entry = tk.Entry(win, font=("Consolas", 22), show="●", relief="flat",
                         bg="#202b22", fg="#ffffff", insertbackground="white")
        entry.pack(fill="x", padx=70, ipady=22)
        entry.focus_set()
        status = tk.Label(win, text="", font=("Segoe UI", 11),
                          fg="#e8c77a", bg="#101612")
        status.pack(pady=12)

        def save_and_close():
            value = entry.get().strip()
            if not value:
                status.configure(text="Vlož API klíč, než budeš pokračovat.")
                return
            try:
                save_key(value)
            except Exception as exc:
                status.configure(text=f"Uložení se nezdařilo: {exc}")
                return
            result["key"] = value
            win.destroy()

        buttons = tk.Frame(win, bg="#101612")
        buttons.pack(pady=22)
        tk.Button(buttons, text="Uložit klíč a spustit Springtrap",
                  command=save_and_close, font=("Segoe UI", 13, "bold"),
                  bg="#426d3d", fg="white", relief="flat",
                  padx=24, pady=14).pack(side="left", padx=8)
        tk.Button(buttons, text="Zrušit", command=win.destroy,
                  font=("Segoe UI", 12), bg="#293a2c", fg="white",
                  relief="flat", padx=24, pady=14).pack(side="left", padx=8)
        tk.Label(win, text="Klíč se při psaní nezobrazuje. Příště se okno už neukáže, dokud klíč nebude potřeba znovu nastavit.",
                 font=("Segoe UI", 10), fg="#7e907b", bg="#101612").pack(pady=(24, 0))
        win.bind("<Return>", lambda _event: save_and_close())
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self.root.wait_window(win)
        return result["key"]

    def change_api_key(self):
        new_key = self._api_key_dialog(startup=False)
        if new_key:
            self.api_key = new_key
            self._append("Systém", "Nový Gemini API klíč byl uložen šifrovaně.")

    def open_character_library(self):
        """Open a searchable-by-franchise starter library; artwork/models are not bundled."""
        games = {
            "Five Nights at Freddy's (všechny díly)": [
                "Springtrap", "Freddy Fazbear", "Bonnie", "Chica", "Foxy",
                "The Puppet", "Circus Baby", "Ennard", "Glamrock Freddy",
                "Roxanne Wolf", "The Mimic"
            ],
            "Apex Legends": [
                "Wraith", "Bangalore", "Bloodhound", "Lifeline", "Pathfinder",
                "Octane", "Mirage", "Revenant", "Valkyrie", "Conduit"
            ],
            "Fortnite": [
                "Jonesy", "Peely", "The Foundation", "Midas", "Meowscles",
                "Fishstick", "Raven", "Hope", "The Ageless", "The Visitor"
            ],
            "VALORANT": [
                "Jett", "Phoenix", "Sage", "Reyna", "Omen", "Sova",
                "Killjoy", "Raze", "Chamber", "Clove"
            ],
            "Half-Life": [
                "Gordon Freeman", "Alyx Vance", "G-Man", "Barney Calhoun",
                "Dr. Kleiner", "Dog", "Combine Soldier", "Vortigaunt"
            ],
            "Overwatch": [
                "Tracer", "D.Va", "Reaper", "Soldier: 76", "Mercy",
                "Genji", "Widowmaker", "Junkrat", "Kiriko", "Ramattra"
            ],
            "Resident Evil": [
                "Leon S. Kennedy", "Jill Valentine", "Claire Redfield",
                "Ada Wong", "Chris Redfield", "Nemesis", "Albert Wesker",
                "Lady Dimitrescu", "Ethan Winters"
            ],
            "Cyberpunk 2077": [
                "V", "Johnny Silverhand", "Judy Alvarez", "Panam Palmer",
                "Jackie Welles", "Songbird", "Adam Smasher"
            ],
            "DOOM": [
                "Doom Slayer", "Samuel Hayden", "VEGA", "The Icon of Sin",
                "Marauder", "Cyberdemon"
            ],
            "Mortal Kombat": [
                "Scorpion", "Sub-Zero", "Liu Kang", "Kitana", "Raiden",
                "Johnny Cage", "Mileena", "Reptile", "Noob Saibot"
            ],
        }
        win = tk.Toplevel(self.root)
        win.title("Herní knihovna postav")
        win.geometry("700x500")
        win.configure(bg="#101612")
        win.transient(self.root)

        tk.Label(win, text="HERNÍ KNIHOVNA", font=("Segoe UI", 16, "bold"),
                 fg="#b8e986", bg="#101612").pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(win, text="10 herních světů • výběr mění osobnost Gemini, ne 3D model",
                 font=("Segoe UI", 9), fg="#a7b7a4", bg="#101612").pack(anchor="w", padx=16, pady=(0, 10))
        body = tk.Frame(win, bg="#101612")
        body.pack(fill="both", expand=True, padx=16, pady=4)
        left = tk.Frame(body, bg="#101612")
        left.pack(side="left", fill="y", padx=(0, 10))
        right = tk.Frame(body, bg="#101612")
        right.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="Hry", fg="#d8e4d7", bg="#101612").pack(anchor="w")
        game_list = tk.Listbox(left, width=31, exportselection=False, bg="#202b22",
                               fg="white", selectbackground="#426d3d", relief="flat")
        game_list.pack(fill="y", expand=True, pady=(4, 0))
        tk.Label(right, text="Postavy", fg="#d8e4d7", bg="#101612").pack(anchor="w")
        char_list = tk.Listbox(right, exportselection=False, bg="#202b22",
                               fg="white", selectbackground="#426d3d", relief="flat")
        char_list.pack(fill="both", expand=True, pady=(4, 8))
        details = tk.Label(right, text="Vyber hru a postavu.", justify="left", anchor="w",
                           wraplength=360, fg="#a7b7a4", bg="#101612")
        details.pack(fill="x", pady=(0, 8))
        for game in games:
            game_list.insert("end", game)

        def update_characters(_event=None):
            selection = game_list.curselection()
            if not selection:
                return
            game = game_list.get(selection[0])
            char_list.delete(0, "end")
            for character in games[game]:
                char_list.insert("end", character)
            details.configure(text=f"{game}\nVyber postavu a stiskni „Použít postavu“.")

        def show_character(_event=None):
            selection = char_list.curselection()
            if selection:
                details.configure(text=f"Vybraná postava: {char_list.get(selection[0])}\n"
                                       "V této verzi se přepne konverzační role. Model, obrázky a "
                                       "speciální animace se doplní samostatně.")

        game_list.bind("<<ListboxSelect>>", update_characters)
        char_list.bind("<<ListboxSelect>>", show_character)
        game_list.selection_set(0)
        update_characters()

        def use_character():
            selection = char_list.curselection()
            if not selection:
                messagebox.showinfo("Vyber postavu", "Nejdřív vyber postavu ze seznamu.", parent=win)
                return
            self.active_character = char_list.get(selection[0])
            self.character_label.configure(text=f"Postava: {self.active_character}")
            self._append("Systém", f"Aktivní postava změněna na: {self.active_character}. "
                                   "Zatím se mění konverzační role, ne vzhled avatara.")
            win.destroy()

        tk.Button(win, text="Použít postavu", command=use_character, bg="#426d3d",
                  fg="white", relief="flat", padx=16, pady=8).pack(anchor="e", padx=16, pady=12)

    def _draw_avatar(self):
        c = self.canvas
        c.delete("all")
        c.create_oval(315, 15, 385, 105, fill="#718c47", outline="#b1c97b", width=3)
        c.create_polygon(325, 45, 300, 0, 335, 18, fill="#647d3e", outline="#b1c97b", width=2)
        c.create_polygon(370, 22, 397, 0, 381, 54, fill="#647d3e", outline="#b1c97b", width=2)
        c.create_oval(326, 47, 345, 67, fill="#e6e8d6", outline="#d0d7ba")
        c.create_oval(355, 47, 374, 67, fill="#e6e8d6", outline="#d0d7ba")
        c.create_oval(334, 52, 341, 64, fill="#a72d28")
        c.create_oval(362, 52, 369, 64, fill="#a72d28")
        c.create_polygon(343, 72, 357, 72, 350, 80, fill="#293128", outline="#b1c97b")
        c.create_arc(334, 76, 366, 98, start=200, extent=140, style="arc", outline="#d2d7bc", width=3)
        c.create_oval(300, 98, 400, 184, fill="#526b37", outline="#b1c97b", width=3)
        c.create_line(318, 119, 338, 130, fill="#2e3e29", width=4)
        c.create_line(382, 116, 364, 133, fill="#2e3e29", width=4)
        c.create_text(18, 18, anchor="nw", text="NEJSEM JEN TAPETA.", fill="#b8e986",
                      font=("Segoe UI", 10, "bold"))
        c.create_text(18, 40, anchor="nw", text="První desktopový prototyp", fill="#a7b7a4",
                      font=("Segoe UI", 9))

    def _append(self, speaker, text):
        self.chat.configure(state="normal")
        tag = "system" if speaker == "Systém" else "name"
        self.chat.insert("end", speaker + ": ", tag)
        self.chat.insert("end", text + "\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _set_busy(self, busy):
        self.busy = busy
        self.send_button.configure(state="disabled" if busy else "normal")
        self.entry.configure(state="disabled" if busy else "normal")

    def send_text(self):
        message = self.entry.get().strip()
        if not message or self.busy:
            return
        self.entry.delete(0, "end")
        self._append("Ty", message)
        self._ask_async(message)

    def _ask_async(self, message, screenshot=None):
        self._set_busy(True)
        self._append("Systém", "Springtrap přemýšlí…")
        threading.Thread(target=self._ask_worker, args=(message, screenshot), daemon=True).start()

    def _ask_worker(self, message, screenshot):
        try:
            brain = GeminiBrain(api_key=self.api_key)
            context = ""
            if self.history:
                context = "Dosavadní konverzace (nejnovější část):\n" + "\n".join(
                    f"{role}: {text}" for role, text in self.history[-12:]
                ) + "\n\n"
            character_instruction = (
                f"\n\nRežim vybrané postavy: vystupuj jako {self.active_character}. "
                "Zachovej její obecně známou atmosféru a osobnost, ale neříkej, že jsi skutečná "
                "postava nebo že ovládáš hru. Odpovídej česky. Pokud jde o postavu z cizí série, "
                "jde o fanouškovské hraní role; nepředstírej, že máš její oficiální hlas nebo model.\n\n"
            )
            reply = brain.ask(character_instruction + context + message, screenshot=screenshot)
            self.history.extend([("Uživatel", message), ("Springtrap", reply)])
            self.events.put(("reply", reply))
        except GeminiBrainError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:
            self.events.put(("error", f"Neočekávaná chyba: {exc}"))

    def _poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "heard":
                    self.entry.configure(state="normal")
                    self.entry.delete(0, "end")
                    self.entry.insert(0, payload)
                    self._append("Rozpoznaná řeč", payload)
                    self.send_text()
                elif kind == "screen":
                    self._append("Ty", "[Povolil jsem analýzu obrazovky]")
                    self._ask_async(
                        "Popiš, co je na snímku obrazovky, a upozorni mě na důležité prvky. Nepředstírej akce.",
                        payload
                    )
                elif kind == "reply":
                    self._set_busy(False)
                    self._append("Springtrap", payload)
                    if self.speech_enabled.get():
                        threading.Thread(target=self._speak, args=(payload,), daemon=True).start()
                elif kind == "error":
                    self._set_busy(False)
                    self._append("Systém", payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _speak(self, text):
        # Prefer a Czech Windows voice and slow the rate slightly for intelligibility.
        # Pass text as Base64 UTF-8 so punctuation cannot break the PowerShell command.
        import base64
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded + "')); "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate=-1; "
            "$v=$s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'cs*' } | Select-Object -First 1; "
            "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
            "$s.Speak($text); $s.Dispose()"
        )
        try:
            result = powershell(script, timeout=120)
            if result.returncode != 0:
                self.events.put(("error", "Český hlas Windows se nepodařilo spustit. Zkontroluj v Nastavení Windows nainstalované hlasové balíčky; dostupné hlasy se liší podle systému."))
        except Exception:
            pass

    def listen(self):
        if self.busy:
            return
        self._append("Systém", "Poslouchám až 10 sekund. Windows může vyžadovat nastavený mikrofon a podporovaný jazyk rozpoznávání.")
        script = r"""
Add-Type -AssemblyName System.Speech
$culture = [Globalization.CultureInfo]::GetCultureInfo('cs-CZ')
try {
  $r = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
  $r.SetInputToDefaultAudioDevice()
  $g = New-Object System.Speech.Recognition.DictationGrammar
  $r.LoadGrammar($g)
  $r.InitialSilenceTimeout = [TimeSpan]::FromSeconds(5)
  $r.BabbleTimeout = [TimeSpan]::FromSeconds(2)
  $r.EndSilenceTimeout = [TimeSpan]::FromSeconds(1)
  $result = $r.Recognize([TimeSpan]::FromSeconds(10))
  if ($result) { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output $result.Text }
} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 2 } finally { if ($r) { $r.Dispose() } }
"""
        def worker():
            try:
                result = powershell(script, timeout=20)
                text = result.stdout.strip()
                if result.returncode != 0:
                    self.events.put(("error", "Windows Speech Recognition se nepodařilo spustit. Zkus napsat zprávu."))
                elif text:
                    self.events.put(("heard", text))
                else:
                    self.events.put(("error", "Nerozuměl jsem nebo nebyla rozpoznána řeč. Zkus to znovu nebo napiš zprávu."))
            except Exception as exc:
                self.events.put(("error", f"Chyba mikrofonu: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def analyze_screen(self):
        if self.busy:
            return
        if not messagebox.askyesno("Povolit snímek obrazovky",
                                  "Springtrap pořídí snímek celé obrazovky a odešle ho do Gemini API k analýze. Pokračovat?"):
            return
        script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
try {
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $p = Join-Path $env:TEMP 'springtrap-screen.png'
  $bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
  Write-Output $p
} finally { $g.Dispose(); $bmp.Dispose() }
"""
        def worker():
            try:
                result = powershell(script, timeout=20)
                path = result.stdout.strip().splitlines()[-1]
                if result.returncode != 0 or not path or not os.path.exists(path):
                    self.events.put(("error", "Nepodařilo se pořídit snímek obrazovky."))
                    return
                data = Path(path).read_bytes()
                os.remove(path)
                self.events.put(("screen", data))
            except Exception as exc:
                self.events.put(("error", f"Snímek obrazovky selhal: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def close(self):
        self.root.destroy()


def main():
    if os.name != "nt":
        raise SystemExit("Tento prototyp je určený pro Windows 10/11.")
    root = tk.Tk()
    app = SpringtrapApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
