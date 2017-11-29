# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from pyramid.security import Allow
from pyramid.request import Response
from pyramid.httpexceptions import HTTPNotFound, HTTPConflict

from cornice import Service

from mentatsync.storage import (
    ROOT_TRANSACTION,
    get_storage,
    NotFoundError,
    ConflictError,
)


UUID_REGEX = "[a-z0-9-]{36}"  # XXX TODO: make more precise...
CHUNKID_REGEX = "[a-z0-9-]{1,64}"  # XXX TODO: make more precise...


def default_acl(request):
    """Default ACL: only the owner is allowed access.

    This must be a function, not a method on MentatSyncService, because
    cornice takes a copy of it when constructing the pyramid view.
    """
    return [(Allow, request.matchdict["userid"], "owner")]


def convert_storage_errors(func):
    def wrapped(*args, **kwds):
        try:
            return func(*args, **kwds)
        except NotFoundError:
            raise HTTPNotFound()
        except ConflictError:
            raise HTTPConflict()
    return wrapped


class MentatSyncService(Service):

    def __init__(self, **kwds):
        # Configure DRY defaults for the path.
        kwds["path"] = self._configure_the_path(kwds["path"])
        # Ensure all views require authenticated user.
        kwds.setdefault("permission", "owner")
        kwds.setdefault("acl", default_acl)
        super(MentatSyncService, self).__init__(**kwds)

    def _configure_the_path(self, path):
        """Helper method to apply default configuration of the service path."""
        # Insert pattern-matching regexes into the path
        path = path.replace("{transaction}",
                            "{transaction:" + UUID_REGEX + "}")
        path = path.replace("{chunk}",
                            "{chunk:" + CHUNKID_REGEX + "}")
        # Add path prefix for the API version number and userid.
        path = "/{api:0\\.1}/{userid:" + UUID_REGEX + "}" + path
        return path


# We define a simple "It Works!" view at the site root, so that
# it's easy to see if the service is correctly running.
site_root = Service(name="site_root", path="/")


@site_root.get()
def get_site_root(request):
    return "It Works!  MentatSync is successfully running on this host."


# Now we define the per-user service API paths.

root = MentatSyncService(name="root", path="")

head = MentatSyncService(name="head", path="/head")

transactions = MentatSyncService(name="transactions", path="/transactions")

transaction = MentatSyncService(name="transaction",
                                path="/transactions/{transaction}")

chunk = MentatSyncService(name="chunk", path="/chunks/{chunk}")


@root.get()
def get_root(request):
    return "ok"


@head.get(renderer="json")
def get_head(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    return {
        "head": storage.get_head(userid)
    }


@head.put()
@convert_storage_errors
def put_head(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    new_head = json.loads(request.body)["head"]
    storage.set_head(userid, new_head)
    request.response.status = 204
    return request.response


@transactions.get(renderer="json")
@convert_storage_errors
def get_transactions(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    frm = request.GET.get("from", ROOT_TRANSACTION)
    limit = int(request.GET.get("limit", "100"))
    return {
        "from": frm,
        "limit": limit,
        "transactions": list(storage.get_transactions(userid, frm, limit)),
    }


@transaction.get(renderer="json")
@convert_storage_errors
def get_transaction(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    trnid = request.matchdict["transaction"]
    trn = storage.get_transaction(userid, trnid)
    return {
        "id": trn["id"],
        "seq": trn["seq"],
        "parent": trn["parent"],
        "chunks": trn["chunks"]
    }


@transaction.put()
@convert_storage_errors
def put_transaction(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    trnid = request.matchdict["transaction"]
    params = json.loads(request.body)
    parent = params["parent"]
    chunks = params["chunks"]
    storage.create_transaction(userid, trnid, parent, chunks)
    request.response.status = 201
    return request.response


@chunk.get()
@convert_storage_errors
def get_chunk(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    chunk = request.matchdict["chunk"]
    payload = storage.get_chunk(userid, chunk)
    return Response(payload)


@chunk.put()
@convert_storage_errors
def put_chunk(request):
    storage = get_storage(request)
    userid = request.matchdict["userid"]
    chunk = request.matchdict["chunk"]
    storage.create_chunk(userid, chunk, request.body)
    request.response.status = 201
    return request.response
