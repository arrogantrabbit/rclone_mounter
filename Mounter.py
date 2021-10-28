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

# Common choices include "-v" or "-vv" for debugging.
rclone_logging_flags = []

# If the data will only be changed through this mounted remote,
# and not by any other means, including web interface or another rclone instance,
# this will effectively disable remote refresh for a small gain in performance.
rclone_options_exclusive_mode = [
    #
    # time the kernel caches the attributes for. Reduces roundtrips to kernel,
    # no risk of corruption if files don't change externally.
    # Otherwise -- remove it!
    "--attr-timeout",
    "60s",
    #
    # Cache directories forever.
    # We can always send "SIGHUP" to force refresh directory caches
    "--dir-cache-time",
    "1000h",
    #
    # Don't poll for changes from remote
    "--poll-interval",
    "0",
]

# Options for cases when the remote can be concurrently accessed via both mount and
# some other side channel. Relevant optons are left to default, this placeholder will
# help with future expansion
rclone_options_default_mode = []

rclone_options_common = [
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
    # For how long kernel should wait before giving up. Imperative for mount stabilty
    "--daemon-timeout",
    "599s",
    #
    # Run as a daemon
    "--daemon",
    #
    # Statistics as one-liners
    "--stats-one-line",
    #
    # Adjust stats output to appear without -v
    "--stats-log-level",
    "NOTICE",
    #
    # Output statistics and progres periodically, until SIGINFO works in --daemon mode
    "--stats",
    "1m",
]


# Executes the short running command line utility and logs outputs
def run_helper(shortname, args):
    logging.info("Launching {}: {}".format(shortname, " ".join(args)))
    p = subprocess.run(args, capture_output=True, text=True)
    if p.stdout:
        logging.info("{}: {}".format(shortname, p.stdout))
    if p.stderr:
        logging.error("{}: {}".format(shortname, p.stderr))


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


# Rules to managing remote names
# 1. Ignore remotes with -raw, -intermediate, -hidden suffixes
# 2. Strip -exclusive suffix, but add configure additional flags that disable updates from
#    the remote to improve performance.
# 3. Replace - with space and make title case
# We parse rclone.conf and look for remote names that don't match the below criteria


def is_hidden(key):
    return (
        key.endswith("-raw")
        or key.endswith("-intermediate")
        or key.endswith("-hidden")
        or key == "DEFAULT"
    )


SUFFIX_EXCLUSIVE = "-exclusive"


def is_exclusive(key):
    return key.endswith(SUFFIX_EXCLUSIVE)


def strip_suffixes(key):
    return key.replace(SUFFIX_EXCLUSIVE, "")


# we use remote names to come up with user friendly titles like so
def make_title(key):
    return strip_suffixes(key).replace("-", " ").title()


# Mount points are also derived from the remote names
def make_path(key):
    return os.path.join(mount_root, strip_suffixes(key))


# Path for rclone log file
def make_rclone_log_path(key):
    return os.path.join(log_folder, strip_suffixes(key) + ".log")


def build_list_of_active_daemons():
    active_daemons = dict()
    # https://rclone.org/commands/rclone_mount/#vfs-directory-cache
    for p in psutil.process_iter(["name", "pid", "cmdline"]):
        if not p.name() == "rclone":
            continue
        try:
            cmdline = p.cmdline()
        except psutil.ZombieProcess:
            logging.warning("rclone({}) is a zombie process, skipped".format(p.pid))
            continue
        except Exception as e:
            logging.info(
                "Exception occured getting a command line for rclone({}): {}".format(
                    p.pid, e
                )
            )
            continue
        if "--daemon" not in cmdline:
            continue
        active_daemons[p.pid] = cmdline

    return active_daemons


active_daemons = build_list_of_active_daemons()


def flush_directory_caches(path=None):
    for pid, cmdline in active_daemons.items():
        if not path or path in cmdline:
            logging.info("Flushing directory caches for {}({})".format("rclone", pid))
            os.kill(pid, signal.SIGHUP)


def daemon_exists_for_path(path):
    for pid, cmdline in active_daemons.items():
        if path in cmdline:
            return True
    return False


# User visible prefixes and captions. Must be unique
safe_unmount_caption = "⛔️ Unmount"
force_unmount_caption = "❌ Force Unmount"
mount_caption = "🎣 Mount"
show_folder_caption = "📂 Show Mounted"
show_log_caption = "🔍 Show Logs For"
flush_directory_caches_for_caption = "🧹 Flush Dir Caches For"
show_mounter_log_caption = "🔍 Show Mounter Log"
flush_directory_caches_caption = "🧹 Flush All Dir Caches"

# Populate the menu if no arguments passed by emitting menu item strings.
if len(sys.argv) == 1:

    logging.info("Populating the menu")
    for remote in remotes:
        if is_hidden(remote):
            continue
        path = make_path(remote)

        if os.path.ismount(path):
            print(
                "SUBMENU|🟢 {0}|{1} {0}|{2} {0}|{3} {0}|{4} {0}|{5} {0}".format(
                    make_title(remote),
                    show_folder_caption,
                    safe_unmount_caption,
                    force_unmount_caption,
                    flush_directory_caches_for_caption,
                    show_log_caption,
                )
            )
        elif daemon_exists_for_path(path):
            print(
                "SUBMENU|🟡 {0} [Working...]|{1} {0}".format(
                    make_title(remote), show_log_caption
                )
            )
        else:
            print(
                "SUBMENU|🔴 {0}|{1} {0}|{2} {0}".format(
                    make_title(remote), mount_caption, show_log_caption
                )
            )

    print("----")
    print(flush_directory_caches_caption)
    print(show_mounter_log_caption)
else:
    action = sys.argv[1]
    target_matched = False
    logging.info('Action received: "{}"'.format(action))
    for remote in remotes:
        if not is_hidden(remote) and make_title(remote) in action:
            path = make_path(remote)
            target_matched = True
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
                        remote + ":",
                        path,
                        "--volname",
                        make_title(remote),
                        "--log-file",
                        make_rclone_log_path(remote),
                    ]
                    + rclone_options_common
                    + (
                        rclone_options_exclusive_mode
                        if is_exclusive(remote)
                        else rclone_options_default_mode
                    )
                    + rclone_logging_flags,
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
                run_helper("open", ["open", make_rclone_log_path(remote)])
            elif flush_directory_caches_for_caption in action:
                flush_directory_caches(path)
            else:
                logging.error(
                    'Action "{}" is unrecognized for "{}".'.format(
                        action, make_title(remote)
                    )
                )

    if not target_matched:
        if show_mounter_log_caption in action:
            run_helper("open", ["open", os.path.join(log_folder, "Mounter.log")])
        elif flush_directory_caches_caption in action:
            flush_directory_caches()
        else:
            logging.error('Action "{}" is unrecognized. Doing nothing.'.format(action))
