#!/usr/bin/env python3
import sys
import os
import vdf
import subprocess
import gi
from pathlib import Path

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
        self.registry_path = self.steam_root / "registry.vdf"
        self.steam_exe = "steam" 

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
        if not self.registry_path.exists():
            print(f"registry.vdf não encontrado em: {self.registry_path}")
            return

        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)

            try:
                reg_steam = data['Registry']['HKCU']['Software']['Valve']['Steam']
                reg_steam['AutoLoginUser'] = account_name
                
                if not account_name:
                    reg_steam['RememberPassword'] = '0'
                else:
                    reg_steam['RememberPassword'] = '1'
                
                if 'AlreadyLoggedIn' in reg_steam:
                    reg_steam['AlreadyLoggedIn'] = '0'
                    
            except KeyError:
                print("Estrutura do registry.vdf inesperada.")
                return

            with open(self.registry_path, 'w', encoding='utf-8') as f:
                vdf.dump(data, f, pretty=True)
                
            print(f"Usuário definido para: '{account_name}'")
            
        except Exception as e:
            print(f"Erro ao escrever no registro: {e}")

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
        except Exception as e:
            print(f"Erro ao fechar Steam: {e}")


class UserRow(Gtk.Box):
    """Widget customizado para exibir um usuário na lista."""
    def __init__(self, user_data, icon_path):
        # Mudado para HORIZONTAL
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.user_data = user_data
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(10)
        self.set_margin_end(10)

        # 1. Ícone
        if icon_path and icon_path.exists():
            icon_img = Gtk.Image.new_from_file(str(icon_path))
        else:
            # Fallback para ícone do tema se o arquivo não existir
            icon_img = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
            
        icon_img.set_pixel_size(32)
        self.append(icon_img)

        # 2. Container de Texto (Vertical)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_valign(Gtk.Align.CENTER)

        # Nome de exibição (Persona)
        lbl_persona = Gtk.Label(label=user_data['PersonaName'])
        lbl_persona.set_halign(Gtk.Align.START)
        lbl_persona.add_css_class("title-4")

        # Nome da conta (AccountName)
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
        
        # Define o caminho do ícone relativo ao script atual
        script_dir = Path(__file__).parent.resolve()
        self.icon_path = script_dir / "icons/hicolor/scalable/status/avatar-default-symbolic.svg"

        # Container Principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        # Cabeçalho
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Lista de Usuários
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.connect("row-activated", self.on_row_activated)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.listbox)
        main_box.append(scrolled)

        # Container Inferior
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
            # Passamos o self.icon_path aqui
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
            GLib.timeout_add(1000, lambda: self.perform_switch(account_name))

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

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        try:
            self.manager = SteamManager()
            win = SteamPassWindow(self, self.manager)
            win.present()
        except FileNotFoundError as e:
            print(f"Erro fatal: {e}")
            self.quit()

if __name__ == "__main__":
    app = SteamPassApp()
    app.run(sys.argv)
