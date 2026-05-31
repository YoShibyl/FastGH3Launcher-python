# FastGH3 Launcher
A Python port of my [FastGH3 Chart Browser](https://github.com/YoShibyl/FGH3ChartBrowser), primarily for use on Linux.  Uses tkinter and ttkbootstrap for the interface.

Note: I've only tested this on Linux so far, so if there are any issues on Windows, let me know.

<details>
  <summary>Screenshot (v1.0.0 Dark Mode)</summary>
  <img width="1151" height="712" alt="image" src="https://github.com/user-attachments/assets/8697765a-fc57-429f-b307-52222e2e461f" />

</details>

## Prerequisites
- Linux or Windows (tested on SteamOS)
- [FastGH3](https://github.com/donnaken15/FastGH3)
- If on Linux, you'll need either [Wine](https://www.winehq.org/) or (preferably) [umu launcher](https://github.com/Open-Wine-Components/umu-launcher)

## Setup
1) Download the latest **`.zip`** of [FastGH3](https://github.com/donnaken15/FastGH3/releases) and extract the contents wherever you'd like.  Make note of where you extract it to, as you'll need to select the `FastGH3.exe` file in the launcher settings!
2) Download the latest release of the launcher from [Releases](https://github.com/YoShibyl/FastGH3Launcher-python/releases) into its own folder.
3) You might need to manually allow the binary to be executed as a program if you're running the Linux binary.  You can either run `chmod +x ./fastgh3launcher`, or on many distros, right-click, open the file's properties, then somewhere there should be an option to allow it to be executed as a program.
4) Upon first launch, you'll want to point the launcher to the location of where you extracted `FastGH3.exe`.  Click **Other Settings**, then **Choose File**, and browse to where FastGH3 is installed and select it.
5) *(Recommended for Linux users)* Download [umu launcher](https://github.com/Open-Wine-Components/umu-launcher), and you can configure the launch command to use `umu-run` instead of `wine`.  For example: `umu-run "$fastgh3path" "Z:$chart"` (Note: you might need to put `./umu-run` instead, if you have umu extracted to the same folder as this launcher)
6) Click **Browse for Songs Folder**, and select the folder where your custom songs are stored.  This should start scanning the folder for charts.
7) It is recommended that you configure FastGH3 via its settings dialog by clicking **FastGH3 Settings**.  This will let you configure things such as windowed/borderless mode, game resolution, etc.
8) Once you have everything configured, select a song from the list and click **Play Song**.

Pro Tip: If you have a device running SteamOS (such as a Steam Deck), this program can be added to Steam and launched in Gaming Mode after being configured.

## Fixing guitar controller issues
If your guitar controller's inputs aren't working as intended (such as a CRKD guitar in Mode 8), then you might need to download [this `xinput1_3.dll` file](https://github.com/YoShibyl/FastGH3Launcher-python/raw/refs/heads/main/xinput1_3.dll) and place it where FastGH3 is installed.  This should force any controller to be recognized as an Xplorer guitar.

If you're on Linux, you'll also need to add this prefix to the beginning of the launch command in order to load the DLL: `WINEDLLOVERRIDES="xinput1_3=n" `

## Building
*soon™*

## Credit the Creators
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) is the library used for enhancing the UI
- [PyInstaller](https://pyinstaller.org/en/stable/) is used for compiling single-file binaries for release
- [donnaken15](https://github.com/donnaken15) : Maker of [FastGH3](https://github.com/donnaken15/FastGH3)
- [mdsitton](https://github.com/mdsitton) : Clone Hero developer who made [the `.sng` format](https://github.com/mdsitton/SngFileFormat)
- Neversoft / Aspyr : Makers of the original *Guitar Hero III* PC port
- Not sure who made the `xinput1_3.dll` file, but it was taken from BetterGH3's optional fixes folder
