import base64
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from guessit import guessit
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import requests

if sys.platform == "win32":
    import ctypes
    import winreg
else:
    ctypes = None
    winreg = None

# ==========================================
#  SINGLE INSTANCE CONTROLE (MUTEX)
# ==========================================
def ensure_single_instance():
    """Zorgt ervoor dat CoreTrakt nooit dubbel geopend kan worden."""
    if not ctypes:
        return None
    try:
        mutex_name = "CoreTrakt_SingleInstance_Mutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        error_already_exists = 183
        if ctypes.windll.kernel32.GetLastError() == error_already_exists:
            ctypes.windll.user32.MessageBoxW(
                0,
                "CoreTrakt draait al actief op de achtergrond in het systeemvak (rechtsonder bij de klok).",
                "CoreTrakt",
                0x40 | 0x10000
            )
            sys.exit(0)
        return mutex
    except Exception:
        return None

# ==========================================
#  TRAKT CONFIGURATIE & THEMA
# ==========================================
DEFAULT_TRAKT_CLIENT_ID = "nOR71aPD0OVuVZy3ZTIC5z0gVUVBXyiI_EmsLy755Js"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config.json"
TOKEN_FILE = BASE_DIR / "trakt_token.json"
TRAKT_API_URL = "https://api.trakt.tv"
POLL_INTERVAL_SECONDS = 5

