## Platypus script for simple UI to mount and unmount rclone remotes on macOS

### Prerequisities

- `rclone` from rclone.org, not brew
- `macFUSE` from https://osxfuse.github.io
- Python3 and pip3
- `platypus` from https://sveinbjorn.org/platypus

### Usage

- Derive user-readable title from rclone remote name by replacing `-` with ` ` and converting to title case
- Skip remote if its name ends with specific suffixes, such as `-hidden`, `-intermediate`, `-raw`, etc. This is handy when using crypt remote: you would not want to manually mount the underlying raw storage, only mount crypt remote.

For example: 
```
[google-drive-raw]
type = drive
...

[google-drive]
type = crypt
remote = google-drive-raw:
...
```

Run the `make run` to create wrapper at ~/Applications and launch it. 
Control mounts from the menu item

