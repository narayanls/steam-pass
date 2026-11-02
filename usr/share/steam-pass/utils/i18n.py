"""Traduções simples da interface.

Português (pt_BR / pt_PT / pt) para quem usa português; inglês para todos os
outros idiomas. O idioma é detectado pelas variáveis de ambiente padrão do
sistema (LANGUAGE, LC_ALL, LC_MESSAGES, LANG), na mesma ordem de prioridade
usada pelo gettext.
"""
import os

_STRINGS = {
    "pt": {
        "unknown": "Desconhecido",
        "remove_tooltip": "Remover conta da lista",
        "add_tooltip": "Adicionar nova conta",
        "no_users": "Nenhum usuário encontrado.",
        "remove_title": "Remover {account}?",
        "remove_body": "Isso removerá a conta da lista de login automático e das credenciais salvas.",
        "steam_running_title": "A Steam está rodando",
        "steam_running_switch": "Deseja fechar a Steam e trocar de usuário?",
        "steam_running_new": "Deseja fechar a Steam e fazer login em nova conta?",
        "integrate_title": "Integrar ao Sistema?",
        "integrate_body": "O Steam Pass está rodando como AppImage.\nDeseja adicionar um atalho ao menu de aplicativos?",
        "desktop_comment": "Gerenciador de contas Steam",
    },
    "en": {
        "unknown": "Unknown",
        "remove_tooltip": "Remove account from the list",
        "add_tooltip": "Add new account",
        "no_users": "No users found.",
        "remove_title": "Remove {account}?",
        "remove_body": "This will remove the account from the auto-login list and from the saved credentials.",
        "steam_running_title": "Steam is running",
        "steam_running_switch": "Do you want to close Steam and switch users?",
        "steam_running_new": "Do you want to close Steam and log in to a new account?",
        "integrate_title": "Integrate with the System?",
        "integrate_body": "Steam Pass is running as an AppImage.\nDo you want to add a shortcut to the applications menu?",
        "desktop_comment": "Steam account manager",
    },
}


def _detect_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if not value:
            continue
        # LANGUAGE pode ter uma lista ("pt_BR:en"); vale a primeira entrada
        first = value.split(":")[0].strip()
        if not first or first in ("C", "POSIX") or first.startswith("C."):
            continue
        return "pt" if first.lower().startswith("pt") else "en"
    return "en"


LANG = _detect_language()


def _(key, **kwargs):
    """Retorna o texto traduzido para a chave; aceita formatação com kwargs."""
    text = _STRINGS[LANG].get(key) or _STRINGS["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text
