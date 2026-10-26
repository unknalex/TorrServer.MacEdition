# SPDX-License-Identifier: GPL-3.0-or-later + # Copyright (C) 2026 unknalex
import os
import sys
import socket
import subprocess
import webbrowser
import threading
import urllib.request
import json
import time
import rumps

BASE_DIR = os.path.expanduser("~/.local/share/TorrServer")
TORR_PATH = os.path.join(BASE_DIR, "TorrServer-darwin-amd64")
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
FIRST_RUN_FILE = os.path.join(BASE_DIR, "notified.txt")
LOG_PATH = os.path.join(BASE_DIR, "server.log")
APP_VERSION = "1.0"
PORT = "8090"
GITHUB_API_URL = "https://api.github.com/repos/YouROK/TorrServer/releases/latest"
PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/com.torrserver.macedition.plist")

XATTR = "/usr/bin/xattr"
PKILL = "/usr/bin/pkill"
PGREP = "/usr/bin/pgrep"
OSASCRIPT = "/usr/bin/osascript"


def get_resource(filename):
    """Находит иконки внутри собранного .app-пакета или в текущей папке с авто-фолбэком."""
    if getattr(sys, 'frozen', False):
        path = os.path.join(os.path.dirname(sys.executable), '../Resources', filename)
        if os.path.exists(path):
            return path
    if os.path.exists(filename):
        return filename

    fallback = "update.png" if filename in ["think.png", "update.png"] else "off.png"
    if getattr(sys, 'frozen', False):
        fallback_path = os.path.join(os.path.dirname(sys.executable), '../Resources', fallback)
        if os.path.exists(fallback_path):
            return fallback_path
    return fallback


def is_autostart_enabled():
    return os.path.exists(PLIST_PATH)


