# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import json
import shutil
import datetime
import stat

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt5.QtCore import Qt

from .util import old_user_dir, user_dir, make_dir
from .logging import get_logger

_logger = get_logger(__name__)


def is_factwallet_data(directory: str) -> bool:
    """
    Determine if a directory contains FactWallet data by checking for FACT genesis block hash.

    Args:
        directory: Path to the suspected FactWallet data directory

    Returns:
        bool: True if the directory contains FactWallet data
    """
    if not os.path.exists(directory):
        return False

    # Check config file for FACT genesis block hash
    config_path = os.path.join(directory, "config")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Check for FACT genesis block hash
                blockchain_preferred_block = config.get('blockchain_preferred_block', {})
                block_hash = blockchain_preferred_block.get('hash')

                # FACT genesis block hashes
                FACT_MAINNET_GENESIS = "79cb40f8075b0e3dc2bc468c5ce2a7acbe0afd36c6c3d3a134ea692edac7de49"
                FACT_TESTNET_GENESIS = "550bbf0a444d9f92189f067dd225f5b8a5d92587ebc2e8398d143236072580af"

                if block_hash in [FACT_MAINNET_GENESIS, FACT_TESTNET_GENESIS]:
                    return True

        except (json.JSONDecodeError, OSError):
            pass

    return False


