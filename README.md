# Prototype server API for syncing data between mentat stores

First version, highly speculative API, written in python so that
we can re-use code from server-syncstorage.  Expect everything here
to change substantially over time.  I'd like to do a version in rust.

Basic conceptual model:

* Users are identified by uuid.  There is no authentication, knowing the uuid is enough to access the data.
* Clients are building a strictly-ordered sequence of *transactions*, which are also identified by uuid.
  * There is a special "root" transaction with id "00000000-0000-0000-0000-000000000000"
* Clients upload data in *chunks*, identified by SHA256 content hash.  Chunks are immutable and opaque.
* Each transaction contains a strictly-ordered sequence of chunks, a parent transaction, and a sequence number.
  * Each trasaction's sequence number is strictly greater than that of its parent
* The transaction with the highest sequence number is the *HEAD*.
* Clients can make their transactions visible to others by atomically advancing *HEAD* to a new transaction.
  * The new HEAD transaction must be a proper descendant of the current HEAD.
  * The new HEAD transaction must not itself have any descendants.
* Clients can query for:
  * the list of transactions between a given transaction and the current HEAD
  * the list of chunks contained in a given transaction
  * the contents of a given chunk
* Clients cannot query for:
  * Transactions that descend from the current HEAD; these are in-progress and not yet visible to others.

Basic operations:

* `GET /0.1/{user}/` - get basic info about the store; currently does nothing
* `GET /0.1/{user}/head` - get transaction id of the current head
* `PUT /0.1/{user}/head` - update current head to new transaction id
* `GET /0.1/{user}/transactions` - get transaction ids in increasing sequence order
  * `?from={trn}` - start listing from a particular transaction id
  * `?limit={limit}` - list at most the given number of transactions
* `PUT /0.1/{user}/transactions/{trn}` - create a new transaction with given id
* `GET /0.1/{user}/transactions/{trn}` - get metadata for a given transaction
* `PUT /0.1/{user}/chunks/{chunk}` - create a new chunk with given id
* `GET /0.1/{user}/chunks/{chunk}` - get contents of a given chunk

Clients can pull down changes by doing something like:

* Get list of new transactions via `GET /transactions?from={prev_head}`
* For each transaction:
  * Get list of chunks via `GET /transactions/{trn}`
  * For each chunk:
    * Get chunk contents via `GET /chunks/{chunk}`
    * Apply chunk contents via the magic of mentat

And can then upload new changes by doing something like:

* For each outgoing transaction:
  * Locally construct the appropriate set of chunks
  * For each chunk:
    * Upload it via `PUT /chunks/{chunk}`
  * Upload transaction metadata via `PUT /transactions/{trn}`
* Make the final transaction the new head via `PUT /head`
  * This will be rejected if it doesn't descend from the current head
  * If rejected due to concurrent change, abort and resync

Notes and things to figure out:

* Should we add some sort of batching API to avoid O(N^2) HTTP requests during fetch, or rely on pipelining/HTTP2/whatever to make this efficient?
* Rules for garbage-collecting abandoned chunks, dead transactions?


