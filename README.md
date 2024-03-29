## Platypus script for simple UI to mount and unmount rclone remotes on macOS

### Prerequisites

- `rclone` from https://rclone.org, not brew
- `macFUSE` from https://osxfuse.github.io
- Python3 and pip3
- `platypus` from https://sveinbjorn.org/platypus

### Configuration

#### Remote Naming

Name rclone remotes with the expectation that the script: 
- Derives user-readable title from rclone remote names by replacing `-` with ` ` and converting to title case
- Skips remote if its name ends with specific suffixes, such as `-hidden`, `-intermediate`, `-raw`, etc. This is handy when using crypt remote: you would not want to manually mount the underlying raw storage, only mount crypt remote.
- If special suffix `-exclusive` is encountered, it is first stripped, and then special rclone options are added that turn off or significantly slow down updates from remote. This is worthwhile optimization when the data be changed through the mount exclusively, not via the web interface or another rclone instance. Having these flags set and then attempting to modify content on the remote anyway outside of mount will likely result in corruption. 

For example: 

```
[google-drive]
type = drive
...

[encrypted-data-raw]
type = drive
...

[secret-encrypted-data-exclusive]
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

#### Specifying remote mount path
By default the root of the remote will be mounted. To mount a specific sub-path -- add `path = /sub/path` to the remote configuration

### Usage

Checkout the repository and run the `make run` to create `Mounter.app` wrapper at `~/Applications` and launch it. Look for '🏔' in the menu bar.

Run `make` without arguments to list available targets


### Contribution guidelines

1. Fork the project
2. Make and test your changes
3. Make sure `make lint` passes
4. Optionally, submit PR