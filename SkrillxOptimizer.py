import ctypes
import os
import platform
import re
import subprocess
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

import psutil

# ---------- Apni social links yahan daalein ----------
SOCIAL = {
    "YOUTUBE": "https://youtube.com/",
    "TIKTOK": "https://tiktok.com/",
    "INSTAGRAM": "https://instagram.com/",
    "WHATSAPP": "https://wa.me/",
}

BG, SIDE, CARD = "#0b0e17", "#111525", "#161b2e"
ACCENT, ACCENT2 = "#00c8ff", "#7c3aed"
TEXT, MUTED, GOOD, WARN = "#e5e7eb", "#8b93a7", "#22c55e", "#f59e0b"

GAME_PROCS = ["aow_exe.exe", "androidemulatorex.exe", "androidemulatoren.exe", "androidemulator.exe"]
PROTECTED = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
             "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe",
             "fontdrvhost.exe", "python.exe", "pythonw.exe", "skrillxoptimizer.exe"}
NO_WINDOW = 0x08000000


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def out(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           creationflags=NO_WINDOW, timeout=60)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def ps(cmd):
    return out(f'powershell -NoProfile -Command "{cmd}"')


def reg(path, name, kind, value):
    out(f'reg add "{path}" /v {name} /t {kind} /d {value} /f')