TRANSLATIONS = {
    "Nederlands": {
        "settings_title": "CoreTrakt - Instellingen",
        "tab_account": "Account & VLC",
        "tab_folders": "Gemonitorde Mappen",
        "tab_prefs": "Voorkeuren",
        "save_only": "Opslaan",
        "save_close": "Opslaan & Sluiten",
        "cancel": "Sluiten",
        "saved_feedback": "✓ Opgeslagen!",
        "trakt_section": "Trakt.tv Account",
        "status_conn": "Verbonden met Trakt",
        "status_disc": "Niet verbonden",
        "btn_connect": "Verbind met Trakt",
        "btn_disconnect": "Ontkoppel Account",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC Mediaspeler",
        "vlc_auto_ok": "VLC Web Interface: Automatisch Geconfigureerd (Gereed)",
        "vlc_auto_fail": "VLC Web Interface: Niet Geconfigureerd",
        "btn_vlc_fix": "VLC Nu Configureren",
        "btn_open_vlc": "VLC Starten ▶",
        "folder_desc": "Alleen bestanden in deze mappen worden gescrobbled naar Trakt.\nAls deze lijst leeg is, wordt alle afgespeelde media gevolgd.",
        "add_folder": "+ Map Toevoegen",
        "no_folders": "Geen mappen ingesteld (alle media wordt gescrobbled)",
        "startup": "Automatisch opstarten met Windows",
        "notify": "Bureaubladmeldingen bij scrobblen",
        "tray_cust": "Systeemvak Icoon Aanpassen",
        "tray_desc": "Kies een aangepaste afbeelding (.ico, .png) of behoud het standaardicoon:",
        "browse": "Bladeren...",
        "reset": "Herstellen",
        "language": "Interfacetaal:",
        "running_in_tray": "CoreTrakt blijft actief op de achtergrond in het systeemvak."
    },
    "English": {
        "settings_title": "CoreTrakt - Settings",
        "tab_account": "Account & VLC",
        "tab_folders": "Monitored Folders",
        "tab_prefs": "Preferences",
        "save_only": "Save",
        "save_close": "Save & Close",
        "cancel": "Close",
        "saved_feedback": "✓ Saved!",
        "trakt_section": "Trakt.tv Account",
        "status_conn": "Connected to Trakt",
        "status_disc": "Not Connected",
        "btn_connect": "Connect with Trakt",
        "btn_disconnect": "Disconnect Account",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC Media Player",
        "vlc_auto_ok": "VLC Web Interface: Auto-Configured (Ready)",
        "vlc_auto_fail": "VLC Web Interface: Not Configured",
        "btn_vlc_fix": "Configure VLC Now",
        "btn_open_vlc": "Launch VLC ▶",
        "folder_desc": "Only media inside these directories will be scrobbled to Trakt.\nIf empty, all videos played in VLC will be tracked.",
        "add_folder": "+ Add Folder",
        "no_folders": "No folders configured (all media will be tracked)",
        "startup": "Start automatically on Windows boot",
        "notify": "Desktop notifications on scrobble",
        "tray_cust": "Tray Icon Customization",
        "tray_desc": "Choose an image file (.ico, .png) or keep the embedded app icon:",
        "browse": "Browse...",
        "reset": "Reset to Default",
        "language": "Interface Language:",
        "running_in_tray": "CoreTrakt remains active in the system tray."
    },
    "Español": {
        "settings_title": "CoreTrakt - Configuración",
        "tab_account": "Cuenta y VLC",
        "tab_folders": "Carpetas Monitorizadas",
        "tab_prefs": "Preferencias",
        "save_only": "Guardar",
        "save_close": "Guardar y Cerrar",
        "cancel": "Cerrar",
        "saved_feedback": "✓ ¡Guardado!",
        "trakt_section": "Cuenta de Trakt.tv",
        "status_conn": "Conectado a Trakt",
        "status_disc": "No conectado",
        "btn_connect": "Conectar con Trakt",
        "btn_disconnect": "Desconectar Cuenta",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "Reproductor VLC",
        "vlc_auto_ok": "Interfaz Web VLC: Configurada Automáticamente (Listo)",
        "vlc_auto_fail": "Interfaz Web VLC: No Configurada",
        "btn_vlc_fix": "Configurar VLC Ahora",
        "btn_open_vlc": "Iniciar VLC ▶",
        "folder_desc": "Solo se sincronizarán los archivos de estas carpetas.\nSi está vacía, se rastreará todo lo reproducido en VLC.",
        "add_folder": "+ Añadir Carpeta",
        "no_folders": "No hay carpetas configuradas (se rastrea todo)",
        "startup": "Iniciar automáticamente con Windows",
        "notify": "Notificaciones de escritorio al scrobblear",
        "tray_cust": "Personalizar Icono de Bandeja",
        "tray_desc": "Elige una imagen personalizada (.ico, .png) o mantén el icono predeterminado:",
        "browse": "Examinar...",
        "reset": "Restablecer",
        "language": "Idioma de interfaz:",
        "running_in_tray": "CoreTrakt sigue activo en la bandeja del sistema."
    },
    "Français": {
        "settings_title": "CoreTrakt - Paramètres",
        "tab_account": "Compte & VLC",
        "tab_folders": "Dossiers Surveillés",
        "tab_prefs": "Préférences",
        "save_only": "Enregistrer",
        "save_close": "Enregistrer & Fermer",
        "cancel": "Fermer",
        "saved_feedback": "✓ Enregistré !",
        "trakt_section": "Compte Trakt.tv",
        "status_conn": "Connecté à Trakt",
        "status_disc": "Non connecté",
        "btn_connect": "Se Connecter à Trakt",
        "btn_disconnect": "Déconnecter le Compte",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "Lecteur VLC",
        "vlc_auto_ok": "Interface Web VLC : Configurée Automatiquement (Prêt)",
        "vlc_auto_fail": "Interface Web VLC : Non Configurée",
        "btn_vlc_fix": "Configurer VLC Maintenant",
        "btn_open_vlc": "Lancer VLC ▶",
        "folder_desc": "Seuls les fichiers de ces dossiers seront scrobblés vers Trakt.\nSi la liste est vide, tous les médias lus dans VLC seront suivis.",
        "add_folder": "+ Ajouter un Dossier",
        "no_folders": "Aucun dossier configuré (tous les médias sont suivis)",
        "startup": "Démarrer automatiquement avec Windows",
        "notify": "Notifications de bureau lors du scrobble",
        "tray_cust": "Personnalisation de l'icône",
        "tray_desc": "Choisissez une image (.ico, .png) ou conservez l'icône par défaut :",
        "browse": "Parcourir...",
        "reset": "Réinitialiser",
        "language": "Langue de l'interface :",
        "running_in_tray": "CoreTrakt reste actif dans la barre d'état système."
    },
    "Deutsch": {
        "settings_title": "CoreTrakt - Einstellungen",
        "tab_account": "Konto & VLC",
        "tab_folders": "Überwachte Ordner",
        "tab_prefs": "Einstellungen",
        "save_only": "Speichern",
        "save_close": "Speichern & Schließen",
        "cancel": "Schließen",
        "saved_feedback": "✓ Gespeichert!",
        "trakt_section": "Trakt.tv-Konto",
        "status_conn": "Mit Trakt verbunden",
        "status_disc": "Nicht verbunden",
        "btn_connect": "Mit Trakt verbinden",
        "btn_disconnect": "Konto trennen",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC Media Player",
        "vlc_auto_ok": "VLC-Webinterface: Automatisch konfiguriert (Bereit)",
        "vlc_auto_fail": "VLC-Webinterface: Nicht konfiguriert",
        "btn_vlc_fix": "VLC jetzt konfigurieren",
        "btn_open_vlc": "VLC starten ▶",
        "folder_desc": "Nur Dateien in diesen Ordnern werden zu Trakt gescrobbelt.\nIst die Liste leer, werden alle in VLC abgespielten Medien erfasst.",
        "add_folder": "+ Ordner hinzufügen",
        "no_folders": "Keine Ordner konfiguriert (alle Medien werden erfasst)",
        "startup": "Automatisch mit Windows starten",
        "notify": "Desktop-Benachrichtigungen beim Scrobbeln",
        "tray_cust": "Tray-Symbol anpassen",
        "tray_desc": "Wählen Sie ein Bild (.ico, .png) oder behalten Sie das Standard-Symbol:",
        "browse": "Durchsuchen...",
        "reset": "Zurücksetzen",
        "language": "Oberflächensprache:",
        "running_in_tray": "CoreTrakt bleibt im Infobereich aktiv."
    },
    "Português": {
        "settings_title": "CoreTrakt - Configurações",
        "tab_account": "Conta & VLC",
        "tab_folders": "Pastas Monitoradas",
        "tab_prefs": "Preferências",
        "save_only": "Salvar",
        "save_close": "Salvar & Fechar",
        "cancel": "Fechar",
        "saved_feedback": "✓ Salvo!",
        "trakt_section": "Conta Trakt.tv",
        "status_conn": "Conectado ao Trakt",
        "status_disc": "Não conectado",
        "btn_connect": "Conectar ao Trakt",
        "btn_disconnect": "Desconectar Conta",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "Reprodutor VLC",
        "vlc_auto_ok": "Interface Web VLC: Configurada Automaticamente (Pronto)",
        "vlc_auto_fail": "Interface Web VLC: Não Configurada",
        "btn_vlc_fix": "Configurar VLC Agora",
        "btn_open_vlc": "Iniciar VLC ▶",
        "folder_desc": "Apenas arquivos nestas pastas serão sincronizados com o Trakt.\nSe a lista estiver vazia, todas as mídias no VLC serão rastreadas.",
        "add_folder": "+ Adicionar Pasta",
        "no_folders": "Nenhuma pasta configurada (todas as mídias são rastreadas)",
        "startup": "Iniciar automaticamente com o Windows",
        "notify": "Notificações na área de trabalho ao scrobbler",
        "tray_cust": "Personalizar Ícone da Barra",
        "tray_desc": "Escolha uma imagem (.ico, .png) ou mantenha o ícone padrão:",
        "browse": "Procurar...",
        "reset": "Redefinir",
        "language": "Idioma da interface:",
        "running_in_tray": "CoreTrakt permanece ativo na bandeja do sistema."
    },
    "Русский": {
        "settings_title": "CoreTrakt - Настройки",
        "tab_account": "Аккаунт и VLC",
        "tab_folders": "Отслеживаемые папки",
        "tab_prefs": "Настройки",
        "save_only": "Сохранить",
        "save_close": "Сохранить и закрыть",
        "cancel": "Закрыть",
        "saved_feedback": "✓ Сохранено!",
        "trakt_section": "Аккаунт Trakt.tv",
        "status_conn": "Подключено к Trakt",
        "status_disc": "Не подключено",
        "btn_connect": "Подключить Trakt",
        "btn_disconnect": "Отключить аккаунт",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "Медиаплеер VLC",
        "vlc_auto_ok": "Веб-интерфейс VLC: Настроен автоматически (Готово)",
        "vlc_auto_fail": "Веб-интерфейс VLC: Не настроен",
        "btn_vlc_fix": "Настроить VLC сейчас",
        "btn_open_vlc": "Запустить VLC ▶",
        "folder_desc": "Скробблинг будет выполняться только для файлов из этих папок.\nЕсли список пуст, отслеживается всё воспроизводимое в VLC видео.",
        "add_folder": "+ Добавить папку",
        "no_folders": "Папки не выбраны (отслеживаются все файлы)",
        "startup": "Автозапуск вместе с Windows",
        "notify": "Уведомления на рабочем столе при скробблинге",
        "tray_cust": "Настройка значка в трее",
        "tray_desc": "Выберите изображение (.ico, .png) или оставьте стандартный значок:",
        "browse": "Обзор...",
        "reset": "Сбросить",
        "language": "Язык интерфейса:",
        "running_in_tray": "CoreTrakt продолжает работать в системном трее."
    },
    "中文": {
        "settings_title": "CoreTrakt - 设置",
        "tab_account": "账户与 VLC",
        "tab_folders": "监控文件夹",
        "tab_prefs": "偏好设置",
        "save_only": "保存",
        "save_close": "保存并关闭",
        "cancel": "关闭",
        "saved_feedback": "✓ 已保存！",
        "trakt_section": "Trakt.tv 账户",
        "status_conn": "已连接到 Trakt",
        "status_disc": "未连接",
        "btn_connect": "连接到 Trakt",
        "btn_disconnect": "断开账户",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC 播放器",
        "vlc_auto_ok": "VLC Web 接口：已自动配置 (就绪)",
        "vlc_auto_fail": "VLC Web 接口：未配置",
        "btn_vlc_fix": "立即自动配置 VLC",
        "btn_open_vlc": "启动 VLC ▶",
        "folder_desc": "只有这些文件夹中的媒体文件才会同步到 Trakt。\n若列表为空，则记录 VLC 播放的所有媒体。",
        "add_folder": "+ 添加文件夹",
        "no_folders": "未设置文件夹（将记录所有媒体）",
        "startup": "随 Windows 自动启动",
        "notify": "Scrobble 时显示桌面通知",
        "tray_cust": "自定义托盘图标",
        "tray_desc": "选择图像文件 (.ico, .png) 或保留默认图标：",
        "browse": "浏览...",
        "reset": "重置",
        "language": "界面语言：",
        "running_in_tray": "CoreTrakt 继续在系统托盘后台运行。"
    },
    "日本語": {
        "settings_title": "CoreTrakt - 設定",
        "tab_account": "アカウント & VLC",
        "tab_folders": "監視フォルダー",
        "tab_prefs": "設定",
        "save_only": "保存",
        "save_close": "保存して閉じる",
        "cancel": "閉じる",
        "saved_feedback": "✓ 保存しました！",
        "trakt_section": "Trakt.tv アカウント",
        "status_conn": "Trakt に接続済み",
        "status_disc": "未接続",
        "btn_connect": "Trakt に接続",
        "btn_disconnect": "アカウントを切断",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC メディアプレイヤー",
        "vlc_auto_ok": "VLC Webインターフェース：自動設定済み (準備完了)",
        "vlc_auto_fail": "VLC Webインターフェース：未設定",
        "btn_vlc_fix": "今すぐ VLC を自動設定",
        "btn_open_vlc": "VLC を起動 ▶",
        "folder_desc": "これらのフォルダー内のメディアファイルのみが Trakt に記録されます。\n空の場合は、VLC で再生されたすべての動画が対象になります。",
        "add_folder": "+ フォルダーを追加",
        "no_folders": "フォルダー未設定 (すべての動画を記録)",
        "startup": "Windows 起動時に自動開始",
        "notify": "スクロブル時にデスクトップ通知を表示",
        "tray_cust": "トレイアイコンのカスタマイズ",
        "tray_desc": "画像ファイル (.ico, .png) を選択するか、デフォルトを維持：",
        "browse": "参照...",
        "reset": "リセット",
        "language": "インターフェース言語：",
        "running_in_tray": "CoreTrakt はシステムトレイで引き続き実行されます。"
    },
    "हिन्दी": {
        "settings_title": "CoreTrakt - सेटिंग्स",
        "tab_account": "खाता और VLC",
        "tab_folders": "निगरानी वाले फ़ोल्डर",
        "tab_prefs": "प्राथमिकताएं",
        "save_only": "सहेजें",
        "save_close": "सहेजें और बंद करें",
        "cancel": "बंद करें",
        "saved_feedback": "✓ सहेजा गया!",
        "trakt_section": "Trakt.tv खाता",
        "status_conn": "Trakt से जुड़ा हुआ",
        "status_disc": "जुड़ा नहीं है",
        "btn_connect": "Trakt से जुड़ें",
        "btn_disconnect": "खाता डिस्कनेक्ट करें",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "VLC मीडिया प्लेयर",
        "vlc_auto_ok": "VLC वेब इंटरफ़ेस: स्वचालित कॉन्फ़िगर (तैयार)",
        "vlc_auto_fail": "VLC वेब इंटरफ़ेस: कॉन्फ़िगर नहीं है",
        "btn_vlc_fix": "VLC अभी कॉन्फ़िगर करें",
        "btn_open_vlc": "VLC शुरू करें ▶",
        "folder_desc": "केवल इन फ़ोल्डरों की मीडिया फाइलें Trakt पर स्क्रॉबल होंगी।\nयदि सूची खाली है, तो VLC में चलने वाली सभी मीडिया ट्रैक की जाएगी।",
        "add_folder": "+ फ़ोल्डर जोड़ें",
        "no_folders": "कोई फ़ोल्डर सेट नहीं है (सभी मीडिया ट्रैक किए जाएंगे)",
        "startup": "Windows के साथ स्वचालित रूप से प्रारंभ करें",
        "notify": "स्क्रॉबल पर डेस्कटॉप सूचनाएं दिखाएं",
        "tray_cust": "ट्रे आइकन अनुकूलित करें",
        "tray_desc": "छवि (.ico, .png) चुनें या डिफ़ॉल्ट आइकन रखें:",
        "browse": "ब्राउज़ करें...",
        "reset": "रीसेट करें",
        "language": "इंटरफ़ेस भाषा:",
        "running_in_tray": "CoreTrakt सिस्टम ट्रे में सक्रिय रहेगा।"
    },
    "العربية": {
        "settings_title": "CoreTrakt - الإعدادات",
        "tab_account": "الحساب و VLC",
        "tab_folders": "المجلدات المراقبة",
        "tab_prefs": "التفضيلات",
        "save_only": "حفظ",
        "save_close": "حفظ وإغلاق",
        "cancel": "إغلاق",
        "saved_feedback": "✓ تم الحفظ!",
        "trakt_section": "حساب Trakt.tv",
        "status_conn": "متصل بـ Trakt",
        "status_disc": "غير متصل",
        "btn_connect": "الاتصال بـ Trakt",
        "btn_disconnect": "فصل الحساب",
        "btn_open_trakt": "Trakt.tv ↗",
        "vlc_section": "مشغل الوسائط VLC",
        "vlc_auto_ok": "واجهة ويب VLC: تم التكوين تلقائيًا (جاهز)",
        "vlc_auto_fail": "واجهة ويب VLC: غير مكونة",
        "btn_vlc_fix": "تكوين VLC الآن",
        "btn_open_vlc": "تشغيل VLC ▶",
        "folder_desc": "سيتم تتبع الوسائط الموجودة داخل هذه المجلدات فقط على Trakt.\nإذا كانت القائمة فارغة، فسيتم تتبع جميع الوسائط المشغلة في VLC.",
        "add_folder": "+ إضافة مجلد",
        "no_folders": "لم يتم تعيين مجلدات (يتم تتبع جميع الوسائط)",
        "startup": "التشغيل تلقائيًا مع بدء تشغيل Windows",
        "notify": "إشعارات سطح المكتب عند التتبع",
        "tray_cust": "تخصيص أيقونة شريط المهام",
        "tray_desc": "اختر صورة (.ico, .png) أو احتفظ بالأيقونة الافتراضية:",
        "browse": "تصفح...",
        "reset": "إعادة ضبط",
        "language": "لغة الواجهة:",
        "running_in_tray": "سيبقى CoreTrakt قيد التشغيل في شريط المهام."
    }
}


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return BASE_DIR / relative_path


