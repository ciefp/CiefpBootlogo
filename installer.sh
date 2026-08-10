#!/bin/bash
##setup command=wget -q "--no-check-certificate" https://raw.githubusercontent.com/ciefp/CiefpBootlogo/main/installer.sh -O - | /bin/sh

######### Version & Changelog #########
version='1.0'
changelog='\n- Initial release\n- Fast GitHub MVI bootlogo installer\n- Local /tmp MVI installation support\n- Live image preview'
#######################################

# Check if we should skip restart (for batch installations)
SKIP_REBOOT="${SKIP_REBOOT:-0}"

TMPPATH=/tmp/CiefpBootlogo

if [ ! -d /usr/lib64 ]; then
	PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/CiefpBootlogo
else
	PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/CiefpBootlogo
fi

# Check package manager and OS type
if [ -f /var/lib/dpkg/status ]; then
	STATUS=/var/lib/dpkg/status
	OSTYPE=DreamOs
	PKG_UPDATE="apt-get update"
	PKG_INSTALL="apt-get install -y"
else
	STATUS=/var/lib/opkg/status
	OSTYPE=Dream
	PKG_UPDATE="opkg update"
	PKG_INSTALL="opkg install"
fi

echo ""
echo "============================================================"
echo "     CiefpBootlogo v$version Installer"
echo "============================================================"
echo ""

# Check Python version
if python --version 2>&1 | grep -q '^Python 3\.'; then
	echo "[OK] Python 3.x detected"
	PACKAGE_REQUESTS="python3-requests"
	PACKAGE_PIL="python3-pillow"
else
	echo "[OK] Python 2.x detected"
	PACKAGE_REQUESTS="python-requests"
	PACKAGE_PIL="python-imaging"
fi

echo ""

# Function to install package if missing
install_if_missing() {
	local pkg=$1
	local pkg_name=$2
	
	if grep -q "Package: $pkg" $STATUS 2>/dev/null; then
		echo "[OK] $pkg_name already installed"
		return 0
	else
		echo "[INSTALL] Installing $pkg_name..."
		$PKG_UPDATE > /dev/null 2>&1
		$PKG_INSTALL $pkg
		if [ $? -eq 0 ]; then
			echo "[OK] $pkg_name installed successfully"
			return 0
		else
			echo "[WARN] Failed to install $pkg_name"
			return 1
		fi
	fi
}

# Install required packages (requests & pillow/imaging)
install_if_missing "$PACKAGE_REQUESTS" "requests"
install_if_missing "$PACKAGE_PIL" "PIL (Pillow)"

echo ""
echo "============================================================"
echo ""

# Clean temporary & old plugin directory
[ -d $TMPPATH ] && rm -rf $TMPPATH
[ -d $PLUGINPATH ] && rm -rf $PLUGINPATH

mkdir -p $TMPPATH
cd $TMPPATH

echo "[DOWNLOAD] Downloading CiefpBootlogo..."

# Download archive from GitHub
if wget -q --no-check-certificate https://github.com/ciefp/CiefpBootlogo/archive/refs/heads/main.tar.gz; then
	echo "[OK] Download successful"
else
	echo "[ERROR] Failed to download plugin!"
	echo "       Please check internet connection and try again."
	exit 1
fi

echo "[EXTRACT] Extracting files..."
tar -xzf main.tar.gz

echo "[INSTALL] Installing plugin files..."
cp -r 'CiefpBootlogo-main/usr' '/'

cd
sleep 2

# Verify installation
if [ ! -d $PLUGINPATH ]; then
	echo "[ERROR] Plugin not installed correctly!"
	echo "       Please check repository structure (usr/lib/enigma2/...)."
	exit 1
fi

# Set permissions
chmod -R 755 $PLUGINPATH
echo "[OK] Permissions set"

# Cleanup
rm -rf $TMPPATH
sync

echo ""
echo "#########################################################"
echo "#          CiefpBootlogo INSTALLED SUCCESSFULLY         #"
echo "#                  developed by ciefp                   #"
echo "#                  .::CiefpSettings::.                  #"
echo "#               https://github.com/ciefp                #"
echo "#########################################################"

if [ "$SKIP_REBOOT" = "0" ]; then
    echo "#           GUI will RESTART in 3 seconds...            #"
    sleep 3
    killall -9 enigma2
else
    echo "#           Installation finished (No Reboot)           #"
fi