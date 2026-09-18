.PHONY: setup deploy collect test verify demo-seed demo-reset help

PYTHON ?= python

help:
	@echo "NETRA — Developer & Judge Interface"
	@echo ""
	@echo "  make setup      Install backend dependencies and frontend modules"
	@echo "  make deploy     Build and deploy the SAM stack to AWS"
	@echo "  make collect    Execute the inventory collector once locally"
	@echo "  make test       Run complete unit test suite across all modules"
	@echo "  make verify     Execute the judge-facing verification suite (<2s proof)"
	@echo "  make demo-seed  Launch the c5.4xlarge runaway demonstration resource"
	@echo "  make demo-reset Terminate demo resources and clean demo state"
	@echo ""

setup:
	@echo "==> Setting up backend dependencies..."
	$(PYTHON) -m pip install -r backend/requirements.txt
	@if [ -f frontend/package.json ]; then \
		echo "==> Setting up frontend dependencies..."; \
		cd frontend && npm install; \
	fi

deploy:
	@echo "==> Building SAM application..."
	cd infra && sam build
	@echo "==> Deploying SAM application to AWS ap-south-1..."
	cd infra && sam deploy

collect:
	@echo "==> Running NETRA collector locally..."
	PYTHONPATH=backend $(PYTHON) -m netra.collector

test:
	@echo "==> Running backend test suite..."
	PYTHONPATH=backend $(PYTHON) -m pytest backend/tests/ -v

verify:
	@echo "==> Running NETRA proof verification..."
	PYTHONPATH=backend $(PYTHON) -m netra.verify

demo-seed:
	@echo "==> Seeding demo runaway resource..."
	PYTHONPATH=backend $(PYTHON) scripts/seed_demo.py

demo-reset:
	@echo "==> Resetting demo state..."
	PYTHONPATH=backend $(PYTHON) scripts/reset_demo.py
