#!/bin/zsh
# make sure platypus and rclone exist
command -v platypus || { echo "Install platypus"; exit 1 }
[ -f /usr/local/bin/rclone ] || { echo "Install rclone to /usr/local/bin/rclone"; exit 2 }
command -v python3 || { echo "Where is python3"; exit 3 }


# format the code
python3 -m black Mounter.py || exit 4

 

platypus    -y \
	     --background \
	     --app-icon "/Applications/Platypus.app/Contents/Resources/PlatypusDefault.icns"  \
	     --name "Mounter"  \
	     --interface-type "Status Menu"  \
	     --interpreter $(which python3)  \
	     --status-item-kind "Text" --status-item-title '🏔' --status-item-sysfont \
	     --status-item-template-icon \
	     "./Mounter.py"
