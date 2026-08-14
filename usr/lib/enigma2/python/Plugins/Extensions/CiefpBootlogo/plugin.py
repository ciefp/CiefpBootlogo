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

PLUGIN_VERSION = "1.2"
PLUGIN_NAME = "CiefpBootlogo"
PLUGIN_ICON = "icon.png"

config.plugins.CiefpBootlogo = ConfigSubsection()
config.plugins.CiefpBootlogo.source = ConfigSelection(default="Online", choices=[
    ("Online", "Online Source (GitHub)"),
    ("Local", "Local Source (/tmp)")
])

MAIN_SKIN = """
    <screen name="CiefpBootlogoMain" position="center,center" size="1920,1080" backgroundColor="#011a2e" flags="wfNoBorder">
        <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />  
        <widget name="plugin_title" position="0,10" size="1920,40" font="Bold;30" halign="center" backgroundColor="#010203" foregroundColor="#FFFFFF" />
        
        <widget name="filelist" position="50,80" size="580,880" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#1a1a2e" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" scrollbarMode="showOnDemand" itemHeight="45" enableWrapAround="1" borderWidth="2" borderColor="#003366" />
        
        <widget name="preview" position="660,80" size="1210,880" backgroundColor="#0a0a1a" borderWidth="3" borderColor="#003366" alphatest="on" />
        
        <widget name="status" position="50,980" size="1820,60" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" />
        
        <widget name="legend" position="50,1040" size="1820,40" font="Regular;20" foregroundColor="#aaaaaa" backgroundColor="#0a0a1a" transparent="1" halign="center" />
    </screen>
"""

def apply_bootlogo_mvi(source_mvi_path_or_bytes):
    """Writes the .mvi content directly to all Enigma2 bootlogo system locations with backup"""
    target_paths = [
        "/usr/share/bootlogo.mvi",
        "/usr/share/backdrop.mvi",
        "/usr/share/bootlogo_wait.mvi"
    ]
    
    # Backup existing original bootlogos (only if backup doesn't exist yet)
    try:
        for path in target_paths:
            if os.path.exists(path):
                backup_path = path + ".backup"
                if not os.path.exists(backup_path):
                    shutil.copy2(path, backup_path)
    except Exception as e:
        print("[CiefpBootlogo] Backup creation error: " + str(e))
    
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

def restore_backup():
    """Restore backup bootlogos if they exist"""
    target_paths = [
        "/usr/share/bootlogo.mvi",
        "/usr/share/backdrop.mvi",
        "/usr/share/bootlogo_wait.mvi"
    ]
    
    restored = False
    try:
        for path in target_paths:
            backup_path = path + ".backup"
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, path)
                restored = True
        if restored:
            return True, "Original bootlogo backup restored successfully!"
        else:
            return False, "No backup files found to restore!"
    except Exception as e:
        return False, "Error restoring backup: " + str(e)

