# -*- coding: utf-8 -*-
from enigma import ePixmap
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSelection, ConfigSubsection
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.Label import Label
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists, pathExists
from Plugins.Plugin import PluginDescriptor
import os
import requests
import json
from PIL import Image
import io
import tempfile
import shutil

PLUGIN_VERSION = "1.0"
PLUGIN_NAME = "CiefpBootlogo"
PLUGIN_ICON = "icon.png"

config.plugins.CiefpBootlogo = ConfigSubsection()
config.plugins.CiefpBootlogo.source = ConfigSelection(default="Online", choices=[("Online", "Online Source"), ("Local", "Local Source (/tmp)")])

MAIN_SKIN = """
    <screen name="CiefpBootlogoMain" position="center,center" size="1920,1080" backgroundColor="#011a2e" flags="wfNoBorder">
        <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />  
        <widget name="plugin_title" position="0,10" size="1920,40" font="Bold;30" halign="center" backgroundColor="#010203" foregroundColor="#FFFFFF" />
        
        <widget name="filelist" position="50,80" size="580,880" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#1a1a2e" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" scrollbarMode="showOnDemand" itemHeight="45" enableWrapAround="1" borderWidth="2" borderColor="#003366" />
        
        <widget name="preview" position="660,80" size="1210,880" backgroundColor="#0a0a1a" borderWidth="3" borderColor="#003366" alphatest="on" />
        
        <widget name="status" position="50,980" size="1820,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" />
        
        <widget name="legend" position="50,1030" size="1820,40" font="Regular;20" foregroundColor="#aaaaaa" backgroundColor="#0a0a1a" transparent="1" halign="center" />
    </screen>
"""

def apply_bootlogo_mvi(source_mvi_path_or_bytes):
    """Writes the .mvi content directly to all Enigma2 bootlogo system locations"""
    target_paths = [
        "/usr/share/bootlogo.mvi",
        "/usr/share/backdrop.mvi",
        "/usr/share/bootlogo_wait.mvi"
    ]
    try:
        if isinstance(source_mvi_path_or_bytes, bytes):
            for path in target_paths:
                with open(path, 'wb') as f:
                    f.write(source_mvi_path_or_bytes)
        else:
            for path in target_paths:
                shutil.copyfile(source_mvi_path_or_bytes, path)
        return True, "Bootlogo updated successfully!"
    except Exception as e:
        return False, "Error applying bootlogo: " + str(e)


