VIRTUALENV = virtualenv
NOSE = local/bin/nosetests -s
TESTS = mentatsync/tests
PYTHON = local/bin/python
PIP = local/bin/pip
PIP_CACHE = /tmp/pip-cache.${USER}
BUILD_TMP = /tmp/mentatsync-build.${USER}
MOZSVC_SQLURI = sqlite:///:memory:

export MOZSVC_SQLURI

INSTALL = ARCHFLAGS=$(ARCHFLAGS) $(PIP) install -U

.PHONY: all build test

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute ./local
	$(INSTALL) --upgrade Distribute pip
	$(INSTALL) -r requirements.txt
	$(PYTHON) ./setup.py develop

test:
	$(INSTALL) nose flake8
	# Check that flake8 passes before bothering to run anything.
	# This can really cut down time wasted by typos etc.
	./local/bin/flake8 mentatsync
	# Run the actual testcases.
	$(NOSE) $(TESTS)
	# Test that live functional tests can run correctly, by actually
	# spinning up a server and running them against it.
	./local/bin/gunicorn --paste ./mentatsync/tests/tests.ini --workers 1 --worker-class mozsvc.gunicorn_worker.MozSvcGeventWorker & SERVER_PID=$$! ; sleep 2 ; ./local/bin/python mentatsync/tests/functional/test_api.py http://localhost:5013 ; kill $$SERVER_PID
