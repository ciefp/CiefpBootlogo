# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen, ConfigList

class CiefpBootlogoSettings(Screen, ConfigListScreen):
    def __init__(self, session):
        self.skin = """
            <screen name="CiefpBootlogoSettings" position="center,center" size="960,540" title="Postavke" flags="wfNoBorder">
                <widget name="title" position="50,30" size="860,50" font="Regular;32" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" halign="center" valign="center" borderWidth="2" borderColor="#0055aa" />
                <widget name="config" position="50,100" size="860,350" backgroundColor="#1a1a2e" foregroundColor="#ffffff" itemHeight="33" font="Regular;26" selectionBackgroundColor="#003366" selectionForegroundColor="#ffffff" />
                <widget name="status" position="50,480" size="860,40" font="Regular;20" foregroundColor="#cccccc" backgroundColor="#0a0a1a" transparent="1" halign="center" />
            </screen>
        """

        Screen.__init__(self, session)
        self.session = session

        # Priprema liste konfiguracionih stavki
        self.list = [
            getConfigListEntry("Rezolucija", config.plugins.CiefpBootlogo.resolution),
            getConfigListEntry("Putanja", config.plugins.CiefpBootlogo.source_path)
        ]

        # Inicijalizacija ConfigListScreen
        ConfigListScreen.__init__(self, self.list, session=self.session)

        # GUI elementi
        self["title"] = Label("Ciefp Bootlogo - Postavke")
        self["status"] = Label("OK / Zeleno: Sačuvaj | Izlaz / Crveno: Odustani")

        self.setup_actions()

    def setup_actions(self):
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.save_settings,
            "cancel": self.keyCancel,
            "red": self.keyCancel,
            "green": self.save_settings,
            "left": self.keyLeft,
            "right": self.keyRight
        }, -1)

    def save_settings(self):
        for item in self["config"].list:
            item[1].save()
        config.save()
        self.close()