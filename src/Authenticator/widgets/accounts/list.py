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

 You should have received a copy of the GNU General Public License
 along with Authenticator. If not, see <http://www.gnu.org/licenses/>.
"""
import asyncio
from gettext import gettext as _
from gi.repository import Gtk, GObject, Handy

from Authenticator.widgets.accounts.row import AccountRow
from Authenticator.models import Account, AccountsManager, ProviderManager, FaviconManager
from Authenticator.utils import load_pixbuf_from_provider


class AccountsWidget(Gtk.Box, GObject.GObject):
    instance = None

    __gsignals__ = {
        'account-removed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'account-added': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        GObject.GObject.__init__(self)
        self.get_style_context().add_class("accounts-widget")

        self._providers = {}
        self._to_delete = []
        self._build_widgets()
        self.__fill_data()

    def _build_widgets(self):
        self.otp_progress_bar = Gtk.ProgressBar()
        self.otp_progress_bar.get_style_context().add_class("progress-bar")
        self.add(self.otp_progress_bar)
        AccountsManager.get_default().connect("counter_updated",
                                               self._on_counter_updated)

        self.accounts_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.accounts_column = Handy.Column()
        self.accounts_column.set_maximum_width(700)
        self.accounts_column.add(self.accounts_container)

        accounts_scrolled = Gtk.ScrolledWindow()
        accounts_scrolled.add_with_viewport(self.accounts_column)
        self.pack_start(accounts_scrolled, True, True, 0)

    @staticmethod
    def get_default():
        """Return the default instance of AccountsWidget."""
        if AccountsWidget.instance is None:
            AccountsWidget.instance = AccountsWidget()
        return AccountsWidget.instance

    def append(self, account):
        accounts_list = self._providers.get(account.provider)
        if not accounts_list:
            accounts_list = AccountsList()
            accounts_list.connect("account-deleted", self._on_account_deleted)
            self._providers[account.provider] = accounts_list
            provider_widget = ProviderWidget(accounts_list, account.provider)
            self.accounts_container.pack_start(provider_widget, False, False, 0)
        accounts_list.add_row(account)
        self._reorder()
        self.emit("account-added")

    @property
    def accounts_lists(self):
        return self._providers.values()

    def clear(self):
        for account_list in self._providers.values():
            self.accounts_container.remove(account_list.get_parent())
        self._providers = {}

    def update_provider(self, account, new_provider):
        current_account_list = None
        account_row = None
        for account_list in self._providers.values():
            for account_row in account_list:
                if account_row.account == account:
                    current_account_list = account_list
                    break

            if current_account_list:
                break
        if account_row:
            current_account_list.remove(account_row)
            account_row.account.provider = new_provider
            self.append(account_row.account)
        self._on_account_deleted(current_account_list)
        self._reorder()
        self._clean_unneeded_providers_widgets()

    def __fill_data(self):
        """Fill the Accounts List with accounts."""
        accounts = AccountsManager.get_default().accounts
        for account in accounts:
            self.append(account)

    def _on_account_deleted(self, account_list):
        if len(account_list.get_children()) == 0:
            self._to_delete.append(account_list)
        self._reorder()
        self._clean_unneeded_providers_widgets()
        self.emit("account-removed")

    def _clean_unneeded_providers_widgets(self):
        for account_list in self._to_delete:
            provider_widget = account_list.get_parent()
            self.accounts_container.remove(provider_widget)
            del self._providers[provider_widget.provider]
        self._to_delete = []

    def _reorder(self):
        """
            Re-order the ProviderWidget on AccountsWidget.
        """
        childs = self.accounts_container.get_children()
        ordered_childs = sorted(
            childs, key=lambda children: children.provider.lower())
        for i in range(len(ordered_childs)):
            self.accounts_container.reorder_child(ordered_childs[i], i)
        self.show_all()

    def _on_counter_updated(self, accounts_manager, counter):
        counter_fraction = counter / accounts_manager.counter_max
        self.otp_progress_bar.set_fraction(counter_fraction)
        self.otp_progress_bar.set_tooltip_text(
            _("The One-Time Passwords expires in {} seconds").format(counter))


class ProviderWidget(Gtk.Box):

    def __init__(self, accounts_list, provider):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.get_style_context().add_class("provider-widget")
        self.provider = provider
        self._build_widgets(accounts_list)

    def _build_widgets(self, accounts_list):
        provider_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        provider_lbl = Gtk.Label()
        provider_lbl.set_text(self.provider)
        provider_lbl.set_halign(Gtk.Align.START)
        provider_lbl.get_style_context().add_class("provider-label")

        self.provider_img = Gtk.Image()

        provider_container.pack_start(self.provider_img, False, False, 3)
        provider_container.pack_start(provider_lbl, False, False, 3)

        self.pack_start(provider_container, False, False, 3)
        self.pack_start(accounts_list, False, False, 3)

        provider = ProviderManager.get_default().get_provider_by_name(self.provider)

        if provider:
            asyncio.run(FaviconManager.get_default().grab_favicon(provider.img, provider.url,
                                                      self.__on_favicon_downloaded,
                                                      None))

    def __on_favicon_downloaded(self, img_path, callback_data=None):
        self.provider_img.set_from_pixbuf(load_pixbuf_from_provider(img_path, 32))

class AccountsList(Gtk.ListBox, GObject.GObject):
    """Accounts List."""

    __gsignals__ = {
        'account-deleted': (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    # Default instance of accounts list
    instance = None

    def __init__(self):
        GObject.GObject.__init__(self)
        Gtk.ListBox.__init__(self)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.get_style_context().add_class("accounts-list")

    def append_new(self, name, provider, token):
        account = Account.create(name, provider, token)
        self.add_row(account)

    def append(self, _id, name, provider, secret_id):
        account = Account(_id, name, provider, secret_id)
        self.add_row(account)

    def add_row(self, account):
        row = AccountRow(account)
        row.delete_btn.connect("clicked", self.__on_delete_child, row)
        self.add(row)

    def __on_delete_child(self, model_btn, account_row):
        self.remove(account_row)
        account_row.account.remove()
        self.emit("account-deleted")

