# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""

Abstract interface definition for storage backends.

"""

import abc
import logging

from mozsvc.plugin import resolve_name


ROOT_TRANSACTION = "00000000-0000-0000-0000-000000000000"


logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base class for exceptions raised from the storage backend."""
    pass


class NotFoundError(StorageError):
    """Exception raised when accessing something that does not exist."""
    pass


class TransactionNotFoundError(NotFoundError):
    """Exception raised when accessing a transaction that does not exist."""
    pass


class ChunkNotFoundError(NotFoundError):
    """Exception raised when accessing a chunk that does not exist."""
    pass


class ConflictError(StorageError):
    """Exception raised when  something that does not exist."""
    pass


class MentatSyncStorage(object):
    """Abstract Base Class for storage backends."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def reset(self, userid):
        """Discard all data stored for the given userid."""

    @abc.abstractmethod
    def get_head(self, userid):
        """Returns the transaction id for the current head."""

    @abc.abstractmethod
    def set_head(self, userid, trnid):
        """Updates the transaction id for the current head."""

    @abc.abstractmethod
    def get_transactions(self, userid, frm, limit):
        """Returns an iterator of transactions in increasing sequence order."""

    @abc.abstractmethod
    def create_transaction(self, userid, trnid, prev_trnid, chunks):
        """Creates a specific transaction."""

    @abc.abstractmethod
    def get_transaction(self, userid, trnid):
        """Returns a specific transaction."""

    @abc.abstractmethod
    def create_chunk(self, userid, chunk, contents):
        """Creates a specific chunk."""

    @abc.abstractmethod
    def get_chunk(self, userid, chunk):
        """Returns a specific chunk."""


def get_storage(request):
    """Returns a storage backend instance, given a request object.

    This function retrieves the appropriate storage backend instance to
    use for a given request.  Imaging it doing some sort of clever sharding.
    """
    return request.registry["mentatsync:storage:default"]


def includeme(config):
    """Load the storage backends for use by the given configurator.

    This function finds all storage backend declarations in the given
    configurator, creates the corresponding objects and caches them in
    the registry.  The backend to use for a specific request can then
    be looked up by calling get_storage(request).
    """
    settings = config.registry.settings
    storage = load_storage_from_settings("storage", settings)
    config.registry["mentatsync:storage:default"] = storage


def load_storage_from_settings(section_name, settings):
    """Load a storage backend from the named section of the settings.

    This function lookds in the named section of the given configuration
    settings for details of a MentatSyncStorage backend to create.  The class
    name must be specified by the setting "backend", and other settings will
    be passed to the class constructor as keyword arguments.

    If the settings contain a key named "wraps", this is taken to reference
    another section of the settings from which a subordinate backend plugin
    is loaded.  This allows you to e.g. wrap a MemcachedStorage instance
    around an SQLStorage instance from a single config file.
    """
    section_settings = settings.getsection(section_name)
    klass = resolve_name(section_settings.pop("backend"))
    wraps = section_settings.pop("wraps", None)
    if wraps is None:
        return klass(**section_settings)
    else:
        wrapped_storage = load_storage_from_settings(wraps, settings)
        return klass(wrapped_storage, **section_settings)