class CiefpBootlogoMain(Screen):
    def __init__(self, session):
        self.skin = MAIN_SKIN
        Screen.__init__(self, session)
        self.session = session
        self.temp_preview_path = None
        self.online_files_dict = {}
        self.current_source = "Online"
        self.loading = False
        self.local_mvi_files = []

        self.setup_actions()
        self.create_gui()
        
        self.onLayoutFinish.append(self.initial_load)

    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.apply_selected,
            "cancel": self.close,
            "red": self.close,
            "green": self.apply_selected,
            "yellow": self.ask_restore_backup,
            "blue": self.change_source,
            "up": self.move_up,
            "down": self.move_down
        }, -1)

    def create_gui(self):
        self["filelist"] = MenuList([])
        self["filelist"].onSelectionChanged.append(self.on_selection_changed)
        
        self["plugin_title"] = Label("..:: Ciefp Bootlogo - GitHub Source ::..")
        self["separator0"] = Label()
        self["preview"] = Pixmap()
        self["status"] = Label("Loading content from GitHub...")
        self["legend"] = Label("Red: Exit | Green/OK: Apply | Yellow: Restore Backup | Blue: Change Source")

    def initial_load(self):
        source = config.plugins.CiefpBootlogo.source.value
        if source == "Online":
            self.load_online_content()
        else:
            self.check_local_tmp_mvi()

    def show_placeholder(self):
        try:
            placeholder_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpBootlogo/placeholder.png"
            if fileExists(placeholder_path) and hasattr(self["preview"], 'instance') and self["preview"].instance:
                self["preview"].instance.setPixmapFromFile(placeholder_path)
                self["preview"].instance.setScale(1)
        except Exception as e:
            print("[CiefpBootlogo] Placeholder error: " + str(e))

    def load_online_content(self):
        if self.loading:
            return
            
        self.loading = True
        self.show_placeholder()
        self["status"].setText("Loading from GitHub...")
        self.current_source = "Online"
        self["plugin_title"].setText("..:: Ciefp Bootlogo - GitHub Source ::..")
        
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
        finally:
            self.loading = False

    def on_selection_changed(self):
        if self.current_source == "Online":
            self.preview_online_image()

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

    def apply_selected(self):
        if self.current_source == "Online":
            self.download_online_mvi()
        else:
            self.apply_local_mvi()

    def download_online_mvi(self):
        file_name = self["filelist"].getCurrent()
        if not file_name or file_name not in self.online_files_dict:
            self.session.open(MessageBox, "Please select an image first!", MessageBox.TYPE_ERROR)
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

    def ask_restore_backup(self):
        msg = "Are you sure you want to restore the original backup bootlogo?"
        self.session.openWithCallback(self.confirm_restore, MessageBox, msg, MessageBox.TYPE_YESNO)

    def confirm_restore(self, answer):
        if answer:
            success, msg = restore_backup()
            if success:
                self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                self["status"].setText("Original backup restored")
            else:
                self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)

    def change_source(self):
        choices = [
            ("Online", "Online Source (GitHub)"),
            ("Local", "Local Source (/tmp)")
        ]
        self.session.openWithCallback(self.source_selected, ChoiceBox, title="Select Source", list=choices)

    def source_selected(self, choice):
        if not choice:
            return
            
        source = choice[0]
        config.plugins.CiefpBootlogo.source.value = source
        config.plugins.CiefpBootlogo.source.save()
        config.save()
        
        if source == "Online":
            self.load_online_content()
        else:
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

        self.current_source = "Local"
        self["plugin_title"].setText("..:: Ciefp Bootlogo - Local Source (/tmp) ::..")
        
        if mvi_files:
            self["filelist"].setList(mvi_files)
            self.online_files_dict = {}
            self.show_placeholder()
            self["status"].setText("Found " + str(len(mvi_files)) + " local MVI file(s) in /tmp. Press Green/OK to apply.")
            self.local_mvi_files = mvi_files
        else:
            self["filelist"].setList([])
            self["status"].setText("No .mvi files found in /tmp folder.\nCopy your .mvi file to /tmp and select Source again.")
            self.show_placeholder()
            self.local_mvi_files = []

    def apply_local_mvi(self):
        file_name = self["filelist"].getCurrent()
        if not file_name:
            self.session.open(MessageBox, "No local MVI file selected or available!", MessageBox.TYPE_ERROR)
            return
            
        file_path = os.path.join("/tmp", file_name)
        
        if not fileExists(file_path):
            self.session.open(MessageBox, "Selected file not found in /tmp!", MessageBox.TYPE_ERROR)
            return
            
        success, msg = apply_bootlogo_mvi(file_path)
        if success:
            self.session.open(MessageBox, "Local bootlogo installed successfully!", MessageBox.TYPE_INFO)
            self["status"].setText("Applied local MVI: " + file_name)
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
            description="Download and apply Enigma2 bootlogo MVI images with backup restore",
            icon=PLUGIN_ICON,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]