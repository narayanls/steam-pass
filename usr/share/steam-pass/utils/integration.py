import os
import shutil
from pathlib import Path

# Configurações do Steam Pass
APP_ID = 'io.github.narayanls.steampass.app'
APP_NAME = 'Steam Pass'
ICON_NAME = 'io.github.narayanls.steampass.app' 

def is_running_as_appimage():
    """Verifica se está rodando via AppImage."""
    return 'APPIMAGE' in os.environ

def is_installed():
    """Verifica se o .desktop já existe."""
    desktop_file = Path.home() / ".local" / "share" / "applications" / f"{APP_ID}.desktop"
    return desktop_file.exists()

def install_appimage():
    try:
        appimage_path = os.environ.get('APPIMAGE')
        if not appimage_path:
            return False

        home = Path.home()
        current_dir = Path(__file__).parent.resolve()

        # Instalação do ícone
        possible_paths = [
            current_dir.parent / f"{ICON_NAME}.svg",
            current_dir.parent.parent.parent.parent / f"{ICON_NAME}.svg",
            current_dir.parent.parent / "icons" / "hicolor" / "scalable" / "apps" / f"{ICON_NAME}.svg"
        ]

        icon_src = None
        for p in possible_paths:
            if p.exists():
                icon_src = p
                break

        if icon_src:
            icon_dest = home / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
            icon_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy(icon_src, icon_dest / f"{APP_ID}.svg")

        # --- 2. Criação do .desktop ---
        apps_dir = home / ".local" / "share" / "applications"
        apps_dir.mkdir(parents=True, exist_ok=True)

        desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Gerenciador de contas Steam
Exec="{appimage_path}"
Icon={APP_ID}
Categories=Game;Utility;
Terminal=false
StartupWMClass={APP_ID}
X-AppImage-Version=1.0
"""
        target_file = apps_dir / f"{APP_ID}.desktop"
        with open(target_file, "w") as f:
            f.write(desktop_content)
        
        target_file.chmod(0o755)
        return True

    except Exception as e:
        print(f"Erro na integração: {e}")
        return False
