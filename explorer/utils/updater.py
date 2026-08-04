import json
import os
import requests
import zipfile
import time
from threading import Thread
from semantic_version import Version # type: ignore

from config import config # type: ignore

from .debug import Debug

# Check for updates at most once per day
UPDATE_CHECK_INTERVAL:int = (3600 * 24)

TIMEOUT=10

class Updater():
    """
    Handle checking for, and installing, plugin updates.

    Create the object with parameters plugin_dir, gh_project, gh_release_info.
      gh_project is the github project name, e.g. "my-plugin"
    gh_release_info is the github api url for release info, e.g. "https://api.github.com/repos/coder/my-plugin/releases/latest"
    Call check_for_update(version) at plugin startup. It's asynchronous.
    Call install() to install the update when you choose (commonly on shutdown).

    Not a singleton: EDMC loads every plugin into one process, and since each plugin
    constructs its own Updater for its own plugin_dir/gh_project, a shared/global instance
    here would mean the second plugin to construct one silently gets the first plugin's
    already-initialized instance instead of its own -- construct one per plugin as needed.
    """
    def __init__(self, plugin_dir:str, gh_project:str, gh_release_info:str='') -> None:
        self.plugin_dir:str = plugin_dir
        self.gh_project:str = gh_project
        self.gh_release_info:str = gh_release_info
        if self.gh_release_info == '':
            self.gh_release_info = f'https://api.github.com/repos/coder/{self.gh_project}/releases/latest'

        self.update_available:bool = False # Is there an update available?
        self.install_update:bool = False # Should it be installed?
        self.update_version:Version = Version("0.0.0") # The update version number
        self.releasenotes:str = "" # The update release notes

        self.download_url:str = ""
        self.zip_downloaded:str = "" # ZIP file that was downloaded

    def download_zip(self) -> None:
        """ Download the zipfile of the latest version """

        self.zip_path:str = os.path.join(self.plugin_dir, "updates")
        os.makedirs(self.zip_path, exist_ok=True)

        zip_file:str = os.path.join(self.zip_path, f"{self.gh_project}-{str(self.update_version)}.zip")
        # Don't download again if we already have it. (Was os.remove(zip_file))
        if os.path.exists(zip_file):
            self.zip_downloaded = zip_file
            return

        try:
            r:requests.Response = requests.get(self.download_url, headers={'User-Agent': 'EDMC-PluginLib Updater'}, timeout=TIMEOUT)
            r.raise_for_status()
        except Exception:
            Debug.logger.error(f"Failed to download {self.gh_project} update (status code {r.status_code}).)")
            return

        with open(zip_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=32768):
                f.write(chunk)
        self.zip_downloaded = zip_file

    def install(self) -> None:
        """ Download the latest zip file and install it """
        if self.install_update != True or self.zip_downloaded == "":
            return
        try:
            with zipfile.ZipFile(self.zip_downloaded, 'r') as zip_ref:
                zip_ref.extractall(self.plugin_dir)
            with open(os.path.join(self.plugin_dir, "version"), 'w') as version_file:
                version_file.write(str(self.update_version))
            Debug.logger.info(f"Version {self.update_version} installed")
        except Exception as e:
            Debug.logger.error("Failed to install update, exception info:", exc_info=e)

    def get_release(self) -> bool:
        """ Get info about the latest release from github, version, changelog, and download url """
        try:
            Debug.logger.debug(f"Requesting {self.gh_release_info}")
            r:requests.Response = requests.get(self.gh_release_info, headers={'User-Agent': 'EDMC-PluginLib Updater'}, timeout=TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            Debug.logger.error("Failed to get changelog, exception info:", exc_info=e)
            self.install_update = False
            return False

        version_data:dict = json.loads(r.content)
        if version_data['draft'] == True or version_data['prerelease'] == True:
            Debug.logger.info("Latest server version is draft or pre-release, ignoring")
            return False

        assets:list = version_data.get('assets', [])
        if assets == []:
            Debug.logger.info("No assets")
            return False

        try:
            self.update_version = Version.coerce(version_data.get('tag_name', '0.0.0').replace('v', ''))
        except Exception as e:
            Debug.logger.info(f"Bad version data {e}")
            return False

        # Get the changelog and replace all breaklines with simple ones
        releasenotes:str = version_data.get('body', '')
        self.releasenotes = "\n".join(releasenotes.splitlines())

        self.download_url = assets[0].get('browser_download_url', "")
        if self.download_url == "":
            Debug.logger.info("No download URL")
            return False

        return True

    def _check_update(self, version:Version) -> None:
        """ Compare the current version file with github version """
        try:
            Debug.logger.debug(f"Checking for update")
            if not self.get_release(): return
            Debug.logger.debug(f"Version: {version} response {self.update_version} ")
            if version >= self.update_version: return

            Debug.logger.debug('Update available')
            self.update_available = True
            self.install_update = True
            self.download_zip()

        except Exception as e:
            Debug.logger.error("Failed to check for updates, exception info:", exc_info=e)


    def check_for_update(self, version:Version) -> None:
        """ Start an update check thread """
        last:int = config.get_int(f"{self.gh_project}_last_update_check", 0)
        if last >= int(time.time()) - UPDATE_CHECK_INTERVAL: # Check for updates at most once per interval
            return

        config.set(f"{self.gh_project}_last_update_check", int(time.time()))

        thread:Thread = Thread(target=self._check_update, args=[version], name=f"{self.gh_project} update checker")
        thread.start()
