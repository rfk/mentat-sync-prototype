# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
SQL backend for mentatsync storage.

This module implements an SQL storage plugin for synctorage.  In the simplest
use case it consists of three database tables:

  collections:  the names and ids of any custom collections
  user_collections:  the per-user metadata associated with each collection
  bso:  the individual BSO items stored in each collection

For efficiency when dealing with large datasets, the plugin also supports
sharding of the BSO items into multiple tables named "bso0" through "bsoN".
This behaviour is off by default; pass shard=True to enable it.
"""

import base64
import logging

from mentatsync.storage import (MentatSyncStorage,
                                ConflictError,
                                TransactionNotFoundError,
                                ChunkNotFoundError,
                                ROOT_TRANSACTION)

from mentatsync.storage.sql.dbconnect import DBConnector


logger = logging.getLogger(__name__)


class SQLStorage(MentatSyncStorage):
    """Storage plugin implemented using an SQL database.

    This class implements the storage plugin API using SQLAlchemy.  You
    must specify the SQLAlchemy database URI string to connect to, and
    can customize behaviour with the following keyword arguments:

        * create_tables:         create the database tables if they don't
                                 exist at startup

    """

    def __init__(self, sqluri, **dbkwds):
        self.sqluri = sqluri
        self.dbconnector = DBConnector(sqluri, **dbkwds)

    def reset(self, userid):
        # Deleting all transactions is sufficient to reset the user's
        # storage state.  It might leave some orphaned chunk data but
        # that can be dealth with via background garbage collection.
        with self.dbconnector.connect() as session:
            session.query("DELETE_ALL_TRANSACTIONS", {
                "userid": userid
            })

    def get_head(self, userid):
        with self.dbconnector.connect() as session:
            head = session.query_scalar("GET_HEAD", {
                "userid": userid
            })
            if head is None:
                head = ROOT_TRANSACTION
            return head

    def set_head(self, userid, trnid):
        with self.dbconnector.connect() as session:
            updated = session.query("COMMIT_PENDING_TRANSACTION", {
                "userid": userid,
                "trnid": trnid,
            })
            if not updated:
                raise ConflictError()

    def get_transactions(self, userid, frm, limit):
        with self.dbconnector.connect() as session:
            if frm == ROOT_TRANSACTION:
                trns = session.query_fetchall("GET_TRANSACTIONS_FROM_ROOT", {
                    "userid": userid,
                    "limit": limit,
                })
            else:
                trns = session.query_fetchall("GET_TRANSACTIONS", {
                    "userid": userid,
                    "from": frm,
                    "limit": limit,
                })
                if next(trns)["trnid"] != frm:
                    # Whoops!
                    # You tried to query from an uncommitted transaction!
                    raise RuntimeError("seriously, don't do that")
            for trn in trns:
                yield trn["trnid"]

    def create_transaction(self, userid, trnid, parent, chunks):
        with self.dbconnector.connect() as session:
            if parent == ROOT_TRANSACTION:
                session.query("CREATE_PENDING_TRANSACTION_FROM_ROOT", {
                    "userid": userid,
                    "trnid": trnid,
                })
            else:
                inserted = session.query("CREATE_PENDING_TRANSACTION", {
                    "userid": userid,
                    "trnid": trnid,
                    "parent": parent,
                })
                if not inserted:
                    # This could fail because parent doesn't exist, or
                    # because parent already has a descendant.
                    # We should differentiate, but meh for now.
                    raise ConflictError
                updated = session.query("BUMP_PENDING_TRANSACTION_ANCESTORS", {
                    "userid": userid,
                    "trnid": trnid,
                    "parent": parent,
                })
                if not updated:
                    raise RuntimeError("something has gone terribly wrong")
            for idx, chunk in enumerate(chunks):
                added = session.query("ADD_TRANSACTION_CHUNK", {
                    "userid": userid,
                    "trnid": trnid,
                    "idx": idx,
                    "chunk": chunk,
                })
                if not added:
                    raise ChunkNotFoundError()

    def get_transaction(self, userid, trnid):
        with self.dbconnector.connect() as session:
            trn = session.query_fetchone("GET_TRANSACTION", {
                "userid": userid,
                "trnid": trnid,
            })
            if trn is None:
                raise TransactionNotFoundError()
            chunks = session.query_fetchall("GET_TRANSACTION_CHUNKS", {
                "userid": userid,
                "trnid": trnid,
            })
            return {
                "id": trn["trnid"],
                "seq": trn["seq"],
                "parent": trn["parent"],
                "chunks": [c["chunk"] for c in chunks],
            }

    def create_chunk(self, userid, chunk, payload):
        with self.dbconnector.connect() as session:
            session.query("CREATE_CHUNK", {
                "userid": userid,
                "chunk": chunk,
                "payload": base64.b64encode(payload),
            })

    def get_chunk(self, userid, chunk):
        with self.dbconnector.connect() as session:
            payload = session.query_scalar("GET_CHUNK_PAYLOAD", {
                "userid": userid,
                "chunk": chunk,
            })
            if payload is None:
                raise ChunkNotFoundError()
            return base64.b64decode(payload)
