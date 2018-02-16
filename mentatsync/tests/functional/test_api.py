# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import uuid
import random
import string

from mozsvc.tests.support import FunctionalTestCase

from mentatsync.tests.functional.support import run_live_functional_tests


_ASCII = string.ascii_letters + string.digits

ROOT_TRANSACTION = "00000000-0000-0000-0000-000000000000"


def randtext(size=10):
    return ''.join([random.choice(_ASCII) for i in range(size)])


def randid():
    return str(uuid.uuid4())


class TestAPI(FunctionalTestCase):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.userid = randid()
        self.root = '/0.1/{}'.format(self.userid)

    def get_configurator(self):
        config = super(TestAPI, self).get_configurator()
        config.include("mentatsync")
        return config

    def test_basic_creation_of_new_transactions(self):
        # Initially, head is the empty root transaction.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], ROOT_TRANSACTION)

        # We can upload some chunks.
        self.app.put(self.root + "/chunks/aaaaaaaa",
                     "ayayayayayayayayayayayaya", status=201)
        self.app.put(self.root + "/chunks/bbbbbbbb",
                     "beebeebeebeebeebeebeebeebee", status=201)

        # And link them into a transaction.
        trn1 = randid()
        self.app.put_json(self.root + "/transactions/" + trn1, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["bbbbbbbb", "aaaaaaaa"],
        })

        # We can add a second transaction descending from the first.
        self.app.put(self.root + "/chunks/cccccccc",
                     "sisisisisisisisisisi", status=201)

        trn2 = randid()
        self.app.put_json(self.root + "/transactions/" + trn2, {
            "parent": trn1,
            "chunks": ["cccccccc"],
        })

        # We can commit the second transaction as the new head.
        self.app.put_json(self.root + "/head", {
            "head": trn2,
        }, status=204)

        # It will become the new head.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], trn2)

        # And we can fetch all transactions from root to head.
        resp = self.app.get(self.root + "/transactions")
        self.assertEqual(resp.json["transactions"], [trn1, trn2])

        # As well as from an intermediate transaction.
        resp = self.app.get(self.root + "/transactions?from=" + trn1)
        self.assertEqual(resp.json["transactions"], [trn2])

        # And can fetch all the chunks to download a given transaction.
        resp = self.app.get(self.root + "/transactions/" + trn1)
        self.assertEquals(resp.json["chunks"], ["bbbbbbbb", "aaaaaaaa"])

        resp = self.app.get(self.root + "/chunks/bbbbbbbb")
        self.assertEquals(resp.body, "beebeebeebeebeebeebeebeebee")

    def test_multiple_head_increments(self):
        # Initially, head is the empty root transaction.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], ROOT_TRANSACTION)

        # We can upload some chunks.
        self.app.put(self.root + "/chunks/aaaaaaaa",
                     "ayayayayayayayayayayayaya", status=201)
        self.app.put(self.root + "/chunks/bbbbbbbb",
                     "beebeebeebeebeebeebeebeebee", status=201)

        # And link them into a transaction.
        trn1 = randid()
        self.app.put_json(self.root + "/transactions/" + trn1, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["bbbbbbbb", "aaaaaaaa"],
        })

        # And make it the new head.
        self.app.put_json(self.root + "/head", {
            "head": trn1,
        }, status=204)

        # It will become the new head.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], trn1)

        # We can add a second transaction descending from the first.
        self.app.put(self.root + "/chunks/cccccccc",
                     "sisisisisisisisisisi", status=201)

        trn2 = randid()
        self.app.put_json(self.root + "/transactions/" + trn2, {
            "parent": trn1,
            "chunks": ["cccccccc"],
        })

        # We can commit the second transaction as the new head.
        self.app.put_json(self.root + "/head", {
            "head": trn2,
        }, status=204)

        # It will become the new head.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], trn2)

        # We can add a third transaction descending from the second.
        trn3 = randid()
        self.app.put_json(self.root + "/transactions/" + trn3, {
            "parent": trn2,
            "chunks": ["cccccccc", "aaaaaaaa"],
        })

        # But not set is as the new head.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], trn2)

        # We can add a fourth transaction descending from the third.
        trn4 = randid()
        self.app.put_json(self.root + "/transactions/" + trn4, {
            "parent": trn3,
            "chunks": ["cccccccc", "bbbbbbbb"],
        })

        # We can commit the fourth transaction as the new head.
        self.app.put_json(self.root + "/head", {
            "head": trn4,
        }, status=204)

        # It will become the new head.
        resp = self.app.get(self.root + "/head")
        self.assertEqual(resp.json["head"], trn4)

    def test_cant_commit_conflicting_heads(self):
        self.app.put(self.root + "/chunks/xx", "xx")
        trn1 = randid()
        self.app.put_json(self.root + "/transactions/" + trn1, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["xx"],
        })
        trn2 = randid()
        self.app.put_json(self.root + "/transactions/" + trn2, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["xx"],
        })
        self.app.put_json(self.root + "/head", {
            "head": trn1,
        })
        self.app.put_json(self.root + "/head", {
            "head": trn2,
        }, status=409)

    def test_cant_commit_a_head_with_descendants(self):
        self.app.put(self.root + "/chunks/xx", "xx")
        trn1 = randid()
        self.app.put_json(self.root + "/transactions/" + trn1, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["xx"],
        })
        trn2 = randid()
        self.app.put_json(self.root + "/transactions/" + trn2, {
            "parent": trn1,
            "chunks": ["xx"],
        })
        self.app.put_json(self.root + "/head", {
            "head": trn1,
        }, status=409)

    def test_cant_reference_nonexistent_chunk(self):
        trn1 = randid()
        self.app.put_json(self.root + "/transactions/" + trn1, {
            "parent": ROOT_TRANSACTION,
            "chunks": ["xx"],
        }, status=404)  # XXX TODO: should be a 400 error, not 404

    def test_cant_descend_from_nonexistent_transaction(self):
        self.app.put(self.root + "/chunks/xx", "xx")
        trn1 = randid()
        trn2 = randid()
        self.app.put_json(self.root + "/transactions/" + trn2, {
            "parent": trn1,
            "chunks": ["xx"],
        }, status=409)  # XXX TODO: should be a 400 error, not 409


if __name__ == "__main__":
    # When run as a script, this file will execute the
    # functional tests against a live webserver.
    res = run_live_functional_tests(TestAPI, sys.argv)
    sys.exit(res)