class VLCConfigManager:
    DEFAULT_PASS = "conetrakt"

    @staticmethod
    def get_vlcrc_path() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "vlc" / "vlcrc"
        return Path.home() / "AppData" / "Roaming" / "vlc" / "vlcrc"

    @classmethod
    def get_or_setup_vlc(cls):
        vlcrc = cls.get_vlcrc_path()
        if not vlcrc.parent.exists():
            try:
                vlcrc.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        if not vlcrc.exists():
            try:
                with open(vlcrc, "w", encoding="utf-8") as f:
                    f.write("[main]\nextraintf=http\n\n[lua]\nhttp-password=conetrakt\n")
                return cls.DEFAULT_PASS, True
            except Exception:
                return cls.DEFAULT_PASS, False

        try:
            with open(vlcrc, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return cls.DEFAULT_PASS, False

        existing_pwd = None
        has_http_intf = False
        pwd_line_idx = -1
        extraintf_line_idx = -1

        for idx, line in enumerate(lines):
            s = line.strip()
            if s.startswith("http-password=") and not s.startswith("#"):
                parts = s.split("=", 1)
                if len(parts) > 1 and parts[1].strip():
                    existing_pwd = parts[1].strip()
            elif s.startswith("#http-password=") or s == "http-password=":
                if pwd_line_idx == -1:
                    pwd_line_idx = idx

            if s.startswith("extraintf=") and not s.startswith("#"):
                extraintf_line_idx = idx
                if "http" in s:
                    has_http_intf = True
            elif s.startswith("#extraintf="):
                if extraintf_line_idx == -1:
                    extraintf_line_idx = idx

        if existing_pwd and has_http_intf:
            return existing_pwd, True

        pwd_to_use = existing_pwd if existing_pwd else cls.DEFAULT_PASS
        modified = False

        if not existing_pwd:
            if pwd_line_idx != -1:
                lines[pwd_line_idx] = f"http-password={pwd_to_use}\n"
                modified = True
            else:
                lines.append(f"\n[lua]\nhttp-password={pwd_to_use}\n")
                modified = True

        if not has_http_intf:
            if extraintf_line_idx != -1:
                orig = lines[extraintf_line_idx].strip()
                if orig.startswith("#extraintf="):
                    lines[extraintf_line_idx] = "extraintf=http\n"
                elif orig.startswith("extraintf="):
                    val = orig.split("=", 1)[1].strip()
                    lines[extraintf_line_idx] = f"extraintf={val},http\n" if val else "extraintf=http\n"
                modified = True
            else:
                lines.append("\n[main]\nextraintf=http\n")
                modified = True

        if modified:
            try:
                with open(vlcrc, "w", encoding="utf-8", errors="ignore") as f:
                    f.writelines(lines)
            except Exception:
                return pwd_to_use, False

        return pwd_to_use, True


class ConfigManager:
    DEFAULT_CONFIG = {
        "vlc_host": "http://localhost:8080",
        "vlc_password": "conetrakt",
        "folders": [],
        "run_on_startup": False,
        "show_notifications": True,
        "custom_icon_path": "",
        "language": "Nederlands"
    }

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lock = threading.RLock()
        self.data = self.load()

    def load(self) -> dict:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = self.DEFAULT_CONFIG.copy()
                    merged.update(cfg)
                    return merged
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()

    def _save_unlocked(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[CoreTrakt] Error saving config: {e}")

    def save(self):
        with self.lock:
            self._save_unlocked()

    def get(self, key, default=None):
        with self.lock:
            return self.data.get(key, default)

    def set(self, key, value):
        with self.lock:
            self.data[key] = value
            self._save_unlocked()


def set_windows_startup(enable: bool):
    """Beheert de Windows Run registersleutel en ruimt oude aliassen op."""
    if not winreg:
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "CoreTrakt"
    legacy_names = ["ConeTrakt", "VLC_Trakt_Scrobbler", "vlc_trakt_tray"]
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        # Ruim te allen tijde oude restanten op om dubbele starts te voorkomen
        for old in legacy_names:
            try:
                winreg.DeleteValue(key, old)
            except FileNotFoundError:
                pass

        if enable:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}"'
            else:
                cmd = f'"{sys.executable}" "{Path(__file__).resolve()}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[CoreTrakt] Startup Registry Error: {e}")


def create_fallback_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg_color = (237, 28, 36, 255)
    corner_radius = int(size * 0.22)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=corner_radius, fill=bg_color)
    white = (255, 255, 255, 255)
    bar_thick = max(2, int(size * 0.16))
    draw.rectangle([(int(size * 0.20), int(size * 0.22)), (int(size * 0.80), int(size * 0.22) + bar_thick)], fill=white)
    stem_x0 = int(size * 0.5) - (bar_thick // 2)
    draw.rectangle([(stem_x0, int(size * 0.22) + bar_thick), (stem_x0 + bar_thick, int(size * 0.78))], fill=white)
    return img


def get_application_icon(custom_path: str = "") -> Image.Image:
    if custom_path and os.path.exists(custom_path):
        try:
            return Image.open(custom_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        except Exception:
            pass

    for filename in ("app_icon.ico", "logo.png"):
        candidate = get_resource_path(filename)
        if candidate.exists():
            try:
                return Image.open(candidate).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

    return create_fallback_icon(64)


class TraktClient:
    def __init__(self, config: ConfigManager, token_path: Path):
        self.config = config
        self.token_path = token_path
        self.token = self._load_token()
        self._search_cache = {}

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": DEFAULT_TRAKT_CLIENT_ID,
        }
        if self.token and "access_token" in self.token:
            headers["Authorization"] = f"Bearer {self.token['access_token']}"
        return headers

    def _load_token(self):
        if self.token_path.exists():
            try:
                with open(self.token_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_token(self, token_data):
        self.token = token_data
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

    def clear_token(self):
        self.token = None
        if self.token_path.exists():
            try:
                self.token_path.unlink()
            except Exception:
                pass

    def is_authenticated(self) -> bool:
        return bool(self.token and "access_token" in self.token)

    def refresh_token_if_needed(self):
        if not self.token or "refresh_token" not in self.token:
            return
        created_at = self.token.get("created_at", 0)
        expires_in = self.token.get("expires_in", 7776000)
        if time.time() > (created_at + expires_in - 172800):
            payload = {
                "refresh_token": self.token["refresh_token"],
                "client_id": DEFAULT_TRAKT_CLIENT_ID,
                "grant_type": "refresh_token",
            }
            try:
                res = requests.post(f"{TRAKT_API_URL}/oauth/token", json=payload, timeout=10)
                if res.status_code == 200:
                    self.save_token(res.json())
            except Exception:
                pass

    def resolve_media_ids(self, media_type: str, title: str, year: int = None):
        """Vindt het officiële Trakt ID via de Trakt Search API."""
        cache_key = (media_type, title.strip().lower(), year)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        search_type = "show" if media_type == "episode" else "movie"
        params = {"query": title}
        if year:
            params["years"] = str(year)

        try:
            url = f"{TRAKT_API_URL}/search/{search_type}"
            res = requests.get(url, params=params, headers=self._headers(), timeout=5)
            if res.status_code == 200:
                results = res.json()
                if not results and year:
                    res = requests.get(url, params={"query": title}, headers=self._headers(), timeout=5)
                    if res.status_code == 200:
                        results = res.json()

                if results and isinstance(results, list):
                    item_data = results[0].get(search_type, {})
                    resolved = {
                        "title": item_data.get("title", title),
                        "year": item_data.get("year", year),
                        "ids": item_data.get("ids", {}),
                    }
                    print(f"[CoreTrakt] Matched '{title}' -> '{resolved['title']}' (Trakt ID: {resolved['ids'].get('trakt')})")
                    self._search_cache[cache_key] = resolved
                    return resolved
        except Exception as e:
            print(f"[CoreTrakt] Search error for '{title}': {e}")

        fallback = {"title": title, "year": year, "ids": {}}
        self._search_cache[cache_key] = fallback
        return fallback

    def scrobble(self, action: str, media_info: dict, progress: float):
        if not self.is_authenticated():
            print(f"[CoreTrakt] Scrobble '{action}' skipped: Not authenticated.")
            return False

        resolved = self.resolve_media_ids(
            media_info["type"],
            media_info["title"],
            media_info.get("year"),
        )

        endpoint = f"{TRAKT_API_URL}/scrobble/{action}"
        payload = {"progress": round(progress, 2)}

        if media_info["type"] == "episode":
            payload["show"] = {
                "title": resolved.get("title", media_info["title"])
            }
            if resolved.get("ids"):
                payload["show"]["ids"] = resolved["ids"]
            elif resolved.get("year"):
                payload["show"]["year"] = int(resolved["year"])

            payload["episode"] = {
                "season": int(media_info.get("season", 1)),
                "number": int(media_info.get("episode", 1)),
            }
        else:
            payload["movie"] = {
                "title": resolved.get("title", media_info["title"])
            }
            if resolved.get("ids"):
                payload["movie"]["ids"] = resolved["ids"]
            elif resolved.get("year"):
                payload["movie"]["year"] = int(resolved["year"])

        try:
            print(f"[CoreTrakt] Scrobble '{action}' request: {payload}")
            res = requests.post(endpoint, json=payload, headers=self._headers(), timeout=8)
            print(f"[CoreTrakt] Trakt response ({res.status_code}): {res.text.strip()}")
            return res.status_code in [200, 201]
        except Exception as e:
            print(f"[CoreTrakt] Scrobble network error: {e}")
            return False


# ==========================================
#  MODERNE CUSTOMTKINTER GUI
# ==========================================
class SettingsGUI:
    _is_open = False

    def __init__(self, config: ConfigManager, trakt: TraktClient, tray_app=None, on_save_callback=None):
        if SettingsGUI._is_open:
            return
        SettingsGUI._is_open = True

        self.config = config
        self.trakt = trakt
        self.tray_app = tray_app
        self.on_save_callback = on_save_callback

        self.folders = list(self.config.get("folders", []))
        self.lang = self.config.get("language", "Nederlands")
        if self.lang not in TRANSLATIONS:
            self.lang = "Nederlands"
        self.t = TRANSLATIONS[self.lang]

        print("[CoreTrakt] Opening Modern Settings GUI...")
        self.root = ctk.CTk()
        self.root.title(self.t["settings_title"])
        self.root.geometry("680x520")
        self.root.minsize(620, 480)

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)
        self.root.focus_force()

        self.var_startup = tk.BooleanVar(value=self.config.get("run_on_startup", False))
        self.var_notify = tk.BooleanVar(value=self.config.get("show_notifications", True))

        self._build_ui()
        print("[CoreTrakt] Settings GUI is ready.")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 5))

        self.tab_account = self.tabview.add(self.t["tab_account"])
        self.tab_folders = self.tabview.add(self.t["tab_folders"])
        self.tab_prefs = self.tabview.add(self.t["tab_prefs"])

        self._build_account_tab()
        self._build_folders_tab()
        self._build_prefs_tab()

        btn_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_bar.pack(fill="x", side="bottom", padx=15, pady=(5, 15))

        self.lbl_save_status = ctk.CTkLabel(btn_bar, text="", text_color="#2ecc71", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_save_status.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(
            btn_bar, text=self.t["cancel"], width=90, fg_color="transparent",
            border_width=1, border_color="#555555", hover_color="#333333", command=self._on_close
        )
        self.btn_cancel.pack(side="right", padx=(5, 0))

        self.btn_save_close = ctk.CTkButton(
            btn_bar, text=self.t["save_close"], width=130, command=self._save_and_close
        )
        self.btn_save_close.pack(side="right", padx=5)

        self.btn_save_only = ctk.CTkButton(
            btn_bar, text=self.t["save_only"], width=90, fg_color="#333333", hover_color="#444444", command=self._save_only
        )
        self.btn_save_only.pack(side="right", padx=5)

    def _build_account_tab(self):
        card_trakt = ctk.CTkFrame(self.tab_account, corner_radius=10)
        card_trakt.pack(fill="x", pady=(5, 12), padx=5)

        lbl_trakt_title = ctk.CTkLabel(card_trakt, text=self.t["trakt_section"], font=ctk.CTkFont(size=14, weight="bold"))
        lbl_trakt_title.pack(anchor="w", padx=15, pady=(12, 6))

        row_trakt = ctk.CTkFrame(card_trakt, fg_color="transparent")
        row_trakt.pack(fill="x", padx=15, pady=(0, 12))

        is_auth = self.trakt.is_authenticated()
        self.lbl_auth_status = ctk.CTkLabel(
            row_trakt,
            text=self.t["status_conn"] if is_auth else self.t["status_disc"],
            text_color="#2ecc71" if is_auth else "#e74c3c",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_auth_status.pack(side="left")

        btn_text = self.t["btn_disconnect"] if is_auth else self.t["btn_connect"]
        self.btn_auth = ctk.CTkButton(row_trakt, text=btn_text, command=self._toggle_trakt_auth, width=140)
        self.btn_auth.pack(side="right", padx=(5, 0))

        self.btn_open_trakt = ctk.CTkButton(
            row_trakt, text=self.t["btn_open_trakt"], width=95, fg_color="transparent",
            border_width=1, border_color="#555555", hover_color="#333333",
            command=lambda: webbrowser.open("https://trakt.tv")
        )
        self.btn_open_trakt.pack(side="right", padx=(0, 5))

        card_vlc = ctk.CTkFrame(self.tab_account, corner_radius=10)
        card_vlc.pack(fill="x", pady=6, padx=5)

        lbl_vlc_title = ctk.CTkLabel(card_vlc, text=self.t["vlc_section"], font=ctk.CTkFont(size=14, weight="bold"))
        lbl_vlc_title.pack(anchor="w", padx=15, pady=(12, 6))

        row_vlc = ctk.CTkFrame(card_vlc, fg_color="transparent")
        row_vlc.pack(fill="x", padx=15, pady=(0, 12))

        self.vlc_ok = bool(self.config.get("vlc_password"))
        self.lbl_vlc_status = ctk.CTkLabel(
            row_vlc,
            text=self.t["vlc_auto_ok"] if self.vlc_ok else self.t["vlc_auto_fail"],
            text_color="#2ecc71" if self.vlc_ok else "#e74c3c",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_vlc_status.pack(side="left")

        self.btn_vlc_fix = ctk.CTkButton(row_vlc, text=self.t["btn_vlc_fix"], command=self._run_vlc_autoconfig, width=140)
        self.btn_vlc_fix.pack(side="right", padx=(5, 0))

        self.btn_open_vlc = ctk.CTkButton(
            row_vlc, text=self.t["btn_open_vlc"], width=95, fg_color="transparent",
            border_width=1, border_color="#555555", hover_color="#333333",
            command=self._launch_vlc
        )
        self.btn_open_vlc.pack(side="right", padx=(0, 5))

    def _launch_vlc(self):
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "VideoLAN" / "VLC" / "vlc.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "VideoLAN" / "VLC" / "vlc.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "VideoLAN" / "VLC" / "vlc.exe",
        ]
        vlc_path = None
        for c in candidates:
            if c.exists():
                vlc_path = str(c)
                break

        if not vlc_path and winreg:
            for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for sub in (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe",
                    r"SOFTWARE\VideoLAN\VLC",
                ):
                    try:
                        with winreg.OpenKey(root_key, sub) as key:
                            val, _ = winreg.QueryValueEx(key, "" if "App Paths" in sub else "InstallDir")
                            if val:
                                p = Path(val)
                                if p.is_dir():
                                    p = p / "vlc.exe"
                                if p.exists():
                                    vlc_path = str(p)
                                    break
                    except Exception:
                        pass
                if vlc_path:
                    break

        try:
            if vlc_path:
                subprocess.Popen([vlc_path])
            else:
                os.startfile("vlc")
        except Exception as e:
            messagebox.showwarning("VLC", f"Kon VLC niet automatisch starten: {e}\nZorg dat VLC geïnstalleerd is.", parent=self.root)

    def _build_folders_tab(self):
        desc = ctk.CTkLabel(self.tab_folders, text=self.t["folder_desc"], justify="left", text_color="#aaaaaa")
        desc.pack(anchor="w", padx=5, pady=(5, 10))

        bar = ctk.CTkFrame(self.tab_folders, fg_color="transparent")
        bar.pack(fill="x", padx=5, pady=(0, 8))

        btn_add = ctk.CTkButton(bar, text=self.t["add_folder"], command=self._add_folder, width=140)
        btn_add.pack(side="left")

        self.folder_scroll = ctk.CTkScrollableFrame(self.tab_folders, corner_radius=8)
        self.folder_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self._refresh_folder_list()

    def _refresh_folder_list(self):
        for widget in self.folder_scroll.winfo_children():
            widget.destroy()

        if not self.folders:
            empty = ctk.CTkLabel(self.folder_scroll, text=self.t["no_folders"], text_color="#777777")
            empty.pack(pady=30)
            return

        for path_str in self.folders:
            row = ctk.CTkFrame(self.folder_scroll, fg_color="#242424", corner_radius=6)
            row.pack(fill="x", pady=3, padx=4)

            lbl = ctk.CTkLabel(row, text=path_str, anchor="w", font=ctk.CTkFont(size=12))
            lbl.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            btn_del = ctk.CTkButton(
                row, text="✕", width=32, height=28, fg_color="#c0392b", hover_color="#962d22",
                command=lambda p=path_str: self._remove_folder(p)
            )
            btn_del.pack(side="right", padx=6, pady=4)

    def _add_folder(self):
        chosen = filedialog.askdirectory(parent=self.root)
        if chosen:
            path_str = str(Path(chosen).resolve())
            if path_str not in self.folders:
                self.folders.append(path_str)
                self._refresh_folder_list()

    def _remove_folder(self, path_str):
        if path_str in self.folders:
            self.folders.remove(path_str)
            self._refresh_folder_list()

    def _build_prefs_tab(self):
        card_prefs = ctk.CTkFrame(self.tab_prefs, corner_radius=10)
        card_prefs.pack(fill="x", pady=(5, 12), padx=5)

        row_lang = ctk.CTkFrame(card_prefs, fg_color="transparent")
        row_lang.pack(fill="x", padx=15, pady=(12, 8))

        lbl_lang = ctk.CTkLabel(row_lang, text=self.t["language"], font=ctk.CTkFont(weight="bold"))
        lbl_lang.pack(side="left")

        self.combo_lang = ctk.CTkOptionMenu(
            row_lang, values=list(TRANSLATIONS.keys()), command=self._on_language_change, width=140
        )
        self.combo_lang.set(self.lang)
        self.combo_lang.pack(side="right")

        row_switches = ctk.CTkFrame(card_prefs, fg_color="transparent")
        row_switches.pack(fill="x", padx=15, pady=(4, 12))

        sw_startup = ctk.CTkSwitch(row_switches, text=self.t["startup"], variable=self.var_startup)
        sw_startup.pack(anchor="w", pady=6)

        sw_notify = ctk.CTkSwitch(row_switches, text=self.t["notify"], variable=self.var_notify)
        sw_notify.pack(anchor="w", pady=6)

        card_icon = ctk.CTkFrame(self.tab_prefs, corner_radius=10)
        card_icon.pack(fill="x", pady=6, padx=5)

        lbl_icon_title = ctk.CTkLabel(card_icon, text=self.t["tray_cust"], font=ctk.CTkFont(size=14, weight="bold"))
        lbl_icon_title.pack(anchor="w", padx=15, pady=(12, 2))

        lbl_icon_desc = ctk.CTkLabel(card_icon, text=self.t["tray_desc"], text_color="#aaaaaa")
        lbl_icon_desc.pack(anchor="w", padx=15, pady=(0, 8))

        row_icon = ctk.CTkFrame(card_icon, fg_color="transparent")
        row_icon.pack(fill="x", padx=15, pady=(0, 12))

        self.entry_icon_path = ctk.CTkEntry(row_icon)
        self.entry_icon_path.insert(0, self.config.get("custom_icon_path", ""))
        self.entry_icon_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(row_icon, text=self.t["browse"], width=80, command=self._browse_icon)
        btn_browse.pack(side="left", padx=(0, 5))

        btn_reset = ctk.CTkButton(
            row_icon, text=self.t["reset"], width=80, fg_color="transparent",
            border_width=1, border_color="#555555", hover_color="#333333", command=self._reset_icon
        )
        btn_reset.pack(side="left")

    def _browse_icon(self):
        chosen = filedialog.askopenfilename(
            parent=self.root,
            title="Select Custom Icon",
            filetypes=[("Image Files", "*.ico *.png *.jpg *.jpeg")],
        )
        if chosen:
            self.entry_icon_path.delete(0, tk.END)
            self.entry_icon_path.insert(0, chosen)

    def _reset_icon(self):
        self.entry_icon_path.delete(0, tk.END)

    def _on_language_change(self, choice):
        if choice in TRANSLATIONS and choice != self.lang:
            self.lang = choice
            self.t = TRANSLATIONS[self.lang]
            self.config.set("language", self.lang)
            self.root.title(self.t["settings_title"])
            for child in self.root.winfo_children():
                child.destroy()
            self._build_ui()

    def _toggle_trakt_auth(self):
        if self.trakt.is_authenticated():
            self.trakt.clear_token()
            self.lbl_auth_status.configure(text=self.t["status_disc"], text_color="#e74c3c")
            self.btn_auth.configure(text=self.t["btn_connect"])
            messagebox.showinfo("Trakt", "Account successfully disconnected.", parent=self.root)
        else:
            self.btn_auth.configure(state="disabled")
            self.lbl_auth_status.configure(text="Connecting...", text_color="#f39c12")
            threading.Thread(target=self._run_device_code_auth, daemon=True).start()

    def _run_device_code_auth(self):
        try:
            resp = requests.post(
                f"{TRAKT_API_URL}/oauth/device/code",
                json={"client_id": DEFAULT_TRAKT_CLIENT_ID},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code != 200:
                self.root.after(0, lambda: self._auth_failed(f"Trakt API Error {resp.status_code}"))
                return

            data = resp.json()
            device_code = data["device_code"]
            user_code = data["user_code"]
            verification_url = data["verification_url"]

            self.root.clipboard_clear()
            self.root.clipboard_append(user_code)
            self.root.update()

            webbrowser.open(verification_url)
            self.root.after(0, lambda: messagebox.showinfo(
                "Authorize Trakt",
                f"Enter code on Trakt.tv:  {user_code}\n\n(The code is already copied to your clipboard!)",
                parent=self.root
            ))

            start = time.time()
            while time.time() - start < data.get("expires_in", 600):
                time.sleep(data.get("interval", 5))
                t_resp = requests.post(
                    f"{TRAKT_API_URL}/oauth/device/token",
                    json={"code": device_code, "client_id": DEFAULT_TRAKT_CLIENT_ID},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if t_resp.status_code == 200:
                    self.trakt.save_token(t_resp.json())
                    self.root.after(0, self._auth_succeeded)
                    return
                elif t_resp.status_code == 400:
                    continue
                else:
                    break
            self.root.after(0, lambda: self._auth_failed("Authorization timed out."))
        except Exception as e:
            self.root.after(0, lambda: self._auth_failed(str(e)))

    def _auth_succeeded(self):
        self.btn_auth.configure(state="normal", text=self.t["btn_disconnect"])
        self.lbl_auth_status.configure(text=self.t["status_conn"], text_color="#2ecc71")
        messagebox.showinfo("Trakt Connected", "Your Trakt account is successfully connected!", parent=self.root)

    def _auth_failed(self, msg):
        self.btn_auth.configure(state="normal", text=self.t["btn_connect"])
        self.lbl_auth_status.configure(text=self.t["status_disc"], text_color="#e74c3c")
        messagebox.showerror("Error", msg, parent=self.root)

    def _run_vlc_autoconfig(self):
        pwd, ok = VLCConfigManager.get_or_setup_vlc()
        self.config.set("vlc_password", pwd)
        self.vlc_ok = ok
        self.lbl_vlc_status.configure(
            text=self.t["vlc_auto_ok"] if ok else self.t["vlc_auto_fail"],
            text_color="#2ecc71" if ok else "#e74c3c"
        )
        if ok:
            messagebox.showinfo("VLC Setup", "VLC has been configured successfully! Please restart VLC if open.", parent=self.root)
        else:
            messagebox.showwarning("VLC Setup", "Could not configure VLC automatically.", parent=self.root)

    def _save_data(self):
        self.config.set("folders", self.folders)
        startup_val = self.var_startup.get()
        self.config.set("run_on_startup", startup_val)
        set_windows_startup(startup_val)
        self.config.set("show_notifications", self.var_notify.get())
        self.config.set("custom_icon_path", self.entry_icon_path.get().strip())
        self.config.set("language", self.combo_lang.get())

        if self.on_save_callback:
            try:
                self.on_save_callback()
            except Exception:
                pass

    def _save_only(self):
        self._save_data()
        self.lbl_save_status.configure(text=self.t["saved_feedback"])
        self.root.after(2500, lambda: self.lbl_save_status.configure(text=""))

    def _save_and_close(self):
        self._save_data()
        if self.tray_app and self.config.get("show_notifications", True):
            self.tray_app.notify("CoreTrakt", self.t["running_in_tray"])
        self._on_close()

    def _on_close(self):
        SettingsGUI._is_open = False
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass


# ==========================================
#  VLC SCROBBLER ENGINE & SYSTEEMVAK
# ==========================================
class VLCScrobblerEngine:
    def __init__(self, trakt: TraktClient, config: ConfigManager, tray_app):
        self.trakt = trakt
        self.config = config
        self.tray_app = tray_app
        self.current_media = None
        self.last_state = "stopped"
        self.last_progress = 0.0
        self.stop_signal = threading.Event()

    def _get_vlc_auth_headers(self):
        p = self.config.get("vlc_password", "conetrakt")
        b64 = base64.b64encode(f":{p}".encode()).decode()
        return {"Authorization": f"Basic {b64}"}

    def get_vlc_status(self):
        h = self.config.get("vlc_host", "http://localhost:8080").rstrip("/")
        try:
            r = requests.get(f"{h}/requests/status.json", headers=self._get_vlc_auth_headers(), timeout=2)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def _find_active_uri(self, node: dict):
        if not isinstance(node, dict):
            return None
        if node.get("current") == "current" and "uri" in node:
            return node["uri"]
        for child in node.get("children", []):
            f = self._find_active_uri(child)
            if f:
                return f
        return None

    def get_current_file_path(self):
        h = self.config.get("vlc_host", "http://localhost:8080").rstrip("/")
        try:
            r = requests.get(f"{h}/requests/playlist.json", headers=self._get_vlc_auth_headers(), timeout=2)
            if r.status_code == 200:
                uri = self._find_active_uri(r.json())
                if uri and uri.startswith("file://"):
                    pp = urllib.parse.urlparse(uri).path
                    return Path(urllib.request.url2pathname(pp)).resolve()
        except Exception:
            pass
        return None

    def is_folder_allowed(self, fp: Path):
        flds = self.config.get("folders", [])
        if not flds:
            return True
        if not fp:
            return False
        fs = str(fp.resolve()).lower()
        for a in flds:
            if fs.startswith(a.lower()):
                return True
        return False

    def parse_metadata(self, status: dict, fp: Path = None):
        info = status.get("information", {}).get("category", {}).get("meta", {})

        candidates = []
        if fp:
            candidates.append(fp.name)
            candidates.append(str(fp))
        if info.get("filename"):
            candidates.append(info.get("filename"))
        if info.get("title"):
            candidates.append(info.get("title"))

        parsed = None
        used_name = None
        for cand in candidates:
            if not cand:
                continue
            try:
                p = guessit(cand)
            except Exception:
                continue
            if p and "title" in p:
                parsed = p
                used_name = cand
                if p.get("type") == "episode" and "episode" in p:
                    break
                if p.get("type") == "movie" and cand != candidates[-1]:
                    continue
                break

        if not parsed or "title" not in parsed:
            for cand in candidates:
                if not cand:
                    continue
                try:
                    p = guessit(cand)
                    if p and "title" in p:
                        parsed = p
                        used_name = cand
                        break
                except Exception:
                    pass

        if not parsed or "title" not in parsed:
            return None

        s = parsed.get("season")
        if s is None:
            clean_s = 1
        elif isinstance(s, list):
            clean_s = int(s[0]) if s else 1
        else:
            try:
                clean_s = int(s)
            except (ValueError, TypeError):
                clean_s = 1

        e = parsed.get("episode")
        if e is None:
            clean_e = 1
        elif isinstance(e, list):
            clean_e = int(e[0]) if e else 1
        else:
            try:
                clean_e = int(e)
            except (ValueError, TypeError):
                clean_e = 1

        is_ep = parsed.get("type") == "episode" or "episode" in parsed
        media_type = "episode" if is_ep else "movie"

        return {
            "raw_name": used_name or (fp.name if fp else info.get("title", "Unknown")),
            "type": media_type,
            "title": str(parsed.get("title")),
            "season": clean_s,
            "episode": clean_e,
            "year": parsed.get("year"),
        }

    def _poll_cycle(self):
        if not self.trakt.is_authenticated():
            self.tray_app.update_status("Trakt Not Configured")
            return

        status = self.get_vlc_status()
        if not status:
            if self.current_media:
                self.trakt.scrobble("stop", self.current_media, self.last_progress)
                self.current_media = None
                self.tray_app.update_status("VLC Disconnected")
            else:
                self.tray_app.update_status("VLC Closed / Idle")
            return

        st = status.get("state", "stopped")
        ln = status.get("length", 0)
        ct = status.get("time", 0)

        if ln <= 0:
            self.tray_app.update_status("VLC Idle")
            return

        fp = self.get_current_file_path()
        if not self.is_folder_allowed(fp):
            if self.current_media:
                self.trakt.scrobble("stop", self.current_media, self.last_progress)
                self.current_media = None
            self.tray_app.update_status("Playing Ignored Folder")
            return

        pr = (ct / ln) * 100
        mi = self.parse_metadata(status, fp)
        if not mi:
            return

        td = mi["title"]
        if mi["type"] == "episode":
            td += f" S{mi['season']:02d}E{mi['episode']:02d}"

        if st == "playing":
            if not self.current_media or self.current_media["raw_name"] != mi.get("raw_name"):
                if self.current_media:
                    self.trakt.scrobble("stop", self.current_media, self.last_progress)
                self.current_media = mi
                self.trakt.scrobble("start", self.current_media, pr)
                if self.config.get("show_notifications", True):
                    self.tray_app.notify("Now Scrobbling", td)
            elif self.last_state == "paused":
                self.trakt.scrobble("start", self.current_media, pr)
            self.tray_app.update_status(f"Playing: {td} ({int(pr)}%)")
        elif st == "paused" and self.last_state == "playing":
            if self.current_media:
                self.trakt.scrobble("pause", self.current_media, pr)
                self.tray_app.update_status(f"Paused: {td} ({int(pr)}%)")
        elif st == "stopped" and self.current_media:
            self.trakt.scrobble("stop", self.current_media, self.last_progress)
            self.current_media = None
            self.tray_app.update_status("Stopped")

        self.last_state = st
        self.last_progress = pr

    def run(self):
        while not self.stop_signal.is_set():
            try:
                self._poll_cycle()
            except Exception as e:
                print(f"[CoreTrakt] Error in engine cycle: {e}")
            self.stop_signal.wait(POLL_INTERVAL_SECONDS)

        if self.current_media:
            try:
                self.trakt.scrobble("stop", self.current_media, self.last_progress)
            except Exception:
                pass


class TraktTrayApp:
    def __init__(self):
        self.config = ConfigManager(CONFIG_FILE)

        # Ruim bij het starten altijd direct legacy register-sleutels op
        set_windows_startup(self.config.get("run_on_startup", False))

        print("[CoreTrakt] Verifying VLC web interface setup...")
        pwd, ok = VLCConfigManager.get_or_setup_vlc()
        self.config.set("vlc_password", pwd)
        print(f"[CoreTrakt] VLC Configuration status: {'OK' if ok else 'Requires attention'}")

        self.trakt = TraktClient(self.config, TOKEN_FILE)
        self.status_text = "Starting..."
        self.icon = None
        self.engine = None
        self.thread = None

    def update_status(self, text: str):
        self.status_text = text
        if self.icon:
            self.icon.title = f"CoreTrakt: {text}"
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def notify(self, title: str, message: str):
        if self.icon and self.icon.HAS_NOTIFICATION:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def reload_icon_image(self):
        if self.icon:
            try:
                self.icon.icon = get_application_icon(self.config.get("custom_icon_path", ""))
            except Exception:
                pass

    def open_settings(self, icon=None, item=None):
        threading.Thread(
            target=lambda: SettingsGUI(
                self.config, self.trakt, tray_app=self, on_save_callback=self.reload_icon_image
            ),
            daemon=True
        ).start()

    def on_exit(self, icon, item):
        self.update_status("Stopping...")
        if self.engine:
            self.engine.stop_signal.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        icon.stop()

    def run(self):
        print("[CoreTrakt] Starting application engine...")
        if not self.trakt.is_authenticated():
            print("[CoreTrakt] Trakt is not authenticated yet. Launching setup window...")
            SettingsGUI(self.config, self.trakt, tray_app=self)

        self.trakt.refresh_token_if_needed()

        self.engine = VLCScrobblerEngine(self.trakt, self.config, self)
        self.thread = threading.Thread(target=self.engine.run, daemon=True)
        self.thread.start()

        menu = pystray.Menu(
            item(lambda text: f"Status: {self.status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("Settings...", self.open_settings),
            pystray.Menu.SEPARATOR,
            item("Exit Scrobbler", self.on_exit),
        )

        self.icon = pystray.Icon(
            name="CoreTrakt",
            icon=get_application_icon(self.config.get("custom_icon_path", "")),
            title="CoreTrakt: Idle",
            menu=menu,
        )
        self.icon.run()


if __name__ == "__main__":
    _instance_mutex = ensure_single_instance()
    TraktTrayApp().run()