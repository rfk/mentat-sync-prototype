# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
""" Base test class, with an instanciated app.
"""

import os
import sys
import optparse

import unittest2


def run_live_functional_tests(TestCaseClass, argv=None):
    """Execute the given suite of testcases against a live server."""
    if argv is None:
        argv = sys.argv

    usage = "Usage: %prog [options] <server-url>"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-x", "--failfast", action="store_true",
                      help="stop after the first failed test")
    parser.add_option("", "--config-file",
                      help="name of the config file in use by the server")

    try:
        opts, args = parser.parse_args(argv)
    except SystemExit, e:
        return e.args[0]
    if len(args) != 2:
        parser.print_usage()
        return 2

    os.environ["MOZSVC_TEST_REMOTE"] = args[1]
    if opts.config_file is not None:
        os.environ["MOZSVC_TEST_INI_FILE"] = opts.config_file

    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(TestCaseClass))
    runner = unittest2.TextTestRunner(
        stream=sys.stderr,
        failfast=opts.failfast,
    )
    res = runner.run(suite)
    if not res.wasSuccessful():
        return 1
    return 0


# Tell over-zealous test discovery frameworks that this isn't a real test.
run_live_functional_tests.__test__ = False
