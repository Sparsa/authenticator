"""
 Copyright © 2017 Bilal Elmoussaoui <bil.elmoussaoui@gmail.com>

 This file is part of Authenticator.

 Authenticator is free software: you can redistribute it and/or
 modify it under the terms of the GNU General Public License as published
 by the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Authenticator is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You  ould have received a copy of the GNU General Public License
 along with Authenticator. If not, see <http://www.gnu.org/licenses/>.
"""
from collections import OrderedDict
import sqlite3
from os import path, makedirs

from gi.repository import GLib
from .logger import Logger


class Database:
    """SQL database handler."""

    # Default instance
    instance = None
    db_version = 2

    def __init__(self):
        db_dir = path.join(GLib.get_user_config_dir(), 'Authenticator/')
        db_file = path.join(
            db_dir, 'database-{}.db'.format(str(Database.db_version)))
        makedirs(path.dirname(db_dir), exist_ok=True)
        if not path.exists(db_file):
            with open(db_file, 'w') as file_obj:
                file_obj.write('')
        self.conn = sqlite3.connect(db_file)
        if not self.is_table_exists():
            Logger.debug("SQL: Table 'accounts' does not exist")
            self.create_table()
            Logger.debug("SQL: Table 'accounts' created successfully")

    @staticmethod
    def get_default():
        """Return the default instance of database"""
        if Database.instance is None:
            Database.instance = Database()
        return Database.instance

    def insert(self, name, provider, secret, image):
        """
        Insert a new account to the database
        :param name: Account name
        :param provider: Service provider
        :param secret: the secret code
        :param image: the image name/url
        :return: a dict with id, name, image & encrypted_secret
        """
        query = "INSERT INTO accounts (name, provider, secret_code, image) VALUES (?, ?, ?, ?)"
        try:
            self.conn.execute(query, [name, provider, secret, image])
            self.conn.commit()
            return OrderedDict([
                ("id", self.latest_id),
                ("name", name),
                ("provider", provider),
                ("secret_id", secret),
                ("image", image)
            ])
        except Exception as error:
            Logger.error("[SQL] Couldn't add a new account")
            Logger.error(str(error))

    def get_secret_code(self, id_):
        """
        Get the secret code by id
        :param id_: int the account id
        :return: the secret id
        """
        query = "SELECT secret_code FROM accounts WHERE uid=?"
        try:
            data = self.conn.cursor().execute(query, (id_,))
            return data.fetchone()[0]
        except Exception as error:
            Logger.error("[SQL] Couldn't get account secret code")
            Logger.error(str(error))
        return None

    def remove(self, id_):
        """
            Remove an account by id
            :param id_: (int) account uid
        """
        query = "DELETE FROM accounts WHERE uid=?"
        try:
            self.conn.execute(query, (id_,))
            self.conn.commit()
        except Exception as error:
            Logger.error("[SQL] Couldn't remove account by uid")
            Logger.error(str(error))

    def update(self, id_, name, image):
        """
        Update an account by id
        :param id_: the account id
        :param name: the new account name
        :param image: the new account image
        """
        query = "UPDATE accounts SET name=?, image=? WHERE uid=?"
        try:
            self.conn.execute(query, (name, image, id_, ))
            self.conn.commit()
        except Exception as error:
            Logger.error("[SQL] Couldn't update account name by id")
            Logger.error(error)

    @property
    def count(self):
        """
            Count number of accounts
           :return: (int) count
        """
        query = "SELECT COUNT(uid) AS count FROM accounts"
        try:
            data = self.conn.cursor().execute(query)
            return data.fetchone()[0]
        except Exception as error:
            Logger.error("[SQL]: Couldn't count accounts list")
            Logger.error(str(error))
        return None

    @property
    def accounts(self):
        """
            Fetch list of accounts
            :return: (tuple) list of accounts
        """
        query = "SELECT * FROM accounts"
        try:
            data = self.conn.cursor().execute(query)
            accounts = data.fetchall()
            return [OrderedDict([
                    ("id", account[0]),
                    ("name", account[1]),
                    ("provider", account[2]),
                    ("secret_id", account[3]),
                    ("logo", account[4])
                    ]) for account in accounts]
        except Exception as error:
            Logger.error("[SQL] Couldn't fetch accounts list")
            Logger.error(str(error))
        return None

    @property
    def latest_id(self):
        """
            Get the latest uid on accounts table
            :return: (int) latest uid
        """
        query = "SELECT uid FROM accounts ORDER BY uid DESC LIMIT 1;"
        try:
            data = self.conn.cursor().execute(query)
            return data.fetchone()[0]
        except Exception as error:
            Logger.error("[SQL] Couldn't fetch the latest uid")
            Logger.error(str(error))
        return None

    def create_table(self):
        """Create 'accounts' table."""
        query = '''CREATE TABLE "accounts" (
            "uid" INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE ,
            "name" VARCHAR NOT NULL ,
            "provider" VARCHAR NOT NULL,
            "secret_code" VARCHAR NOT NULL UNIQUE,
            "image" TEXT NOT NULL
        )'''
        try:
            self.conn.execute(query)
            self.conn.commit()
        except Exception as error:
            Logger.error("[SQL] Impossible to create table 'accounts'")
            Logger.error(str(error))

    def is_table_exists(self):
        """
            Check if accounts table exists
            :return: (bool)
        """
        query = "SELECT uid from accounts LIMIT 1"
        try:
            self.conn.cursor().execute(query)
            return True
        except Exception as e:
            return False
