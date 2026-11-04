# Micro Helper Android APK

This folder builds a debug-installable Android wrapper around the hosted Micro Helper PWA.

## Build
1. Open GitHub Actions in this repository.
2. Run **Build Micro Helper Android APK** on branch `micro-helper`, or push a change under this folder.
3. Download the artifact `micro-helper-android-debug-apk` from the completed workflow run.
4. Extract and install `app-debug.apk` on Android. Android may ask to allow installation from the browser/file manager.

The APK is a debug-signed WebView wrapper that loads the hosted app. It is not a Play Store release and does not bundle the backend or cloud AI. Internet access is required for cloud AI and account sync. Chrome can also install the PWA directly without an APK build.

The workflow adds Android microphone permission. Speech recognition still requires the app to be open and may depend on Android/Chrome speech services.
