.PHONY: help

TARGET="$(HOME)/Applications/Mounter.app"

help: 
	@echo "Available targets"
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

define check_install_shell
	@command -v $(1) > /dev/null || (echo "ERROR: $(1) is missing. $(2)"; exit 1)
endef

define check_install_pip3
	@[[ ! -z $$(pip3 list | grep "$(1)" ) ]] ||  pip3 install $(1)
endef

.PHONY: check-tools 
check-tools: 		## Check for tools and python modules. Install python modules as needed
	@echo "Checking for tools"
	$(call check_install_shell,platypus,)
	$(call check_install_shell,python3,)
	$(call check_install_shell,rclone,Install directly from rclone.org. Homebrew version won't work)
	$(call check_install_shell,pip3,)
	$(call check_install_pip3,psutil)
	$(call check_install_pip3,black)

.PHONY: patch-rclone-path
patch-rclone-path: 	## Embed absolute path to rclone on this system to Mounter.py
patch-rclone-path: check-tools
	@echo "Patching the rclone path in Mounter.py"
	@sed -i "" "s|rclone_binary = .*$$|rclone_binary = \"$$(which rclone)\"|g" Mounter.py

.PHONY: format
format:			## Format python code using Black formatter
	@python3 -m black Mounter.py

define platypusify
	@mkdir -p "$(TARGET)"
	@platypus --overwrite \
	     --background \
	     --name "Mounter"  \
	     --interface-type "Status Menu"  \
	     --status-item-kind "Text" --status-item-title '🏔' --status-item-sysfont \
	     --bundle-identifier "com.arrogantrabbit.mounter" \
	     "./Mounter.py" \
	     "$(TARGET)" $(1)
endef

.PHONY: install 
install:		## Install the Platypus wrapper to "~/Applications"
install: check-tools format patch-rclone-path
	$(call platypusify,--optimize-nib)

.PHONY: install-local
install-local:		## Install the Platypus wrapper with symlink to script instead of copying
install-local: check-tools format patch-rclone-path
	$(call platypusify,--symlink)
	
.PHONY: run
run: 			## Make and run wrapper.
run: install
	@echo "Launching $(TARGET)"
	@open "$(TARGET)"