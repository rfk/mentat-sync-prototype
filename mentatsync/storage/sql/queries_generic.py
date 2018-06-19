# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Pre-built queries for the SQL storage backend.

This module defines a set of pre-built queries for the SQL storage backend.
Each is either a raw SQL string or a function returning an SQLAlchemy
query object.

"""

from mentatsync.storage import ROOT_TRANSACTION


GET_HEAD = """
    SELECT trnid
    FROM transactions
    WHERE userid = :userid
    AND committed
    ORDER BY seq DESC LIMIT 1
"""

GET_TRANSACTIONS = """
    SELECT trnid
    FROM transactions
    WHERE userid = :userid
    AND seq >= (
        SELECT seq FROM transactions WHERE userid = :userid and trnid = :from
    )
    AND committed
    ORDER BY seq ASC
    LIMIT :limit
"""

GET_TRANSACTIONS_FROM_ROOT = """
    SELECT trnid
    FROM transactions
    WHERE userid = :userid
    AND committed
    ORDER BY seq ASC
    LIMIT :limit
"""

DELETE_ALL_TRANSACTIONS = """
    DELETE FROM transactions
    WHERE userid = :userid
"""

GET_TRANSACTION = """
    SELECT trnid, parent, seq
    FROM transactions
    WHERE userid = :userid AND trnid = :trnid
"""

GET_TRANSACTION_CHUNKS = """
    SELECT chunk
    FROM transaction_chunks
    WHERE userid = :userid AND trnid = :trnid
    ORDER BY idx
"""

CREATE_PENDING_TRANSACTION_FROM_ROOT = """
    INSERT INTO transactions
        (userid, trnid, parent, committed, seq, prev_head, next_head)
    VALUES (:userid, :trnid, '{}', 0, 1, '{}', :trnid)
""".format(ROOT_TRANSACTION, ROOT_TRANSACTION)

CREATE_PENDING_TRANSACTION = """
    INSERT INTO transactions
        (userid, trnid, parent, committed, seq, next_head, prev_head)
    SELECT :userid, :trnid, tprev.trnid, 0, tprev.seq + 1, :trnid,
        CASE WHEN committed THEN :parent ELSE tprev.prev_head END AS cur_head
    FROM transactions AS tprev
    WHERE tprev.userid = :userid AND tprev.trnid = :parent
    AND tprev.next_head = :parent
"""

BUMP_PENDING_TRANSACTION_ANCESTORS = """
    UPDATE transactions
    SET next_head = :trnid
    WHERE userid = :userid AND next_head = :parent
"""

COMMIT_PENDING_TRANSACTION = """
    UPDATE transactions
    SET committed = 1
    WHERE userid = :userid
    AND next_head = :trnid
    AND prev_head = COALESCE((
        SELECT trnid FROM (
            SELECT trnid FROM transactions
            WHERE userid = :userid AND committed
            ORDER BY seq DESC LIMIT 1
        ) as current_head
    ), '{}')
""".format(ROOT_TRANSACTION)

ADD_TRANSACTION_CHUNK = """
    INSERT INTO transaction_chunks (userid, trnid, idx, chunk)
    SELECT :userid, :trnid, :idx, c.chunk
    FROM chunks AS c
    WHERE c.userid = :userid AND c.chunk = :chunk
"""

GET_CHUNK_PAYLOAD = """
    SELECT payload FROM chunks WHERE userid = :userid AND chunk = :chunk
"""

CREATE_CHUNK = """
    INSERT INTO chunks (userid, chunk, payload)
    VALUES (:userid, :chunk, :payload)
"""
