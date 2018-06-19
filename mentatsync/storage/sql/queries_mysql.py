# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Custom queries for MySQL.

This module overrides some queries from queries_generic.py with code
tailored to MySQL.
"""

# We can use mysql's multi-table delete to transitively
# remove chunk data when clearing a user's transactions.

DELETE_ALL_TRANSACTIONS = """
    DELETE transactions, transaction_chunks, chunks
    FROM transactions
      INNER JOIN transaction_chunks USING (userid, trnid)
      INNER JOIN chunks USING (userid)
    WHERE transactions.userid = :userid
"""
