## Platypus script for simple UI to mount and unmount rclone remotes on macOS

### Prerequisites

- `rclone` from https://rclone.org, not brew
- `macFUSE` from https://osxfuse.github.io
- Python3 and pip3
- `platypus` from https://sveinbjorn.org/platypus

### Configuration

Name rclone remotes with the expectation that the script: 
- Derives user-readable title from rclone remote name by replacing `-` with ` ` and converting to title case
- Skips remote if its name ends with specific suffixes, such as `-hidden`, `-intermediate`, `-raw`, etc. This is handy when using crypt remote: you would not want to manually mount the underlying raw storage, only mount crypt remote.

For example: 

```
[google-drive]
type = drive
...

[encrypted-data-raw]
type = drive
...

[secret-encrypted-data]
type = crypt
remote = encrypted-data-raw:
...
```

will result in the main menu containing the following items (one shown as mounted, another unmounted for illustration purposes):

🟢  Google Drive	<br>
🔴  Secret Encrypted Data<br>

Each item will have a submenu, with the following actions: 

📂 Show<br>
⛔️ Unmount<br>
❌ Force<br>
🎣 Mount<br>
🔍 Logs<br>

### Usage

Checkout the repository and run the `make run` to create `Mounter.app` wrapper at `~/Applications` and launch it. Look for '🏔' in the menu bar.

Run `make` without arguments to list available targets
