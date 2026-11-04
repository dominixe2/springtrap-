# Micro Helper Android APK

This folder builds a debug-installable Android wrapper around the hosted Micro Helper PWA.

## Build and install

1. Open [GitHub Actions](https://github.com/dominixe2/springtrap-/actions/workflows/android-apk.yml?query=branch%3Amicro-helper).
2. Download the artifact `micro-helper-android-debug-apk` from the latest successful run.
3. Extract the ZIP archive. It contains `app-debug.apk` and `app-debug.apk.sha256`.
4. Optional integrity check: from a shell with `sha256sum`, run `sha256sum -c app-debug.apk.sha256` in the extracted directory.
5. Install `app-debug.apk` on Android. If prompted, allow installation from the browser or file manager used to open the APK.

The APK is a debug-signed WebView wrapper that loads the hosted app. It is not a Play Store release and does not bundle the backend or cloud AI. Internet access is required for cloud AI and account sync. Chrome can also install the PWA directly without an APK build.

The workflow adds Android microphone permission. Speech recognition still requires the app to be open and may depend on Android/Chrome speech services. The APK is unsigned by a production release key and should be treated as a test/beta build.
