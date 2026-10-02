# Distributing ReadMask

Local `./build.sh` output is for testing. It uses an ad hoc signature and is not a public release artifact.

Build on macOS with a Python, PyObjC, and PyInstaller environment matching the intended architecture. On Apple Silicon, check that `python3` and `pyinstaller` are arm64; an x86_64 Python running under Rosetta produces an x86_64 app. Set `READMASK_PYINSTALLER` to a specific PyInstaller executable when needed. `READMASK_TARGET_ARCH=universal2` is supported only when Python and all bundled native dependencies contain both architectures. The release script checks the finished executable before signing.

To create a distributable ZIP, first configure a Developer ID Application certificate and a `notarytool` keychain profile outside the repository. Then run:

```sh
export READMASK_SIGN_IDENTITY="Developer ID Application: ..."
export READMASK_NOTARY_PROFILE="readmask-notary"
./scripts/package-release.sh
```

The script builds the app, checks its architecture, signs with the hardened runtime, submits it for notarization, staples the ticket, checks Gatekeeper, and creates `dist/ReadMask-macos-<arch>.zip`. It does not upload or publish a release. To build a non-native architecture intentionally, set `READMASK_RELEASE_ARCH` to `arm64`, `x86_64`, or `universal2` as appropriate.
