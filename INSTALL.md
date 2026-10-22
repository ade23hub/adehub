# Installing GOPILOT

GOPILOT is a Windows desktop app that watches a folder and sorts new files into
Pictures, Videos, Music, Documents, Text, Archives and Unknown.

**Requirements:** Windows 10 or 11 (64-bit). You do not need Python to use the ready-made app.

---

## Option 1 – Use the ready-made app (recommended)

1. Go to the project's **Releases** page on GitHub and download **`GOPILOT-Windows.zip`**.
2. Right-click the zip → **Extract All…** and pick a folder, for example `C:\Users\<you>\GOPILOT`.
   Do not run it from inside the zip.
3. Open the extracted `GOPILOT` folder and double-click **`GOPILOT.exe`**.
   No command prompt window opens.
4. *(Optional)* Right-click `GOPILOT.exe` → **Send to → Desktop (create shortcut)**, or
   **Pin to Start**.

### If Windows shows "Windows protected your PC"
The app is not code-signed, so SmartScreen may warn you the first time.
Click **More info → Run anyway**.

### Where GOPILOT keeps its data
`%APPDATA%\GOPILOT` (usually `C:\Users\<you>\AppData\Roaming\GOPILOT`) holds the settings,
the activity log database and the Test-mode folder. Nothing is written to the install folder.

### Uninstall
Close GOPILOT (tray icon → **Stop monitoring and exit**), delete the `GOPILOT` folder,
and optionally delete `%APPDATA%\GOPILOT` to remove your settings and history.

---

## Option 2 – Run from source (for developers)

You need **Python 3.10 or newer** and **Git**.

```bat
git clone https://github.com/ade23hub/GOPILOT.git
cd GOPILOT
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app\splash.py
```

### Build the Windows app yourself
```bat
pip install pyinstaller pillow
python build_exe.py
```
This creates `dist\GOPILOT\GOPILOT.exe` and a shareable `dist\GOPILOT-Windows.zip`.

---

## First-time use

1. Open GOPILOT. It starts in **Test mode**, which only touches a safe sandbox folder.
2. Click **Start Monitoring** and drop a file into the watched folder to see it sorted.
3. When you are happy, open **Settings** to choose your watched folder and destinations.
   You can also switch to **Production mode** to organize your real Windows folders
   (GOPILOT asks you to confirm first).
4. Turn on **Preview each file and wait for my approval** if you want to approve every move.
5. Closing the window while monitoring keeps GOPILOT running in the system tray.
   To quit, use the tray menu → **Stop monitoring and exit**.

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing happens when I double-click | Re-extract the whole zip; the `_internal` folder must stay next to `GOPILOT.exe`. Check your antivirus did not quarantine it. |
| "Monitoring Active" when saving settings | Stop monitoring first, then save. |
| App seems missing after closing the window | It is in the system tray (bottom-right, maybe under the `^` arrow). |
| Moved the wrong file | Open **Logs**, select the row and click **Undo Selected Move**. |
