# Build EXE Executable

This guide explains how to convert the PyQt5 GUI application into a standalone `.exe` file.

## Prerequisites

You need to have:
- Python 3.8+ installed
- All dependencies from `requirements-gui.txt`

## Step 1: Install PyInstaller

```bash
pip install PyInstaller
```

## Step 2: Build the EXE

### Option A: Simple Build (Folder Output)

```bash
pyinstaller --onedir --windowed --name "2K_Vision_Hub" gui_app.py
```

**Output:** `dist/2K_Vision_Hub/2K_Vision_Hub.exe`

### Option B: Single File EXE (Recommended)

```bash
pyinstaller --onefile --windowed --name "2K_Vision_Hub" --icon=icon.ico gui_app.py
```

**Output:** `dist/2K_Vision_Hub.exe` (single executable file)

### Option C: Advanced Build (with hidden imports)

```bash
pyinstaller --onefile --windowed ^
  --name "2K_Vision_Hub" ^
  --hidden-import=cv2 ^
  --hidden-import=PyQt5 ^
  --hidden-import=pyds4 ^
  --hidden-import=numpy ^
  gui_app.py
```

## Step 3: Run the EXE

Navigate to the `dist` folder and double-click `2K_Vision_Hub.exe`

Or run from command line:
```bash
./dist/2K_Vision_Hub.exe
```

## Troubleshooting

### "Cannot find module cv2"
```bash
pyinstaller --onefile --windowed --name "2K_Vision_Hub" \
  --collect-all opencv-python \
  --collect-all PyQt5 \
  gui_app.py
```

### "Missing DLL files"
The `dist` folder contains all required files. Keep them together.

### Large EXE file (300+ MB)
This is normal due to OpenCV and PyQt5 libraries. Use `--onedir` instead of `--onefile` to reduce size.

## Create a Shortcut

1. Right-click `2K_Vision_Hub.exe`
2. Select "Create Shortcut"
3. Move shortcut to Desktop for easy access

## Building on Different Platforms

**Windows:**
```bash
pyinstaller --onefile --windowed --name "2K_Vision_Hub" gui_app.py
```

**Mac:**
```bash
pyinstaller --onefile --windowed --osx-bundle-identifier com.2kvision.hub gui_app.py
```

**Linux:**
```bash
pyinstaller --onefile --windowed --name "2K_Vision_Hub" gui_app.py
```

## Advanced: Add Custom Icon

1. Find or create a `.ico` file (or convert PNG to ICO using online tools)
2. Place in project root as `icon.ico`
3. Build with:

```bash
pyinstaller --onefile --windowed --icon=icon.ico gui_app.py
```

## File Size Optimization

To reduce the EXE size:

```bash
pyinstaller --onefile --windowed -y --optimize=2 gui_app.py
```

## Batch Build Script

Create `build.bat` (Windows):

```batch
@echo off
echo Building 2K Vision Hub...
pyinstaller --onefile --windowed ^
  --name "2K_Vision_Hub" ^
  --icon=icon.ico ^
  --collect-all opencv-python ^
  --collect-all PyQt5 ^
  gui_app.py

echo.
echo Build complete! EXE located at: dist\2K_Vision_Hub.exe
pause
```

Run with: `build.bat`

## Distribution

To share the EXE with others:

1. Navigate to `dist` folder
2. Right-click `2K_Vision_Hub.exe` folder → Send to → Compressed (zipped) folder
3. Share the `.zip` file
4. Users can extract and run the `.exe` directly (no Python installation required)

---

For more info: https://pyinstaller.org/