# ---------- Gamma / colour ----------
def set_gamma(brightness=0.0, contrast=1.0, gamma=1.0, r=1.0, g=1.0, b=1.0):
    ramp = (ctypes.c_ushort * 256 * 3)()
    for i in range(256):
        v = (i / 255 - 0.5) * contrast + 0.5 + brightness
        v = min(max(v, 0.0), 1.0) ** (1.0 / gamma)
        for ch, m in enumerate((r, g, b)):
            ramp[ch][i] = int(min(max(v * m, 0.0), 1.0) * 65535)
    hdc = ctypes.windll.user32.GetDC(0)
    ok = ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
    ctypes.windll.user32.ReleaseDC(0, hdc)
    return bool(ok)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SkrillxOptimizer v2")
        self.geometry("980x640")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.auto_boost = tk.BooleanVar(value=False)
        self.done = set()
        self.total_tasks = 8
        self.pages = {}
        self.build_ui()
        self.show("Dashboard")
        self.load_sysinfo()
        self.tick()
        self.auto_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if not is_admin():
            self.log("Admin mode OFF. Right-click > Run as administrator.")

    # ---------- layout ----------
    def build_ui(self):
        side = tk.Frame(self, bg=SIDE, width=200, height=640)
        side.place(x=0, y=0)
        tk.Label(side, text="SKRILLX", font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=SIDE).place(x=20, y=16)
        tk.Label(side, text="OPTIMIZER v2", font=("Segoe UI", 9), fg=MUTED, bg=SIDE).place(x=22, y=52)
        self.navbtns = {}
        for i, name in enumerate(["Dashboard", "Optimization", "Windows Tweaks", "Network",
                                  "Display & Colors", "Game Boost"]):
            b = tk.Button(side, text=name, anchor="w", padx=16, relief="flat", bg=SIDE, fg=TEXT,
                          activebackground=CARD, activeforeground=ACCENT, font=("Segoe UI", 10, "bold"),
                          cursor="hand2", command=lambda n=name: self.show(n))
            b.place(x=10, y=90 + i * 46, width=180, height=38)
            self.navbtns[name] = b

        self.content = tk.Frame(self, bg=BG, width=780, height=430)
        self.content.place(x=200, y=0)
        for name, fn in [("Dashboard", self.page_dashboard), ("Optimization", self.page_opt),
                         ("Windows Tweaks", self.page_win), ("Network", self.page_net),
                         ("Display & Colors", self.page_display), ("Game Boost", self.page_boost)]:
            f = tk.Frame(self.content, bg=BG, width=780, height=430)
            self.pages[name] = f
            fn(f)

        self.logbox = tk.Text(self, height=9, width=96, bg=CARD, fg=GOOD, relief="flat",
                              font=("Consolas", 9), state="disabled")
        self.logbox.place(x=215, y=440)

    def show(self, name):
        for p in self.pages.values():
            p.place_forget()
        self.pages[name].place(x=0, y=0)
        for n, b in self.navbtns.items():
            b.config(bg=CARD if n == name else SIDE, fg=ACCENT if n == name else TEXT)

    def title_lbl(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 16, "bold"), fg=ACCENT, bg=BG).place(x=20, y=14)

    def btn(self, parent, text, cmd, x, y, w=22, color=ACCENT2, threaded=True):
        c = (lambda: threading.Thread(target=cmd, daemon=True).start()) if threaded else cmd
        b = tk.Button(parent, text=text, command=c, bg=color, fg="white", activebackground=ACCENT,
                      activeforeground="black", relief="flat", font=("Segoe UI", 9, "bold"),
                      width=w, height=2, cursor="hand2")
        b.place(x=x, y=y)
        return b

    def card(self, parent, x, y, w, h):
        f = tk.Frame(parent, bg=CARD, width=w, height=h)
        f.place(x=x, y=y)
        f.pack_propagate(False)
        return f

    def log(self, msg):
        def _w():
            self.logbox.config(state="normal")
            self.logbox.insert("end", "> " + msg + "\n")
            self.logbox.see("end")
            self.logbox.config(state="disabled")
        self.after(0, _w)

    def mark(self, key):
        self.done.add(key)
        self.after(0, self.draw_gauge)

    # ---------- Dashboard ----------
    def page_dashboard(self, p):
        self.title_lbl(p, "DASHBOARD")
        self.info = {}
        spots = [("SYSTEM", 20, 56), ("PROCESSOR", 220, 56), ("MEMORY", 20, 130), ("GRAPHICS", 220, 130)]
        for name, x, y in spots:
            c = self.card(p, x, y, 190, 66)
            tk.Label(c, text=name, font=("Segoe UI", 8, "bold"), fg=ACCENT, bg=CARD).pack(anchor="w", padx=8, pady=(6, 0))
            l = tk.Label(c, text="...", font=("Segoe UI", 8), fg=TEXT, bg=CARD, justify="left", wraplength=175)
            l.pack(anchor="w", padx=8)
            self.info[name] = l

        c = self.card(p, 430, 56, 330, 140)
        tk.Label(c, text="SYSTEM BOOST", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=CARD).pack(anchor="w", padx=10, pady=6)
        self.gauge = tk.Canvas(c, width=300, height=100, bg=CARD, highlightthickness=0)
        self.gauge.pack()
        self.draw_gauge()

        self.bars = {}
        for i, n in enumerate(["CPU", "RAM", "DISK"]):
            c = self.card(p, 20 + i * 245, 210, 235, 56)
            l = tk.Label(c, text=n, font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD)
            l.pack(anchor="w", padx=10, pady=(6, 2))
            bar = ttk.Progressbar(c, length=215, maximum=100)
            bar.pack(padx=10)
            self.bars[n] = (bar, l)

        tk.Label(p, text="FOLLOW US", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG).place(x=20, y=282)
        for i, (n, url) in enumerate(SOCIAL.items()):
            self.btn(p, n, lambda u=url: webbrowser.open(u), 20 + i * 150, 304, w=16, color=CARD, threaded=False)

        self.btn(p, "ONE-CLICK: APPLY RECOMMENDED", self.one_click, 20, 360, w=34, color=ACCENT2)
        tk.Label(p, text="Safe tweaks only. Game ko hack/inject nahi karta.", font=("Segoe UI", 8),
                 fg=MUTED, bg=BG).place(x=300, y=374)

    def draw_gauge(self):
        g = self.gauge
        g.delete("all")
        pct = int(len(self.done) / self.total_tasks * 100)
        g.create_arc(80, 10, 220, 150, start=0, extent=180, style="arc", width=12, outline="#26304a")
        g.create_arc(80, 10, 220, 150, start=180, extent=-180 * pct / 100, style="arc", width=12,
                     outline=GOOD if pct >= 60 else WARN)
        g.create_text(150, 78, text=f"{pct}%", fill=TEXT, font=("Segoe UI", 16, "bold"))
        g.create_text(150, 98, text="optimized" if pct else "NOT OPTIMIZED", fill=MUTED, font=("Segoe UI", 8))

    def load_sysinfo(self):
        def work():
            cpu = ps("(Get-CimInstance Win32_Processor | Select -First 1).Name") or platform.processor()
            gpu = ps("(Get-CimInstance Win32_VideoController | Select -First 1).Name") or "Unknown"
            sysd = f"{platform.system()} {platform.release()}\nbuild {platform.version().split('.')[-1]} | " + \
                   ("admin" if is_admin() else "user")
            threads = psutil.cpu_count(logical=True)
            mem = psutil.virtual_memory()
            self.after(0, lambda: (
                self.info["SYSTEM"].config(text=sysd),
                self.info["PROCESSOR"].config(text=f"{cpu}\n{threads} threads"),
                self.info["MEMORY"].config(text=f"{mem.used/2**30:.1f} / {mem.total/2**30:.1f} GB ({mem.percent:.0f}%)"),
                self.info["GRAPHICS"].config(text=gpu)))
        threading.Thread(target=work, daemon=True).start()

    def tick(self):
        vals = {"CPU": psutil.cpu_percent(), "RAM": psutil.virtual_memory().percent,
                "DISK": psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\").percent}
        for n, (bar, lbl) in self.bars.items():
            bar["value"] = vals[n]
            lbl.config(text=f"{n}  {vals[n]:.0f}%")
        self.after(1500, self.tick)

    def one_click(self):
        self.log("One-click: recommended settings laga raha hoon...")
        self.pc_optimize()
        self.power_plan()
        self.game_mode()
        self.win_tweaks()
        self.flush_dns()
        self.boost()
        self.log("One-click complete.")

    # ---------- Optimization ----------
    def page_opt(self, p):
        self.title_lbl(p, "OPTIMIZATION")
        self.btn(p, "PC OPTIMIZE (RAM + Junk)", self.pc_optimize, 20, 60)
        self.btn(p, "Clean RAM", self.clean_ram, 270, 60)
        self.btn(p, "Clean Junk Files", self.clean_junk, 520, 60)
        self.btn(p, "Max Power Plan", self.power_plan, 20, 120)
        self.btn(p, "Game Mode ON", self.game_mode, 270, 120)
        self.btn(p, "LAG TEST", self.lag_test, 520, 120)

        tk.Label(p, text="ONE-CLICK PROFILE", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG).place(x=20, y=190)
        self.btn(p, "Low-End PC", lambda: self.profile("low"), 20, 214, w=20)
        self.btn(p, "Balanced", lambda: self.profile("mid"), 220, 214, w=20)
        self.btn(p, "Maximum FPS", lambda: self.profile("max"), 420, 214, w=20)

        tk.Label(p, text="GAME ENGINE (GameLoop Settings mein khud select karein):\n"
                         "- DirectX+ : zyada tar NVIDIA/AMD cards par best\n"
                         "- OpenGL+  : purane PC / Intel graphics par stable\n"
                         "- Smart    : auto chunta hai (pehle yehi try karein)\n"
                         "Tip: RAM 4GB, CPU 4 cores, FPS 60/90 se shuru karein.",
                 justify="left", font=("Segoe UI", 9), fg=MUTED, bg=BG).place(x=20, y=290)

    def pc_optimize(self):
        self.clean_ram()
        self.clean_junk()
        self.mark("pc")

    def clean_ram(self):
        before = psutil.virtual_memory().available
        for p in psutil.process_iter(["pid", "name"]):
            if (p.info["name"] or "").lower() in GAME_PROCS:
                continue
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, p.info["pid"])
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
            except Exception:
                pass
        freed = (psutil.virtual_memory().available - before) / 2**20
        self.log(f"RAM clean: approx {max(freed, 0):.0f} MB free.")
        self.mark("ram")

    def clean_junk(self):
        total = 0
        for folder in (os.environ.get("TEMP"), r"C:\Windows\Temp", r"C:\Windows\Prefetch"):
            if not folder or not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        s = os.path.getsize(fp)
                        os.remove(fp)
                        total += s
                    except Exception:
                        pass
        self.log(f"Junk clean: {total / 2**20:.0f} MB saaf.")
        self.mark("junk")

    def power_plan(self):
        out("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
        self.log("High Performance power plan ON.")
        self.mark("power")

    def game_mode(self):
        reg(r"HKCU\Software\Microsoft\GameBar", "AutoGameModeEnabled", "REG_DWORD", 1)
        reg(r"HKCU\Software\Microsoft\GameBar", "AllowAutoGameMode", "REG_DWORD", 1)
        self.log("Windows Game Mode ON.")
        self.mark("gamemode")

    def lag_test(self):
        self.log("Lag test (8.8.8.8) chal raha hai, 10 sec...")
        r = out("ping -n 10 8.8.8.8")
        times = [int(x) for x in re.findall(r"time[=<](\d+)ms", r)]
        lost = 10 - len(times)
        if times:
            avg = sum(times) / len(times)
            jit = max(times) - min(times)
            verdict = "Excellent" if avg < 40 else "Good" if avg < 80 else "Laggy"
            self.log(f"Ping avg {avg:.0f}ms | jitter {jit}ms | loss {lost}/10 -> {verdict}")
        else:
            self.log("Lag test fail. Internet check karein.")

    def profile(self, kind):
        self.log(f"Profile: {kind}")
        self.power_plan()
        self.game_mode()
        if kind in ("mid", "max"):
            self.clean_junk()
            self.clean_ram()
        if kind in ("low", "max"):
            self.win_tweaks()
        if kind == "max":
            self.boost()
            self.flush_dns()
        self.log("Profile applied.")

    # ---------- Windows tweaks ----------
    def page_win(self, p):
        self.title_lbl(p, "WINDOWS TWEAKS")
        self.btn(p, "Apply All Tweaks", self.win_tweaks, 20, 60, color=ACCENT2)
        self.btn(p, "Undo (Defaults)", self.win_undo, 270, 60, color=CARD)
        tk.Label(p, text="Ye tweaks lagte hain:\n\n"
                         "- Game DVR / background recording OFF\n"
                         "- Transparency effects OFF\n"
                         "- Visual Effects = Best Performance\n"
                         "- Mouse acceleration OFF (aim ke liye behtar)\n"
                         "- Background apps OFF\n"
                         "- Hibernation OFF (disk space bhi bachta hai)\n\n"
                         "Kuch tweaks sign-out / restart ke baad poori tarah lagte hain.",
                 justify="left", font=("Segoe UI", 10), fg=MUTED, bg=BG).place(x=20, y=130)

    def win_tweaks(self):
        reg(r"HKCU\System\GameConfigStore", "GameDVR_Enabled", "REG_DWORD", 0)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", 0)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", "REG_DWORD", 0)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", "REG_DWORD", 2)
        reg(r"HKCU\Control Panel\Mouse", "MouseSpeed", "REG_SZ", 0)
        reg(r"HKCU\Control Panel\Mouse", "MouseThreshold1", "REG_SZ", 0)
        reg(r"HKCU\Control Panel\Mouse", "MouseThreshold2", "REG_SZ", 0)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", "REG_DWORD", 1)
        out("powercfg /hibernate off")
        self.log("Windows tweaks apply ho gaye.")
        self.mark("win")

    def win_undo(self):
        reg(r"HKCU\System\GameConfigStore", "GameDVR_Enabled", "REG_DWORD", 1)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", 1)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", "REG_DWORD", 1)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", "REG_DWORD", 0)
        reg(r"HKCU\Control Panel\Mouse", "MouseSpeed", "REG_SZ", 1)
        reg(r"HKCU\Control Panel\Mouse", "MouseThreshold1", "REG_SZ", 6)
        reg(r"HKCU\Control Panel\Mouse", "MouseThreshold2", "REG_SZ", 10)
        reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", "REG_DWORD", 0)
        out("powercfg /hibernate on")
        self.done.discard("win")
        self.after(0, self.draw_gauge)
        self.log("Windows tweaks wapas default.")

    # ---------- Network ----------
    def page_net(self, p):
        self.title_lbl(p, "NETWORK")
        self.btn(p, "Flush DNS", self.flush_dns, 20, 60)
        self.btn(p, "DNS -> Google (8.8.8.8)", lambda: self.set_dns("8.8.8.8,8.8.4.4"), 270, 60)
        self.btn(p, "DNS -> Cloudflare (1.1.1.1)", lambda: self.set_dns("1.1.1.1,1.0.0.1"), 520, 60)
        self.btn(p, "DNS -> Automatic", lambda: self.set_dns(None), 20, 120, color=CARD)
        self.btn(p, "Reset Winsock (restart chahiye)", self.reset_winsock, 270, 120, color=CARD)
        self.btn(p, "LAG TEST", self.lag_test, 520, 120)
        tk.Label(p, text="Tip: game ke waqt WiFi ki jagah LAN cable use karein, aur download/streaming band rakhein.",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG, wraplength=700, justify="left").place(x=20, y=200)

    def flush_dns(self):
        out("ipconfig /flushdns")
        self.log("DNS flush done.")
        self.mark("dns")

    def set_dns(self, servers):
        if servers:
            cmd = ("Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object "
                   f"{{Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses {servers}}}")
        else:
            cmd = ("Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object "
                   "{Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses}")
        ps(cmd)
        self.log(f"DNS set: {servers or 'Automatic'}")

    def reset_winsock(self):
        out("netsh winsock reset")
        self.log("Winsock reset. PC restart karein.")

    # ---------- Display & Colors ----------
    def page_display(self, p):
        self.title_lbl(p, "DISPLAY & COLORS")
        self.sliders = {}
        spec = [("Brightness", -0.2, 0.2, 0.0), ("Contrast", 0.7, 1.3, 1.0), ("Gamma", 0.6, 1.8, 1.0),
                ("Red", 0.7, 1.0, 1.0), ("Green", 0.7, 1.0, 1.0), ("Blue", 0.7, 1.0, 1.0)]
        for i, (n, lo, hi, d) in enumerate(spec):
            x, y = 20 + (i % 2) * 380, 60 + (i // 2) * 56
            tk.Label(p, text=n, fg=TEXT, bg=BG, font=("Segoe UI", 9, "bold")).place(x=x, y=y)
            s = tk.Scale(p, from_=lo, to=hi, resolution=0.01, orient="horizontal", length=320,
                         bg=BG, fg=TEXT, troughcolor=CARD, highlightthickness=0, command=lambda _v: self.apply_colors())
            s.set(d)
            s.place(x=x, y=y + 16)
            self.sliders[n] = (s, d)

        tk.Label(p, text="PRESETS", font=("Segoe UI", 9, "bold"), fg=ACCENT, bg=BG).place(x=20, y=240)
        presets = {
            "Default": dict(Brightness=0, Contrast=1, Gamma=1, Red=1, Green=1, Blue=1),
            "Vivid (PUBG)": dict(Brightness=0.02, Contrast=1.12, Gamma=1.15, Red=1, Green=1, Blue=1),
            "Bright Shadows": dict(Brightness=0.05, Contrast=1.0, Gamma=1.4, Red=1, Green=1, Blue=1),
            "Night / Warm": dict(Brightness=-0.03, Contrast=1.0, Gamma=1.0, Red=1, Green=0.88, Blue=0.7),
        }
        for i, (n, v) in enumerate(presets.items()):
            self.btn(p, n, lambda v=v: self.load_preset(v), 20 + i * 185, 264, w=16, color=ACCENT2, threaded=False)
        self.btn(p, "RESET COLORS", lambda: self.load_preset(presets["Default"]), 20, 320, w=22, color=CARD, threaded=False)
        tk.Label(p, text="Ye Windows ki screen gamma use karta hai. Agar kuch ajeeb lage to RESET dabayein.\n"
                         "Bohot zyada values Windows reject kar sakta hai.",
                 fg=MUTED, bg=BG, font=("Segoe UI", 9), justify="left").place(x=270, y=326)

    def apply_colors(self):
        s = {n: v[0].get() for n, v in self.sliders.items()}
        set_gamma(s["Brightness"], s["Contrast"], s["Gamma"], s["Red"], s["Green"], s["Blue"])

    def load_preset(self, vals):
        for n, v in vals.items():
            self.sliders[n][0].set(v)
        self.apply_colors()
        self.log("Colour preset apply hui.")

    # ---------- Game Boost ----------
    def page_boost(self, p):
        self.title_lbl(p, "GAME BOOST")
        self.btn(p, "BOOST GAMELOOP NOW", self.boost, 20, 56)
        tk.Checkbutton(p, text="Auto Boost (GameLoop khulte hi High priority)", variable=self.auto_boost,
                       fg=TEXT, bg=BG, selectcolor=CARD, activebackground=BG, activeforeground=TEXT,
                       font=("Segoe UI", 10)).place(x=270, y=66)
        tk.Label(p, text="Sab se zyada RAM lene wale apps (End Task se band karein):",
                 fg=ACCENT, bg=BG, font=("Segoe UI", 9, "bold")).place(x=20, y=118)
        self.lst = tk.Listbox(p, width=80, height=10, bg=CARD, fg=TEXT, relief="flat",
                              selectbackground=ACCENT2, font=("Consolas", 9))
        self.lst.place(x=20, y=142)
        self.btn(p, "Refresh List", self.refresh_procs, 20, 340, w=18, color=CARD, threaded=False)
        self.btn(p, "End Selected Task", self.kill_selected, 230, 340, w=20, color="#b91c1c", threaded=False)
        self.refresh_procs()

    def refresh_procs(self):
        self.proc_rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                self.proc_rows.append((p.info["memory_info"].rss, p.info["pid"], p.info["name"] or "?"))
            except Exception:
                pass
        self.proc_rows = sorted(self.proc_rows, reverse=True)[:25]
        self.lst.delete(0, "end")
        for rss, pid, name in self.proc_rows:
            self.lst.insert("end", f"{name:<32} {rss/2**20:>8.0f} MB   (pid {pid})")

    def kill_selected(self):
        sel = self.lst.curselection()
        if not sel:
            return
        rss, pid, name = self.proc_rows[sel[0]]
        if name.lower() in PROTECTED or name.lower() in GAME_PROCS:
            messagebox.showinfo("Protected", f"{name} ko band nahi kiya ja sakta (system/game).")
            return
        if messagebox.askyesno("End Task", f"{name} band karein? Unsaved kaam chala jayega."):
            try:
                psutil.Process(pid).terminate()
                self.log(f"{name} band kiya.")
            except Exception as e:
                self.log(f"Band nahi hua: {e}")
            self.refresh_procs()

    def boost(self):
        n = 0
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info["name"] or "").lower() in GAME_PROCS:
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
                    n += 1
            except Exception:
                pass
        self.log(f"{n} GameLoop process High priority." if n else "GameLoop chal nahi raha. Pehle kholein.")
        if n:
            self.mark("boost")

    def auto_loop(self):
        if self.auto_boost.get():
            for p in psutil.process_iter(["name"]):
                try:
                    if (p.info["name"] or "").lower() in GAME_PROCS and p.nice() != psutil.HIGH_PRIORITY_CLASS:
                        p.nice(psutil.HIGH_PRIORITY_CLASS)
                except Exception:
                    pass
        self.after(8000, self.auto_loop)

    def on_close(self):
        try:
            set_gamma()  # colours reset
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