def perform_migration(electrum_dir: str, backup_dir: str, factwallet_dir: str) -> bool:
    """
    Perform the migration: backup old dir and copy contents to new dir.

    Args:
        electrum_dir: Source Electrum directory path
        backup_dir: Backup directory path
        factwallet_dir: Destination FactWallet directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # 1. Move the old wallet directory to backup location
        _logger.info(f"Moving {electrum_dir} to {backup_dir}")
        shutil.move(electrum_dir, backup_dir)

        # 2. Create the new FactWallet directory
        make_dir(factwallet_dir)

        # 3. Copy all files from backup to new FactWallet directory (excluding socket files)
        _logger.info(f"Copying from {backup_dir} to {factwallet_dir}")
        def ignore_sockets(dir, files):
            socket_files = []
            for f in files:
                file_path = os.path.join(dir, f)
                try:
                    if stat.S_ISSOCK(os.stat(file_path).st_mode):
                        socket_files.append(f)
                except Exception:
                    # Let files we can't identify pass
                    pass
            return socket_files
        shutil.copytree(backup_dir, factwallet_dir, dirs_exist_ok=True, ignore=ignore_sockets)

        # 4. Create a marker file to indicate successful migration
        marker_path = os.path.join(factwallet_dir, '.migrated_from_electrum')
        with open(marker_path, 'w', encoding='utf-8') as f:
            f.write(f"Migrated from `{electrum_dir}` (backup: `{backup_dir}`) to `{factwallet_dir}` on {datetime.datetime.now().isoformat()}")

        return True
    except Exception as e:
        _logger.error(f"Migration failed: {e}")
        return False


class MigrationDialog(QDialog):
    """Dialog that asks the user if they want to migrate data from Electrum's directory to FactWallet's."""

    def __init__(self, electrum_dir: str, factwallet_dir: str, parent=None):
        super().__init__(parent)
        self.electrum_dir = electrum_dir
        self.factwallet_dir = factwallet_dir
        when = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.backup_dir = f"{electrum_dir}-backupByFactWallet-{when}"

        self.result = False
        self.error = False

        self.setWindowTitle("FactWallet Migration")
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        # Message
        message = QLabel(
            f"Your FACT0RN wallet is currently stored in:<br>"
            f"<code>{electrum_dir}</code><br><br>"
            f"Would you like to migrate it to:<br>"
            f"<code>{factwallet_dir}</code><br><br>"
            f"A backup will be created before migration<br><br>"
            f"If you choose to skip, a new wallet will be created."
        )
        message.setWordWrap(True)
        message.setTextFormat(Qt.RichText)
        layout.addWidget(message)

        # Buttons
        button_layout = QVBoxLayout()

        self.migrate_button = QPushButton("Yes, migrate my wallet")
        self.migrate_button.clicked.connect(self.do_migrate)
        button_layout.addWidget(self.migrate_button)

        self.skip_button = QPushButton("No, create a new wallet")
        self.skip_button.clicked.connect(self.reject)
        button_layout.addWidget(self.skip_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def do_migrate(self):
        # Perform the migration
        if perform_migration(self.electrum_dir, self.backup_dir, self.factwallet_dir):
            self.result = True
            # QMessageBox.information is a modal dialog - it will block execution until the user
            # acknowledges the message box by clicking OK. This ensures the migration dialog
            # doesn't complete its exec_() call until after the user sees and acknowledges the result.
            QMessageBox.information(
                self,
                "Migration Complete",
                f"Your wallet has been successfully migrated.\n\n"
                f"A backup containing your original wallet is available at:\n"
                f"{self.backup_dir}\n"
            )
            # This will only be called after the user acknowledges the info dialog
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Migration Failed",
                f"Failed to migrate wallet from {self.electrum_dir} to {self.factwallet_dir}.\n\n"
                f"A backup containing your original wallet is available at:\n"
                f"{self.backup_dir}\n\n"
                f"Please try manually copying your wallet or create a new wallet."
            )
            self.error = True
            # This will only be called after the user acknowledges the critical dialog
            self.reject()


def run_migration(electrum_dir: str, factwallet_dir: str) -> bool:
    """
    Run the migration process after user confirmation.

    Args:
        electrum_dir: Source Electrum directory path
        factwallet_dir: Destination FactWallet directory path

    Returns:
        bool: True if migration was either successful or skipped by user
    """
    # Initialize QApplication for the migration dialog
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        created_app = True
    else:
        created_app = False

    try:
        # Show migration dialog
        dialog = MigrationDialog(electrum_dir, factwallet_dir)
        result = dialog.exec_() == QDialog.Accepted and dialog.result

        if dialog.error:
            raise Exception("Error during wallet migration")

        if result:
            _logger.info(f"Successfully migrated data from {electrum_dir} to {factwallet_dir}")
        else:
            _logger.info("User skipped migration")

        return True
    except Exception as e:
        _logger.error(f"Error during migration: {e}")
        raise e
    finally:
        # Clean up the QApplication if we created it
        if created_app and app is not None:
            app.quit()


def check_for_migration(config_options: dict = None) -> None:
    """
    Check if migration is needed and handle it if so.

    Args:
        config_options: Config options dictionary that gets passed to SimpleConfig
    """
    is_portable = config_options.get('portable', False)

    # Skip migration in these cases:
    # 1. On Android (each app has its own data directory)
    if 'ANDROID_DATA' in os.environ:
        _logger.info("Skipping migration check on Android")
        return

    # 2. If user specified a custom data directory outside of portable mode
    if config_options and config_options.get('electrum_path') and not is_portable:
        _logger.info(f"Custom data directory specified: {config_options.get('electrum_path')}")
        return

    # Locate data directories
    if is_portable:
        factwallet_dir = config_options['electrum_path']
        electrum_dir = os.path.join(os.path.dirname(config_options['electrum_path']), 'electrum_data')
    else:
        factwallet_dir = user_dir()
        electrum_dir = old_user_dir()

    # Skip migration if FactWallet directory already exists
    if os.path.exists(factwallet_dir):
        _logger.info(f"FactWallet directory already exists: {factwallet_dir}")
        return

    # Check if Electrum directory exists and contains FactWallet data
    if not electrum_dir or not os.path.exists(electrum_dir):
        _logger.info(f"No Electrum directory found at: {electrum_dir}")
        return

    if is_factwallet_data(electrum_dir):
        _logger.info(f"Found FactWallet data in Electrum directory: {electrum_dir}")
        run_migration(electrum_dir, factwallet_dir)
