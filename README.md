## Platypus script for simple UI to mount and unmount rclone remotes on macOS


To use: 

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

Run the `create_platypus_bundle.sh` to create wrapper. 
Launch `Mounter.app`