def set_autostart(enable):
    if enable:
        app_path = "/Applications/TorrServer.app"
        if not os.path.exists(app_path):
            app_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../.."))

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.torrserver.macedition</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>{app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
        os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
        with open(PLIST_PATH, "w") as f:
            f.write(plist_content)
    else:
        if os.path.exists(PLIST_PATH):
            os.remove(PLIST_PATH)


class TorrServerManager(rumps.App):
    def __init__(self):
        super(TorrServerManager, self).__init__("", icon=get_resource("off.png"))

        self._busy = False

        self.status_item = rumps.MenuItem("Статус: Проверка...")
        self.toggle_item = rumps.MenuItem("Включить TorrServer", callback=self.toggle_server)

        self.autostart_item = rumps.MenuItem("Автозагрузка", callback=self.toggle_autostart)
        self.autostart_item.state = is_autostart_enabled()

        self.update_item = rumps.MenuItem("Проверить обновление", callback=self.manual_check_update)
        self.about_item = rumps.MenuItem("О программе", callback=self.show_about)
        self.open_web = rumps.MenuItem("Открыть веб-интерфейс", callback=self.open_browser)

        self.menu = [
            self.status_item,
            self.toggle_item,
            None,
            self.autostart_item,
            self.update_item,
            None,
            self.open_web,
            self.about_item,
        ]
        self.timer = rumps.Timer(self.periodic_check, 5)
        self.timer.start()

        self.check_notification_permission()

        if not os.path.exists(TORR_PATH):
            self.icon = get_resource("think.png")
            self.status_item.title = "Статус: Скачивание..."
            self.toggle_item.title = "Подождите..."
            threading.Thread(target=self.download_server, args=(True, False), daemon=True).start()
        else:
            self.check_status()
            threading.Thread(target=self.check_for_updates, args=(False,), daemon=True).start()

    # ---------- служебное ----------

    def periodic_check(self, _):
        if self._busy:
            return
        self.check_status()

    def check_notification_permission(self):
        if not os.path.exists(FIRST_RUN_FILE):
            try:
                os.makedirs(BASE_DIR, exist_ok=True)
                script = ('display dialog "Для полноценного отслеживания статуса сервера, '
                          'автозагрузки и уведомлений об обновлениях рекомендуем разрешить уведомления." '
                          'buttons {"Понятно"} default button "Понятно" with title "TorrServer" with icon note')
                subprocess.call([OSASCRIPT, "-e", script])
                rumps.notification("TorrServer", "Уведомления активны",
                                   "Теперь вы будете в курсе состояния сервера.")
                open(FIRST_RUN_FILE, "w").close()
            except Exception as e:
                print(f"Dialog error: {e}")

    def _process_exists(self):
        """Существует ли процесс сервера (по имени бинаря)."""
        try:
            subprocess.check_output([PGREP, "-f", os.path.basename(TORR_PATH)])
            return True
        except Exception:
            return False

    def is_running(self):
        """Сервер «работает», если порт 8090 принимает соединения."""
        if not os.path.exists(TORR_PATH):
            return False
        try:
            with socket.create_connection(("127.0.0.1", int(PORT)), timeout=0.5):
                return True
        except Exception:
            return False

    def start_server_process(self):
        """Запуск TorrServer с правильным cwd и логированием."""
        os.makedirs(BASE_DIR, exist_ok=True)
        log = open(LOG_PATH, "ab")
        try:
            log.write(
                f"\n=== start at {time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"cwd={BASE_DIR} ===\n".encode()
            )
            log.flush()
        except Exception:
            pass
        return subprocess.Popen(
            [TORR_PATH],
            cwd=BASE_DIR,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    def _stop_server_process(self):
        subprocess.run([PKILL, "-f", os.path.basename(TORR_PATH)],
                       check=False, stderr=subprocess.DEVNULL)

    # ---------- установка / обновление ----------

    def download_server(self, is_initial=False, manual=False):
        self._busy = True
        try:
            self.icon = get_resource("think.png")
            self.status_item.title = "Статус: Скачивание..."
            self.toggle_item.title = "Подождите..."

            os.makedirs(BASE_DIR, exist_ok=True)
            req = urllib.request.Request(GITHUB_API_URL,
                                         headers={'User-Agent': 'TorrServer-MacEdition'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            latest_tag = data.get('tag_name', '')

            download_url = None
            for asset in data.get('assets', []):
                if 'darwin-amd64' in asset.get('name', ''):
                    download_url = asset.get('browser_download_url')
                    break

            if not download_url:
                raise Exception("Не найден файл для Intel Mac (darwin-amd64).")

            was_running = self._process_exists()
            if was_running:
                self._stop_server_process()
                time.sleep(1)

            urllib.request.urlretrieve(download_url, TORR_PATH)
            os.chmod(TORR_PATH, 0o755)

            # Снять quarantine, иначе Gatekeeper может блокировать exec из .app
            subprocess.run([XATTR, "-d", "com.apple.quarantine", TORR_PATH],
                           stderr=subprocess.DEVNULL, check=False)

            with open(VERSION_FILE, "w") as f:
                f.write(latest_tag)

            if was_running:
                try:
                    self.start_server_process()
                except Exception as e:
                    print(f"Restart error: {e}")

            if manual or is_initial:
                rumps.notification("TorrServer", "Успешно!",
                                   f"Установлена версия {latest_tag}")
        except Exception as e:
            print(f"Download error: {e}")
            if manual:
                rumps.notification("TorrServer", "Ошибка обновления", str(e))
        finally:
            self._busy = False
            self.check_status()

    def check_for_updates(self, manual=False):
        try:
            if manual:
                self.icon = get_resource("think.png")
                self.status_item.title = "Статус: Проверка обновлений..."
                rumps.notification("TorrServer", "Проверка", "Связываемся с GitHub...")

            req = urllib.request.Request(GITHUB_API_URL,
                                         headers={'User-Agent': 'TorrServer-MacEdition'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            latest_tag = data.get('tag_name', '')
            current_tag = ""
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    current_tag = f.read().strip()

            if latest_tag != current_tag or not os.path.exists(TORR_PATH):
                if manual:
                    rumps.notification("TorrServer", "Найдено обновление",
                                       f"Скачиваем {latest_tag}...")
                self.download_server(is_initial=False, manual=manual)
            else:
                if manual:
                    rumps.notification("TorrServer", "Обновлений нет",
                                       "Текущая версия актуальна.")
                self.check_status()
        except Exception as e:
            print(f"Update check error: {e}")
            if manual:
                rumps.notification("TorrServer", "Ошибка проверки", str(e))
                self.check_status()

    def manual_check_update(self, sender):
        threading.Thread(target=self.check_for_updates, args=(True,), daemon=True).start()

    # ---------- меню ----------

    def show_about(self, sender):
        core_version = "Не определена"
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r") as f:
                core_version = f.read().strip()

        icon_path = get_resource("logo.png")

        script = f'''
        set iconFile to POSIX file "{icon_path}"
        set messageText to "TorrServer.MacEdition — версия " & "{APP_VERSION}" & return & return & "Ядро: TorrServer MatriX (" & "{core_version}" & ")" & return & return & "Автор: unknalex" & return & "https://github.com/unknalex/TorrServer.MacEdition" & return & return & "Создано на основе официального TorrServer" & return & "https://github.com/YouROK/TorrServer"

        set res to button returned of (display dialog messageText with title "О программе" buttons {{"Закрыть", "GitHub TorrServer", "GitHub проекта"}} default button "Закрыть" with icon file iconFile)
        return res
        '''
        try:
            result = subprocess.check_output([OSASCRIPT, "-e", script]).decode().strip()
            if result == "GitHub проекта":
                webbrowser.open("https://github.com/unknalex/TorrServer.MacEdition")
            elif result == "GitHub TorrServer":
                webbrowser.open("https://github.com/YouROK/TorrServer")
        except Exception:
            pass

    def check_status(self):
        if not os.path.exists(TORR_PATH):
            return
        if self.is_running():
            self.icon = get_resource("on.png")
            self.status_item.title = "Статус: РАБОТАЕТ"
            self.toggle_item.title = "Выключить TorrServer"
        else:
            self.icon = get_resource("off.png")
            self.status_item.title = "Статус: ВЫКЛЮЧЕН"
            self.toggle_item.title = "Включить TorrServer"

    # ---------- включение / выключение ----------

    def toggle_server(self, sender):
        threading.Thread(target=self._toggle_server_thread, daemon=True).start()

    def _toggle_server_thread(self):
        self._busy = True
        try:
            if "ВЫКЛЮЧЕН" in self.status_item.title or "ОСТАНОВЛЕН" in self.status_item.title:
                self.icon = get_resource("think.png")
                self.status_item.title = "Статус: Включение..."
                self.toggle_item.title = "Подождите..."
                try:
                    self._stop_server_process()
                    time.sleep(0.3)

                    self.start_server_process()

                    success = False
                    for _ in range(50):  # ~15 сек макс
                        if self.is_running():
                            success = True
                            break
                        time.sleep(0.3)

                    if success:
                        rumps.notification("TorrServer", "Запущен", "Сервер активен.")
                    else:
                        rumps.notification("TorrServer", "Внимание",
                                           "Сервер не отвечает. Проверьте server.log.")
                except Exception as e:
                    print(f"Toggle error: {e}")

            elif "РАБОТАЕТ" in self.status_item.title:
                self.icon = get_resource("think.png")
                self.status_item.title = "Статус: Выключение..."
                self.toggle_item.title = "Подождите..."
                try:
                    self._stop_server_process()

                    success = False
                    for _ in range(35):
                        if not self.is_running():
                            success = True
                            break
                        time.sleep(0.3)

                    if success:
                        rumps.notification("TorrServer", "Остановлен", "")
                    else:
                        rumps.notification("TorrServer", "Внимание",
                                           "Сервер не отключился. Попробуйте перезапустить программу.")
                except Exception as e:
                    print(f"Stop error: {e}")
        finally:
            self._busy = False
            self.check_status()

    def toggle_autostart(self, sender):
        new_state = not sender.state
        set_autostart(new_state)
        sender.state = new_state

    def open_browser(self, sender):
        webbrowser.open(f"http://127.0.0.1:{PORT}")


if __name__ == "__main__":
    TorrServerManager().run()
