#!/usr/local/bin/python3

__doc__ = """
Platypus script for simple UI to mount and unmount rclone remotes on macOS.
Please see README.md for details
"""

import os
import subprocess
import sys
import logging
import configparser
import signal
import psutil

# User Configuration
USER_HOME = os.environ["HOME"]
MOUNT_ROOT = USER_HOME
RCLONE_CONFIG = os.path.join(USER_HOME, ".config", "rclone", "rclone.conf")
RCLONE_BINARY = "/usr/local/bin/rclone"
LOGGING_LEVEL = logging.INFO
LOG_FOLDER = os.path.join(USER_HOME, "Library", "Logs", "Mounter")

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
    # https://rclone.org/commands/rclone_mount/#vfs-directory-cache
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

# Rules to managing remote names
# 1. Ignore remotes with -raw, -intermediate, -hidden suffixes
# 2. Strip -exclusive suffix, but add configure additional flags that disable updates from
#    the remote to improve performance.
# 3. Replace - with space and make title case
# We parse rclone.conf and look for remote names that don't match the below criteria


def is_hidden(remote):
    """Check if the remote shall be visible based on the suffix"""
    return (
        remote.endswith("-raw")
        or remote.endswith("-intermediate")
        or remote.endswith("-hidden")
        or remote == "DEFAULT"
    )


SUFFIX_EXCLUSIVE = "-exclusive"


def is_exclusive(remote):
    """Check if remote shall be mounted in exclusive mode"""
    return remote.endswith(SUFFIX_EXCLUSIVE)


def strip_suffixes(remote):
    """Remove known suffixes from the visible remotes"""
    return remote.replace(SUFFIX_EXCLUSIVE, "")


def make_title(remote):
    """Synthesize the user visible title from the stripped remote name"""
    return strip_suffixes(remote).replace("-", " ").title()


def make_path(remote):
    """Derive mountpoint path from a stripped remote name"""
    return os.path.join(MOUNT_ROOT, strip_suffixes(remote))


def make_rclone_log_path(remote):
    """Derive path for rclone log."""
    return os.path.join(LOG_FOLDER, strip_suffixes(remote) + ".log")


