#!/usr/bin/env python3
import sys
import os
import vdf
import subprocess
import gi
import time
from pathlib import Path

# Importação da Integração
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.integration import is_running_as_appimage, is_installed, install_appimage

# Configuração do GTK4
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib

class SteamManager:
    """Gerencia a localização e modificação dos arquivos da Steam."""
    
    def __init__(self):
        self.steam_root = self._find_steam_root()
        if not self.steam_root:
            fallback = Path.home() / ".local" / "share" / "Steam"
            if fallback.exists():
                self.steam_root = fallback
            else:
                raise FileNotFoundError("Diretório da Steam não encontrado.")
            
        self.config_path = self.steam_root / "config" / "loginusers.vdf"
        self.steam_exe = "steam" 
        
        self.registry_file = None
        self.mode = "registry"

        if (self.steam_root / "registry.vdf").exists():
            self.registry_file = self.steam_root / "registry.vdf"
        elif (self.steam_root.parent / "registry.vdf").exists():
            self.registry_file = self.steam_root.parent / "registry.vdf"
        else:
            print("registry.vdf não encontrado. Usando config/config.vdf (Modo Moderno).")
            self.registry_file = self.steam_root / "config" / "config.vdf"
            self.mode = "config_store"

    def _find_steam_root(self):
        possible_paths = [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam"
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "config").exists():
                return path
        return None

    def _get_case_insensitive_dict(self, dictionary, key):
        for k in dictionary.keys():
            if k.lower() == key.lower():
                return dictionary[k]
        dictionary[key] = {}
        return dictionary[key]

    def get_users(self):
        if not self.config_path.exists():
            return []

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
            
            users_dict = data.get('users', {})
            users_list = []
            
            for steam_id, info in users_dict.items():
                users_list.append({
                    'steam_id': steam_id,
                    'AccountName': info.get('AccountName', 'Desconhecido'),
                    'PersonaName': info.get('PersonaName', 'Desconhecido'),
                    'Timestamp': info.get('Timestamp', '0')
                })
            
            users_list.sort(key=lambda x: x['Timestamp'], reverse=True)
            return users_list
        except Exception as e:
            print(f"Erro ao ler usuários: {e}")
            return []

    def set_active_user(self, account_name):
        if not self.registry_file or not self.registry_file.exists():
            print(f"Arquivo de configuração não encontrado: {self.registry_file}")
            if self.mode == "config_store":
                 self.registry_file.parent.mkdir(parents=True, exist_ok=True)
                 with open(self.registry_file, 'w') as f:
                     f.write('"InstallConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t}\n\t\t}\n\t}\n}')

        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = vdf.load(f)

            reg_steam = None

            if self.mode == "registry":
                try:
                    root = self._get_case_insensitive_dict(data, 'Registry')
                    hkcu = self._get_case_insensitive_dict(root, 'HKCU')
                    soft = self._get_case_insensitive_dict(hkcu, 'Software')
                    valve = self._get_case_insensitive_dict(soft, 'Valve')
                    reg_steam = self._get_case_insensitive_dict(valve, 'Steam')
                except Exception:
                    print("Erro estrutural no registry.vdf")
                    return

            else:
                try:
                    root = self._get_case_insensitive_dict(data, 'InstallConfigStore')
                    soft = self._get_case_insensitive_dict(root, 'Software')
                    valve = self._get_case_insensitive_dict(soft, 'Valve')
                    reg_steam = self._get_case_insensitive_dict(valve, 'Steam')
                except Exception:
                    print("Erro estrutural no config.vdf")
                    return

            if reg_steam is not None:
                reg_steam['AutoLoginUser'] = account_name
                
                if not account_name:
                    reg_steam['RememberPassword'] = '0'
                else:
                    reg_steam['RememberPassword'] = '1'
                
                found_already = False
                for k in list(reg_steam.keys()):
                    if k.lower() == 'alreadyloggedin':
                        reg_steam[k] = '0'
                        found_already = True
                if not found_already:
                    reg_steam['AlreadyLoggedIn'] = '0'

                with open(self.registry_file, 'w', encoding='utf-8') as f:
                    vdf.dump(data, f, pretty=True)
                    
                print(f"Sucesso: Usuário '{account_name}' definido em {self.registry_file}")
            
        except Exception as e:
            print(f"Erro ao escrever no arquivo de configuração: {e}")

    def reset_login(self):
        self.set_active_user("")

    def is_steam_running(self):
        try:
            subprocess.check_call(["pgrep", "-x", "steam"], stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def launch_steam(self):
        subprocess.Popen([self.steam_exe], start_new_session=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def kill_steam(self):
        try:
            subprocess.run(["pkill", "-x", "steam"], check=False)
            for _ in range(15):
                if not self.is_steam_running():
                    return
                time.sleep(0.2)
        except Exception as e:
            print(f"Erro ao fechar Steam: {e}")

class UserRow(Gtk.Box):
    def __init__(self, user_data, icon_path):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.user_data = user_data
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(10)
        self.set_margin_end(10)

        if icon_path and icon_path.exists():
            icon_img = Gtk.Image.new_from_file(str(icon_path))
        else:
            icon_img = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
            
        icon_img.set_pixel_size(32)
        self.append(icon_img)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_valign(Gtk.Align.CENTER)

        lbl_persona = Gtk.Label(label=user_data['PersonaName'])
        lbl_persona.set_halign(Gtk.Align.START)
        lbl_persona.add_css_class("title-4")

        lbl_account = Gtk.Label(label=user_data['AccountName'])
        lbl_account.set_halign(Gtk.Align.START)
        lbl_account.add_css_class("dim-label")

        text_box.append(lbl_persona)
        text_box.append(lbl_account)
        self.append(text_box)

class SteamPassWindow(Gtk.ApplicationWindow):
    def __init__(self, app, manager):
        super().__init__(application=app, title="Steam Pass")
        self.manager = manager
        self.set_default_size(300, 400)
        
        script_dir = Path(__file__).parent.resolve()
        self.icon_path = script_dir / "icons/hicolor/scalable/status/avatar-default-symbolic.svg"

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.connect("row-activated", self.on_row_activated)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.listbox)
        main_box.append(scrolled)

        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        action_box.set_margin_top(10)
        action_box.set_margin_bottom(10)
        action_box.set_margin_start(10)
        action_box.set_margin_end(10)
        
        btn_add = Gtk.Button(label="Adicionar Nova Conta")
        btn_add.add_css_class("suggested-action") 
        btn_add.connect("clicked", self.on_add_account_clicked)
        
        action_box.append(btn_add)
        main_box.append(action_box)

        self.load_users()

    def load_users(self):
        users = self.manager.get_users()
        if not users:
            lbl = Gtk.Label(label="Nenhum usuário encontrado.")
            lbl.set_margin_top(20)
            self.listbox.append(lbl)
            return

        for user in users:
            row = UserRow(user, self.icon_path)
            list_row = Gtk.ListBoxRow()
            list_row.set_child(row)
            list_row.user_data = user 
            self.listbox.append(list_row)

    def on_row_activated(self, listbox, row):
        if not hasattr(row, 'user_data'):
            return
            
        user = row.user_data
        account = user['AccountName']
        print(f"Selecionado: {account}")
        self.check_and_launch(account)

    def on_add_account_clicked(self, button):
        print("Solicitado: Nova Conta")
        self.check_and_launch("") 

    def check_and_launch(self, account_name):
        if self.manager.is_steam_running():
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="A Steam está rodando"
            )
            msg = "Deseja fechar a Steam e "
            msg += "trocar de usuário?" if account_name else "fazer login em nova conta?"
            dialog.format_secondary_text(msg)
            dialog.connect("response", self.on_dialog_response, account_name)
            dialog.present()
        else:
            self.perform_switch(account_name)

    def on_dialog_response(self, dialog, response_id, account_name):
        dialog.destroy()
        if response_id == Gtk.ResponseType.YES:
            self.manager.kill_steam()
            GLib.timeout_add(500, lambda: self.perform_switch(account_name))

    def perform_switch(self, account_name):
        if account_name:
            self.manager.set_active_user(account_name)
        else:
            self.manager.reset_login()
        self.manager.launch_steam()
        self.close()

class SteamPassApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.narayanls.steampass.app", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.manager = None
        self.win = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        try:
            self.manager = SteamManager()
            self.win = SteamPassWindow(self, self.manager)
            self.win.present()
            
            # Checagem de integração (apenas após janela criada)
            self.check_integration()
            
        except FileNotFoundError as e:
            print(f"Erro fatal: {e}")
            self.quit()

    def check_integration(self):
        """Verifica e oferece integração se for AppImage."""
        if is_running_as_appimage() and not is_installed():
            dialog = Gtk.MessageDialog(
                transient_for=self.win,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Integrar ao Sistema?"
            )
            dialog.format_secondary_text(
                "O Steam Pass está rodando como AppImage.\nDeseja adicionar um atalho ao menu de aplicativos?"
            )
            dialog.connect("response", self.on_integration_response)
            dialog.present()

    def on_integration_response(self, dialog, response_id):
        dialog.destroy()
        if response_id == Gtk.ResponseType.YES:
            if install_appimage():
                print("Integração concluída.")
            else:
                print("Falha na integração.")

if __name__ == "__main__":
    app = SteamPassApp()
    app.run(sys.argv)
