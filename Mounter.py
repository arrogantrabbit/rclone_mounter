#!/usr/local/bin/python3
import os
import subprocess
import sys
import logging
import configparser
import psutil
import signal

# User Configuration
user_home = os.environ["HOME"]
mount_root = user_home
rclone_config = os.path.join(user_home, ".config", "rclone", "rclone.conf")
rclone_binary = "/usr/local/bin/rclone"
logging_level = logging.INFO
log_folder = os.path.join(user_home, "Library", "Logs", "Mounter")
rclone_verbose_logging = False

# We assume the data will only be changed through this remote,
# and not by any other means, including web interface or another rclone instance,
# we are going to effectively disable remote refresh
uber_important_rclone_options = (
    [
        #
        # to avoid I/O errors when file is considered "harmful" by Google
        "--drive-acknowledge-abuse",
        #
        # Full cache mode for best compatibility
        "--vfs-cache-mode",
        "full",
        #
        # 1TB max total size cached
        "--vfs-cache-max-size",
        "1024G",
        #
        # Cache files forever
        "--vfs-cache-max-age",
        "1000h",
        #
        # Check cache for stale objects every so often. Default is 1m, 5 min is
        # good enough; we mainly want to remove files from cache once the size
        # exceeds the max-size above
        "--vfs-cache-poll-interval",
        "5m",
        #
        # time the kernel caches the attributes for. Reduces roundtrips to kernel,
        # no risk of corruption since files don't change externally.
        # Otherwise -- remove it!
        "--attr-timeout",
        "60s",
        #
        # Cache directories forever.
        # We can always send "SIGHUP" to force refresh directory caches
        "--dir-cache-time",
        "1000h",
        #
        # Don't poll for changes on remote
        "--poll-interval",
        "0",
        #
        # For how long kernel should wait before giving up. Imperative for mount stabilty
        "--daemon-timeout",
        "599s",
        #
        # run as a daemon
        "--daemon",
    ]
    + ["-vv"]
    if rclone_verbose_logging
    else []
)


# Executes the short running command line utility and logs outputs
def run_helper(shortname, args):
    logging.info("Launching {}: {}".format(shortname, " ".join(args)))
    p = subprocess.run(args, capture_output=True, text=True)
    if p.stdout:
        logging.info("{}: {}".format(shortname, p.stdout))
    if p.stderr:
        logging.info("{}: {}".format(shortname, p.stderr))


# Initialize logging
if not os.path.exists(log_folder):
    run_helper("mkdir", ["mkdir", "-p", log_folder])

logging.basicConfig(
    filename=os.path.join(log_folder, "Mounter.log"),
    encoding="utf-8",
    format="%(asctime)s : %(levelname)s : %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging_level,
)

# Parser for rclone configuration
remotes = configparser.ConfigParser()
remotes.read(rclone_config)


# We parse rclone.conf and look for remote names that don't match the below criteria
def is_hidden(key):
    return (
        key.endswith("-raw")
        or key.endswith("-intermediate")
        or key.endswith("-hidden")
        or key == "DEFAULT"
    )


# we use remote names to come up with user friendly titles like so
def make_title(key):
    return key.replace("-", " ").title()


# Mount points are also derived from the remote names
def make_path(key):
    return os.path.join(mount_root, key)


# Path for rclone log file
def make_rclone_log_path(key):
    return os.path.join(log_folder, item + ".log")


def flush_all_directory_caches():
    # https://rclone.org/commands/rclone_mount/#vfs-directory-cache
    for p in psutil.process_iter(["name", "pid", "cmdline"]):
        if p.name() == "rclone" and "--daemon" in p.cmdline():
            logging.info("Flushing directory caches for {}({})".format(p.name(), p.pid))
            os.kill(p.pid, signal.SIGHUP)


# User visible prefixes and captions. Must be unique
safe_unmount_caption = "⛔️ Unmount"
force_unmount_caption = "❌ Force Unmount"
mount_caption = "🎣 Mount"
show_folder_caption = "📂 Show"
show_log_caption = "🔍 Logs"
show_mounter_log_caption = "🔍 Show Mounter Log"
flush_directory_caches = "🧹 Flush all dir caches"

# Populate the menu if no arguments passed by emitting menu item strings.
if len(sys.argv) == 1:
    logging.info("Populating the menu")
    for item in remotes:
        if is_hidden(item):
            continue
        if os.path.ismount(make_path(item)):
            print(
                "SUBMENU|🟢 {0}|{1} {0}|{2} {0}|{3} {0}|{4} {0}".format(
                    make_title(item),
                    show_folder_caption,
                    safe_unmount_caption,
                    force_unmount_caption,
                    show_log_caption,
                )
            )
        else:
            print(
                "SUBMENU|🔴 {0}|{1} {0}|{2} {0}".format(
                    make_title(item), mount_caption, show_log_caption
                )
            )

    print("----")
    print(flush_directory_caches)
    print(show_mounter_log_caption)
else:
    action = sys.argv[1]
    logging.info("Action received: {}".format(action))
    for item in remotes:
        if is_hidden(item):
            continue
        path = make_path(item)
        if make_title(item) in action:
            if mount_caption in action:
                if not os.path.exists(path):
                    run_helper("mkdir", ["mkdir", "-p", path])
                run_helper(
                    "rclone",
                    [
                        rclone_binary,
                        "--config",
                        rclone_config,
                        "mount",
                        item + ":",
                        path,
                        "--volname",
                        make_title(item),
                        "--log-file",
                        make_rclone_log_path(item),
                    ]
                    + uber_important_rclone_options,
                )
            elif safe_unmount_caption in action:
                run_helper("unmount", ["/usr/sbin/diskutil", "unmount", path])
                run_helper("rmdir", ["/bin/rmdir", path])
            elif force_unmount_caption in action:
                run_helper("ummount", ["/usr/sbin/diskutil", "unmount", "force", path])
                run_helper("rmdir", ["/bin/rmdir", path])
            elif show_folder_caption in action:
                run_helper("open", ["open", path])
            elif show_log_caption in action:
                run_helper("open", ["open", make_rclone_log_path(item)])
            else:
                logging.error("Action {} is unrecognized. Doing nothing.".format(action))
    if show_mounter_log_caption in action:
        run_helper("open", ["open", os.path.join(log_folder, "Mounter.log")])
    elif flush_directory_caches in action:
        flush_all_directory_caches()
    else:
        logging.error("Action {} is unrecognized. Doing nothing.".format(action))