def run_helper(shortname, args):
    """Executes the short running command line utility and logs outputs"""
    logging.info("Launching %s: %s", shortname, (" ".join(args)))

    try:
        process = subprocess.run(args, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        logging.error("Process %s exited with error %d", shortname, exc.returncode)
        logging.info("%s", exc.stdout)
        logging.error("%s", exc.stderr)
    else:
        if process.stdout:
            logging.info("%s: %s", shortname, process.stdout)
        if process.stderr:
            logging.error("%s: %s", shortname, process.stderr)


def construct_rclone_command_for_remote(remote, path, remote_obj):
    """Construct rclone command for specific remote"""

    remote_path = remote + ":"
    if "path" in remote_obj:
        remote_path = remote_path + remote_obj["path"]

    return (
        [
            RCLONE_BINARY,
            "--config",
            RCLONE_CONFIG,
            "mount",
            remote_path,
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
        + rclone_logging_flags
    )


# User visible prefixes and captions. Must be unique
CAPTION_SAFE_UNMOUNT = "⛔️ Unmount"
CAPTION_FORCE_UNMOUNT = "❌ Force Unmount"
CAPTION_MOUNT = "🎣 Mount"
CAPTION_SHOW_FOLDER = "📂 Show Mounted"
CAPTION_SHOW_LOG = "🔍 Show Logs For"
CAPTION_FLUSH_DIRECTORY_CACHES_FOR = "🧹 Flush Dir Caches For"
CAPTION_SHOW_MOUNTER_LOG = "🔍 Show Mounter Log"
CAPTION_FLUSH_DIRECTORY_CACHES_ALL = "🧹 Flush All Dir Caches"


def active_daemons():
    """Collect rclone instances running in --daemon mode that are not zombies"""
    result = {}
    for proc in psutil.process_iter(["name", "pid", "cmdline"]):
        if not proc.name() == "rclone":
            continue
        try:
            cmdline = proc.cmdline()
        except psutil.ZombieProcess:
            logging.warning("rclone(%d) is a zombie process, skipped", proc.pid)
            continue
        if "--daemon" not in cmdline:
            continue
        result[proc.pid] = cmdline

    return result


def flush_directory_caches(daemons, path=None):
    """Send SIGHUP to all or specific rclone daemon to flush caches"""
    for pid, cmdline in daemons.items():
        if not path or path in cmdline:
            logging.info("Flushing directory caches for rclone(%d)", pid)
            os.kill(pid, signal.SIGHUP)


def perform_action_for_remote(remote, action, remotes, daemons):
    """Action router for remotes"""
    path = make_path(remote)
    if CAPTION_MOUNT in action:
        if not os.path.exists(path):
            run_helper("mkdir", ["mkdir", "-p", path])
        run_helper(
            "rclone", construct_rclone_command_for_remote(remote, path, remotes[remote])
        )
    elif CAPTION_SAFE_UNMOUNT in action:
        run_helper("unmount", ["/usr/sbin/diskutil", "unmount", path])
        run_helper("rmdir", ["/bin/rmdir", path])
    elif CAPTION_FORCE_UNMOUNT in action:
        run_helper("ummount", ["/usr/sbin/diskutil", "unmount", "force", path])
        run_helper("rmdir", ["/bin/rmdir", path])
    elif CAPTION_SHOW_FOLDER in action:
        run_helper("open", ["open", path])
    elif CAPTION_SHOW_LOG in action:
        run_helper("open", ["open", make_rclone_log_path(remote)])
    elif CAPTION_FLUSH_DIRECTORY_CACHES_FOR in action:
        flush_directory_caches(daemons, path)
    else:
        logging.error('Unknown action "%s" for "%s".', action, make_title(remote))


def perform_action_global(action, daemons):
    """Action router global"""
    if CAPTION_SHOW_MOUNTER_LOG in action:
        run_helper("open", ["open", os.path.join(LOG_FOLDER, "Mounter.log")])
    elif CAPTION_FLUSH_DIRECTORY_CACHES_ALL in action:
        flush_directory_caches(daemons)
    else:
        logging.error('Action "%s" is unrecognized. Doing nothing.', action)


def daemon_exists_for_path(path, daemons):
    """Check if this mountpoint is served by an rclone daemon"""
    for _, cmdline in daemons.items():
        if path in cmdline:
            return True
    return False


def populate_menu(remotes, daemons):
    """Populate the menu if no arguments passed by emitting menu item strings."""
    logging.info("Populating the menu")
    for remote in remotes:
        if is_hidden(remote):
            continue
        path = make_path(remote)
        title = make_title(remote)
        if os.path.ismount(path):
            print(
                f"SUBMENU|🟢 {title}"
                + f"|{CAPTION_SHOW_FOLDER} {title}"
                + f"|{CAPTION_SAFE_UNMOUNT} {title}"
                + f"|{CAPTION_FORCE_UNMOUNT} {title}"
                + f"|{CAPTION_FLUSH_DIRECTORY_CACHES_FOR} {title}"
                + f"|{CAPTION_SHOW_LOG} {title}"
            )
        elif daemon_exists_for_path(path, daemons):
            print(f"SUBMENU|🟡 {title} [Working...]|{CAPTION_SHOW_LOG} {title}")
        else:
            print(
                f"SUBMENU|🔴 {title}"
                + f"|{CAPTION_MOUNT} {title}"
                + f"|{CAPTION_SHOW_LOG} {title}"
            )

    print("----")
    print(CAPTION_FLUSH_DIRECTORY_CACHES_ALL)
    print(CAPTION_SHOW_MOUNTER_LOG)


def perform_action(action, remotes, daemons):
    """Try to apply action to specific remote, if none found -- globally"""
    logging.info('Action received: "%s"', action)
    for remote in remotes:
        if not is_hidden(remote) and make_title(remote) in action:
            perform_action_for_remote(remote, action, remotes, daemons)
            return
    perform_action_global(action, daemons)


if __name__ == "__main__":

    # Initialize logging
    if not os.path.exists(LOG_FOLDER):
        run_helper("mkdir", ["mkdir", "-p", LOG_FOLDER])

    logging.basicConfig(
        filename=os.path.join(LOG_FOLDER, "Mounter.log"),
        encoding="utf-8",
        format="%(asctime)s : %(levelname)s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=LOGGING_LEVEL,
    )

    # Parser for rclone configuration
    rclone_remotes = configparser.ConfigParser()
    rclone_remotes.read(RCLONE_CONFIG)

    # Active rclone daemons
    active_daemons = active_daemons()

    if len(sys.argv) == 1:
        populate_menu(rclone_remotes, active_daemons)
    else:
        perform_action(sys.argv[1], rclone_remotes, active_daemons)
