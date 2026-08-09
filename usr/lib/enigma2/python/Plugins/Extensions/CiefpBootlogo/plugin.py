from enigma import eConsoleAppContainer, ePixmap, loadPic
from Components.ActionMap import ActionMap
from Components.config import config, ConfigText, ConfigSelection, ConfigSubsection
from Components.Pixmap import Pixmap
from Components.Sources.List import List
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
from .settings import CiefpBootlogoSettings

# Globalne varijable
PLUGIN_VERSION = "1.0"
PLUGIN_NAME = "CiefpBootlogo"
PLUGIN_ICON = "icon.png"

# Konfiguracija
config.plugins.CiefpBootlogo = ConfigSubsection()
config.plugins.CiefpBootlogo.resolution = ConfigSelection(default="FHD", choices=[("HD", "HD (1280x720)"), ("FHD", "FHD (1920x1080)"), ("UHD", "UHD (3840x2160)")])
config.plugins.CiefpBootlogo.source = ConfigSelection(default="Local", choices=[("Local", "Local"), ("Online", "Online")])
config.plugins.CiefpBootlogo.source_path = ConfigText(default="/tmp", visible_width=50)

class CiefpBootlogoMain(Screen):
    def __init__(self, session):
        self.skin = """
            <screen name="CiefpBootlogoMain" position="center,center" size="1920,1080" backgroundColor="#011a2e" flags="wfNoBorder">
                <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />  
                <widget name="plugin_title" position="0,10" size="1920,40" font="Bold;30" halign="center" backgroundColor="#010203" foregroundColor="#FFFFFF" text="..:: Ciefp Bootlogo ::.." />
                
                <widget name="description" position="50,100" size="1820,40" font="Regular;24" foregroundColor="#cccccc" backgroundColor="#0a0a1a" transparent="1" halign="center" />
                
                <widget name="filelist" position="50,160" size="580,800" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#1a1a2e" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" scrollbarMode="showOnDemand" itemHeight="40" enableWrapAround="1" borderWidth="2" borderColor="#003366" />
                
                <widget name="preview" position="660,160" size="1210,800" backgroundColor="#0a0a1a" borderWidth="3" borderColor="#003366" />
                
                <widget name="status" position="50,980" size="1820,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" />
                
                <widget name="legend" position="50,1030" size="1820,40" font="Regular;18" foregroundColor="#aaaaaa" backgroundColor="#0a0a1a" transparent="1" halign="center" />
            </screen>
        """

        Screen.__init__(self, session)

        self.session = session
        self.container = eConsoleAppContainer()
        self.selected_file = None
        self.file_list = []
        self.image_preview = None
        self.current_path = "/tmp"
        self.placeholder_shown = False
        self.temp_files = []
        self.current_preview = None

        # GUI setup
        self.setup_actions()
        self.create_gui()

        # ODLOŽI učitavanje dok GUI ne bude potpuno spreman
        self.onLayoutFinish.append(self.layout_finished)

    def layout_finished(self):
        self.load_files()

    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.convert_selected,
            "cancel": self.close,
            "red": self.close,
            "green": self.convert_selected,
            "yellow": self.open_settings,
            "blue": self.change_source,
            "up": self.move_up,
            "down": self.move_down,
            "left": self.move_left,
            "right": self.move_right
        }, -1)

    def create_gui(self):
        self["filelist"] = List([])
        self["filelist"].onSelectionChanged.append(self.preview_image)

        self["plugin_title"] = Label("..:: Ciefp Bootlogo ::..")
        self["separator0"] = Label()

        self["preview"] = Pixmap()
        self["status"] = Label("Pritisnite zeleno za konverziju")
        self["legend"] = Label("Crveno: Izlaz | Zeleno: Konvertuj | Žuto: Postavke | Plavo: Izvor")

    def show_placeholder(self):
        try:
            placeholder_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpBootlogo/placeholder.png"

            if not fileExists(placeholder_path):
                self.create_placeholder()

            if fileExists(placeholder_path):
                if hasattr(self["preview"], 'instance') and self["preview"].instance:
                    self["preview"].instance.setPixmapFromFile(placeholder_path)
                    self.placeholder_shown = True
                    self["status"].setText("Placeholder prikazan")
                    return

            self["status"].setText("Nema slika za prikaz")

        except Exception as e:
            print("[CiefpBootlogo] Greška pri prikazu placeholder-a: " + str(e))
            self["status"].setText("Greška: " + str(e))

    def create_placeholder(self):
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            width, height = 800, 450
            img = Image.new('RGB', (width, height), color='#0a0a1a')
            draw = ImageDraw.Draw(img)
            
            draw.rectangle([20, 20, width-20, height-20], outline='#003366', width=3)
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            title = "CIEFP BOOTLOGO"
            title_bbox = draw.textbbox((0, 0), title, font=font)
            title_width = title_bbox[2] - title_bbox[0]
            x = (width - title_width) // 2
            draw.text((x, height//2 - 60), title, fill='#ffffff', font=font)
            
            subtitle = "Nema slika za prikaz"
            sub_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
            sub_width = sub_bbox[2] - sub_bbox[0]
            x = (width - sub_width) // 2
            draw.text((x, height//2 + 20), subtitle, fill='#888888', font=font_small)
            
            info = "Dodajte slike u folder ili promijenite izvor"
            info_bbox = draw.textbbox((0, 0), info, font=font_small)
            info_width = info_bbox[2] - info_bbox[0]
            x = (width - info_width) // 2
            draw.text((x, height//2 + 70), info, fill='#555555', font=font_small)
            
            placeholder_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpBootlogo/placeholder.png"
            os.makedirs(os.path.dirname(placeholder_path), exist_ok=True)
            img.save(placeholder_path)
            print("[CiefpBootlogo] Placeholder kreiran: " + placeholder_path)
        except Exception as e:
            print("[CiefpBootlogo] Greška pri kreiranju placeholder-a: " + str(e))
            
    def load_files(self):
        path = config.plugins.CiefpBootlogo.source_path.value
        self.current_path = path
        
        if not pathExists(path):
            self["status"].setText("Putanja ne postoji: " + path)
            self.show_placeholder()
            return
            
        files = []
        try:
            for f in os.listdir(path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    files.append((f, f))
        except:
            pass
            
        self.file_list = files
        self["filelist"].setList(files)
        
        if len(files) == 0:
            self["status"].setText("Nema slika u " + path)
            self.show_placeholder()
        else:
            self["status"].setText("Pronađeno " + str(len(files)) + " slika u " + path)
            self.placeholder_shown = False
            self.preview_image()
        
    def preview_image(self):
        selection = self["filelist"].getCurrent()
        if not selection:
            if not self.placeholder_shown:
                self.show_placeholder()
            return
            
        file_name = selection[0]
        file_path = os.path.join(self.current_path, file_name)
        
        if not fileExists(file_path):
            self.show_placeholder()
            return
            
        try:
            self.cleanup_temp_files()
            img = Image.open(file_path)
            
            preview_width = 1200
            preview_height = 700
            img.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            img.save(temp_file.name, 'JPEG', quality=85)
            temp_file.close()
            
            self.temp_files.append(temp_file.name)
            success = False
            
            try:
                if hasattr(self["preview"], 'instance') and self["preview"].instance:
                    self["preview"].instance.setPixmapFromFile(temp_file.name)
                    success = True
            except:
                pass
                
            if not success:
                try:
                    from enigma import loadPic
                    pic = loadPic(temp_file.name)
                    if pic and hasattr(self["preview"], 'instance') and self["preview"].instance:
                        self["preview"].instance.setPixmap(pic)
                        success = True
                except:
                    pass
                    
            if not success:
                try:
                    self["preview"].setPixmap(temp_file.name)
                    success = True
                except:
                    pass
                    
            if success:
                self["status"].setText("Prikaz: " + file_name)
                self.placeholder_shown = False
            else:
                self["status"].setText("Ne može prikazati sliku, ali fajl postoji")
            
        except Exception as e:
            self["status"].setText("Greška pri prikazu: " + str(e))
            self.show_placeholder()
            
    def cleanup_temp_files(self):
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        self.temp_files = []
            
    def convert_selected(self):
        selection = self["filelist"].getCurrent()
        if not selection:
            self.session.open(MessageBox, "Nije odabrana slika!", MessageBox.TYPE_ERROR)
            return
            
        file_name = selection[0]
        file_path = os.path.join(self.current_path, file_name)
        
        if not fileExists(file_path):
            self.session.open(MessageBox, "Datoteka ne postoji!", MessageBox.TYPE_ERROR)
            return
            
        from .converter import convert_to_mvi
        success, message = convert_to_mvi(file_path, config.plugins.CiefpBootlogo.resolution.value)
        
        if success:
            self.session.open(MessageBox, "Konverzija uspješna!\n" + message, MessageBox.TYPE_INFO)
            self["status"].setText("Konverzija uspješna: " + file_name)
        else:
            self.session.open(MessageBox, "Greška pri konverziji:\n" + message, MessageBox.TYPE_ERROR)
            
    def move_up(self):
        self["filelist"].up()
        
    def move_down(self):
        self["filelist"].down()
        
    def move_left(self):
        pass
        
    def move_right(self):
        pass
        
    def open_settings(self):
        self.session.openWithCallback(self.settings_closed, CiefpBootlogoSettings)

    def settings_closed(self, *args):
        self.load_files()
        
    def change_source(self):
        choices = [
            ("Local", "Lokalni izvor"),
            ("Online", "Online izvor (GitHub)")
        ]
        self.session.openWithCallback(self.source_selected, ChoiceBox, title="Odaberite izvor", list=choices)
        
    def source_selected(self, choice):
        if not choice:
            return
            
        source = choice[0]
        if source == "Local":
            self.session.openWithCallback(self.settings_closed, CiefpBootlogoLocalSource)
        else:
            self.session.open(CiefpBootlogoOnlineSource)
            
    def refresh_files(self):
        self.load_files()
        
    def __onClose(self):
        self.cleanup_temp_files()

class CiefpBootlogoLocalSource(Screen):
    def __init__(self, session):
        self.skin = """
            <screen name="CiefpBootlogoLocalSource" position="center,center" size="960,540" title="Lokalni izvor" flags="wfNoBorder">
                <widget name="title" position="50,30" size="860,50" font="Regular;32" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" borderWidth="2" borderColor="#0055aa" />
                <widget name="drives" position="50,100" size="860,350" backgroundColor="#1a1a2e" foregroundColor="#ffffff" font="Regular;22" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" itemHeight="45" />
                <widget name="status" position="50,480" size="860,40" font="Regular;20" foregroundColor="#cccccc" backgroundColor="#0a0a1a" transparent="1" halign="center" />
            </screen>
        """
        
        Screen.__init__(self, session)
        self.session = session
        
        self.setup_title()
        self.setup_actions()
        self.create_gui()
        self.load_drives()
        
    def setup_title(self):
        self["title"] = Label("Odaberite lokalni izvor")
        
    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.select_path,
            "cancel": self.close,
            "red": self.close
        }, -1)
        
    def create_gui(self):
        self["drives"] = List([])
        self["status"] = Label("Odaberite disk ili folder")
        
    def load_drives(self):
        drives = [
            ("/tmp", "TMP folder"),
            ("/media/hdd", "HDD"),
            ("/media/usb", "USB"),
            ("/media/usb2", "USB 2"),
            ("/media/sda1", "USB sda1"),
            ("/media/sdb1", "USB sdb1")
        ]
        
        available_drives = []
        for path, name in drives:
            if pathExists(path):
                available_drives.append((path, name))
                
        self["drives"].setList(available_drives)
        self["status"].setText("Pronađeno " + str(len(available_drives)) + " diskova")
        
    def select_path(self):
        selection = self["drives"].getCurrent()
        if not selection:
            return
            
        path = selection[0]
        config.plugins.CiefpBootlogo.source_path.value = path
        config.plugins.CiefpBootlogo.source_path.save()
        config.save()
        self.close()
        
class CiefpBootlogoOnlineSource(Screen):
    def __init__(self, session):
        self.skin = """
            <screen name="CiefpBootlogoOnlineSource" position="center,center" size="1920,1080" title="Online izvor" flags="wfNoBorder">
                <widget name="title" position="50,30" size="1820,60" font="Regular;36" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" borderWidth="2" borderColor="#0055aa" />
                <widget name="filelist" position="50,110" size="580,800" font="Regular;22" backgroundColor="#1a1a2e" foregroundColor="#ffffff" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" itemHeight="40" borderWidth="2" borderColor="#003366" />
                <widget name="preview" position="660,110" size="1210,800" backgroundColor="#0a0a1a" borderWidth="3" borderColor="#003366" />
                <widget name="status" position="50,930" size="1820,40" font="Regular;20" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" />
            </screen>
        """
        
        Screen.__init__(self, session)
        self.session = session
        
        self.setup_title()
        self.setup_actions()
        self.create_gui()
        self.load_online_content()
        
    def setup_title(self):
        self["title"] = Label("Online izvor - GitHub")
        
    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.download_selected,
            "cancel": self.close,
            "red": self.close,
            "green": self.download_selected,
            "up": self.move_up,
            "down": self.move_down
        }, -1)
        
    def create_gui(self):
        self["filelist"] = List([])
        self["preview"] = Pixmap()
        self["status"] = Label("Učitavanje online sadržaja...")
        
    def load_online_content(self):
        github_url = "https://api.github.com/repos/username/bootlogos/contents/"
        
        try:
            response = requests.get(github_url, timeout=10)
            if response.status_code == 200:
                files = response.json()
                
                file_list = []
                for file in files:
                    if file['name'].lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_list.append((file['name'], file['download_url']))
                        
                self["filelist"].setList(file_list)
                self["status"].setText("Pronađeno " + str(len(file_list)) + " online slika")
            else:
                self["status"].setText("Greška pri dohvaćanju sadržaja")
        except Exception as e:
            self["status"].setText("Greška: " + str(e))
            
    def download_selected(self):
        selection = self["filelist"].getCurrent()
        if not selection:
            return
            
        file_name = selection[0]
        download_url = selection[1]
        
        try:
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                tmp_path = "/tmp/" + file_name
                with open(tmp_path, 'wb') as f:
                    f.write(response.content)
                    
                from .converter import convert_to_mvi
                success, message = convert_to_mvi(tmp_path, config.plugins.CiefpBootlogo.resolution.value)
                
                if success:
                    self.session.open(MessageBox, "Preuzimanje i konverzija uspješni!", MessageBox.TYPE_INFO)
                else:
                    self.session.open(MessageBox, "Greška pri konverziji:\n" + message, MessageBox.TYPE_ERROR)
            else:
                self.session.open(MessageBox, "Greška pri preuzimanju!", MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, "Greška: " + str(e), MessageBox.TYPE_ERROR)
            
    def move_up(self):
        self["filelist"].up()
        
    def move_down(self):
        self["filelist"].down()
        

def main(session, **kwargs):
    session.open(CiefpBootlogoMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="{0} v{1}".format(PLUGIN_NAME, PLUGIN_VERSION),
            description="Convert images to bootlogo mvi format",
            icon=PLUGIN_ICON,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]