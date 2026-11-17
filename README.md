# QuadStick Manager Program (QMP)

Desktop app for setting up a [QuadStick](https://www.quadstick.com), a mouth-operated game controller. Runs on Windows and macOS.

## What it does

- **Preferences:** joystick, sip/puff, lip, mouse and Bluetooth settings, saved to the QuadStick.
- **Game files:** copy factory profiles or your own Google Sheets profiles onto the QuadStick, and remove them.
- **Firmware:** download and install firmware updates.
- **External pointers:** feed an UltraStik 360 joystick or the mouse into the QuadStick.
- **Windows only:** virtual Xbox 360 / DualShock 4 controller (ViGEmBus), HidHide, and voice control (Vocola).

## macOS

Needs Python 3.12 and `make`. From the `QuadStick Manager Program` folder:

| Command | What it does |
|---|---|
| `make install` | Create `.venv` and install `requirements-macos.txt` |
| `make run` | Run QMP from source (`make run debug=1` for debug output) |
| `make build` | Build `dist/QuadStick.app` |
| `make test` | Run the HID self-check |
| `make help` | List all targets |

What differs from Windows:

- The Windows-only features above are disabled. The Voice Control tab stays as the transcript for typed commands.
- Settings live in `~/Library/Application Support/QMP_3_settings.repr`.
- Reading the firmware build number needs an administrator password. QMP asks once per firmware version and remembers the answer.
- The built app is not signed with a Developer ID or notarized.

## Windows

Needs Python 3.10. From the `QuadStick Manager Program` folder:

```bat
pip install -r requirements.txt
python QuadStick.py
build.bat
```

`build.bat` builds `dist\QuadStick.exe` with PyInstaller. The wxPython line in `requirements.txt` points to a wheel file on the original author's machine; remove that line and install wxPython yourself.

## License

MIT, see [LICENSE](LICENSE).
