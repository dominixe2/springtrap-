# Gemini brain (initial integration step)

This module sends text and an optional screenshot supplied by another part of the app to Google's Gemini API. It uses Python's standard library; no pip packages are required for this first test.

**Status:** this is only the API connection layer. It is not yet a complete Windows app and is not connected to the avatar, microphone, live screen capture, speech playback, persistent memory, or desktop interactions.

## Requirements
- Windows 10/11
- Python 3.10 or newer
- A Gemini API key from https://aistudio.google.com/apikey
- Internet access and available API quota

## Test from Windows PowerShell
Open PowerShell in the `springtrap/brain` folder, then set the key for this PowerShell session only:

```powershell
$env:GEMINI_API_KEY = "YOUR_GEMINI_KEY"
python -c "from gemini_brain import GeminiBrain; print(GeminiBrain().ask('Představ se česky jako Springtrap.'))"
```

The default model is `gemini-3.8-flash`. To override it, set `$env:GEMINI_MODEL` before running the command.

## Security and privacy
- Never commit the API key or paste it into chat.
- The environment variable above applies to the current PowerShell session only.
- Do not send passwords, private messages, or other sensitive screen content to the API.
- Free-tier availability and quotas depend on Google's current terms and account eligibility; usage is not unlimited.
- Screen capture must be implemented separately and should run only with clear user control and permission.

## Next implementation steps
1. Add a Windows app entry point and setup/launch scripts.
2. Connect the avatar window to the Gemini brain.
3. Add Czech speech input and output, with a mute/Do Not Disturb toggle.
4. Add opt-in screenshot capture and controls for when the screen is sent to Gemini.
5. Add mouse-following and idle/reaction animations.
6. Add tests and package the app for Windows.
