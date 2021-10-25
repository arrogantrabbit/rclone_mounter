
LOCAL_TARGET="Mounter.app"
TARGET="$(HOME)/Applications/Mounter.app"

.PHONY: help
help: 
	@echo 
	@echo "Available targets:"
	@echo 
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
	@echo
	@echo "Example: "
	@echo "   make run"

define check_install_shell
	@command -v $(1) > /dev/null || (echo "ERROR: $(1) is missing. $(2)"; exit 1)
endef

define check_install_pip3
	@[[ ! -z $$(pip3 list | grep "$(1)" ) ]] ||  pip3 install $(1)
endef

.PHONY: check-tools 
check-tools: 		## Check for tools and python modules. Installs python modules as needed
	@echo "Checking for tools"
	$(call check_install_shell,platypus,)
	$(call check_install_shell,python3,)
	$(call check_install_shell,rclone,Install directly from rclone.org. Homebrew version won't work)
	$(call check_install_shell,pip3,)
	$(call check_install_pip3,psutil)

.PHONY: patch-rclone-path
patch-rclone-path: 	## Embed absolute path to rclone on this system to Mounter.py
patch-rclone-path: check-tools
	@echo "Patching the rclone path in Mounter.py"
	@sed -i "" "s|rclone_binary = .*$$|rclone_binary = \"$$(which rclone)\"|g" Mounter.py

define platypusify
	@echo targeting $(2)
	@mkdir -p "$(2)"
	@platypus --overwrite \
	     --background \
	     --name "Mounter"  \
	     --interface-type "Status Menu"  \
	     --status-item-kind "Text" --status-item-title '🏔' --status-item-sysfont \
	     --bundle-identifier "com.arrogantrabbit.mounter" \
	     "./Mounter.py" \
	     "$(2)" $(1)
endef

.PHONY: install 
install:		## Install the Platypus wrapper to "~/Applications" with default logging
install: check-tools patch-rclone-path
	$(call platypusify,--optimize-nib,$(TARGET))

.PHONY: run
run: 			## Make and run wrapper.
run: install
	@echo "Launching $(TARGET)"
	@open "$(TARGET)"

.PHONY: check-tools-dev 
check-tools-dev: 	## Checks for tools useful for development
check-tools-dev: check-tools
	@echo "Checking for dev tools"
	$(call check_install_pip3,black)
	$(call check_install_pip3,flake8)


.PHONY: format
format: 		## Run Black formatter and Flake8
format: check-tools-dev 
	@python3 -m black --line-length 90 Mounter.py
	@python3 -m flake8 --max-line-length 90 Mounter.py

.PHONY: install-dev
install-dev:		## Create wrapper with symlink to script and verbose logging.
install-dev: check-tools-dev format patch-rclone-path
	$(call platypusify,--symlink,$(LOCAL_TARGET))
	
.PHONY: run-dev
run-dev: 		## Make and run dev wrapper in local folder
run-dev: install-dev
	@echo "Launching $(LOCAL_TARGET)"
	@open "$(LOCAL_TARGET)"
	