class CiefpBootlogoMain(Screen):
    def __init__(self, session):
        self.skin = MAIN_SKIN
        Screen.__init__(self, session)
        self.session = session
        self.temp_preview_path = None
        self.online_files_dict = {}

        self.setup_actions()
        self.create_gui()
        
        self.onLayoutFinish.append(self.load_online_content)

    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.download_and_apply,
            "cancel": self.close,
            "red": self.close,
            "green": self.download_and_apply,
            "blue": self.change_source,
            "up": self.move_up,
            "down": self.move_down
        }, -1)

    def create_gui(self):
        self["filelist"] = MenuList([])
        self["filelist"].onSelectionChanged.append(self.preview_online_image)
        
        self["plugin_title"] = Label("..:: Ciefp Bootlogo - GitHub Source ::..")
        self["separator0"] = Label()
        self["preview"] = Pixmap()
        self["status"] = Label("Loading content from GitHub...")
        self["legend"] = Label("Red: Exit | Green / OK: Download & Apply | Blue: Change Source")

    def show_placeholder(self):
        try:
            placeholder_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpBootlogo/placeholder.png"
            if fileExists(placeholder_path) and hasattr(self["preview"], 'instance') and self["preview"].instance:
                self["preview"].instance.setPixmapFromFile(placeholder_path)
                self["preview"].instance.setScale(1)
        except Exception as e:
            print("[CiefpBootlogo] Placeholder error: " + str(e))

    def load_online_content(self):
        self.show_placeholder()
        github_url = "https://api.github.com/repos/ciefp/CiefpBootlogo/contents/Bootlogo"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(github_url, headers=headers, timeout=10)
            if response.status_code == 200:
                files = response.json()
                file_names = []
                self.online_files_dict = {}
                
                for file in files:
                    if isinstance(file, dict) and file.get('type') == 'file':
                        name = file.get('name', '')
                        if name.lower().endswith(('.jpg', '.jpeg', '.png')):
                            file_names.append(name)
                            self.online_files_dict[name] = file.get('download_url', '')
                        
                self["filelist"].setList(file_names)
                if file_names:
                    self["status"].setText("Found " + str(len(file_names)) + " online images")
                    self.preview_online_image()
                else:
                    self["status"].setText("No images found in repository")
            else:
                self["status"].setText("GitHub connection error (Status: " + str(response.status_code) + ")")
        except Exception as e:
            self["status"].setText("Network error: " + str(e))

    def preview_online_image(self):
        file_name = self["filelist"].getCurrent()
        if not file_name or file_name not in self.online_files_dict:
            self.show_placeholder()
            return
            
        download_url = self.online_files_dict[file_name]
        try:
            self.cleanup_preview()
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(download_url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content))
                img.thumbnail((1210, 880), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                self.temp_preview_path = "/tmp/preview_online.jpg"
                img.save(self.temp_preview_path, 'JPEG', quality=90)
                
                if hasattr(self["preview"], 'instance') and self["preview"].instance:
                    self["preview"].instance.setPixmapFromFile(self.temp_preview_path)
                    self["preview"].instance.setScale(1)
                self["status"].setText("Previewing: " + file_name)
        except Exception as e:
            self["status"].setText("Preview error: " + str(e))
            self.show_placeholder()

    def cleanup_preview(self):
        if self.temp_preview_path and os.path.exists(self.temp_preview_path):
            try:
                os.remove(self.temp_preview_path)
            except:
                pass
            self.temp_preview_path = None

    def download_and_apply(self):
        file_name = self["filelist"].getCurrent()
        if not file_name or file_name not in self.online_files_dict:
            return
            
        base_name = os.path.splitext(file_name)[0]
        mvi_name = base_name + ".mvi"
        
        image_url = self.online_files_dict[file_name]
        mvi_url = image_url.rsplit('/', 1)[0] + "/" + mvi_name
        
        try:
            self["status"].setText("Downloading " + mvi_name + "...")
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(mvi_url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                success, msg = apply_bootlogo_mvi(response.content)
                if success:
                    self.session.open(MessageBox, "Bootlogo downloaded and installed successfully!", MessageBox.TYPE_INFO)
                    self["status"].setText("Applied: " + mvi_name)
                else:
                    self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
            else:
                self.session.open(MessageBox, "Corresponding .mvi file not found on GitHub:\n" + mvi_name, MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, "Download error: " + str(e), MessageBox.TYPE_ERROR)

    def change_source(self):
        choices = [
            ("Online", "Online Source (GitHub)"),
            ("Local", "Local Source (/tmp)")
        ]
        self.session.openWithCallback(self.source_selected, ChoiceBox, title="Select Source", list=choices)

    def source_selected(self, choice):
        if not choice:
            return
            
        if choice[0] == "Local":
            self.check_local_tmp_mvi()

    def check_local_tmp_mvi(self):
        tmp_dir = "/tmp"
        mvi_files = []
        
        try:
            if pathExists(tmp_dir):
                for f in os.listdir(tmp_dir):
                    if f.lower().endswith(".mvi"):
                        mvi_files.append(f)
        except Exception as e:
            print("[CiefpBootlogo] Error checking /tmp: " + str(e))

        if mvi_files:
            # If there are local .mvi files in /tmp
            self.found_mvi_path = os.path.join(tmp_dir, mvi_files[0])
            msg = "Found local file in /tmp:\n" + mvi_files[0] + "\n\nDo you want to install this bootlogo?"
            self.session.openWithCallback(self.confirm_local_install, MessageBox, msg, MessageBox.TYPE_YESNO)
        else:
            # If no .mvi files are present in /tmp
            msg = "No .mvi files found in /tmp folder.\n\nPlease copy your .mvi file to /tmp directory and try again."
            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def confirm_local_install(self, answer):
        if answer:
            if hasattr(self, 'found_mvi_path') and fileExists(self.found_mvi_path):
                success, msg = apply_bootlogo_mvi(self.found_mvi_path)
                if success:
                    self.session.open(MessageBox, "Local bootlogo installed successfully!", MessageBox.TYPE_INFO)
                    self["status"].setText("Installed local MVI from /tmp")
                else:
                    self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)

    def move_up(self):
        self["filelist"].up()
        
    def move_down(self):
        self["filelist"].down()

    def __onClose(self):
        self.cleanup_preview()


def main(session, **kwargs):
    session.open(CiefpBootlogoMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="{0} v{1}".format(PLUGIN_NAME, PLUGIN_VERSION),
            description="Download and change Enigma2 bootlogo MVI images",
            icon=PLUGIN_ICON,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]