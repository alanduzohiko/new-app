# مەشخەڵ — Android app source

This repository is the new, independent home for the Meshkhal Android app. It is separate from the previous `masheqal` repository.

## Build from the supplied source archive

The project source archive is too large to store as ordinary Git files. Create a GitHub Release with tag `v1.0.0-source`, and attach the file `Meshkhal-ui-trilingual-source-ready.zip` as a release asset. Publishing that source release triggers the Android build workflow. The workflow downloads the source archive, validates the bundled Quran/content databases, runs Gradle tests and lint, then builds a debug APK.

After the workflow completes, open **Actions → مەشخەڵ Android Build → Artifacts** and download `meshkhal-android-build-...` to retrieve the APK and reports.

**Important:** a successful build does not prove every app feature works on a physical phone. See `docs/implementation-status.md` inside the source archive for the known implementation and testing gaps.
