.PHONY: setup deploy collect test verify break demo-up demo-down demo-seed demo-reset help

PYTHON ?= python

help:
	@echo "NETRA — Developer & Judge Interface"
	@echo ""
	@echo "  make setup      Install backend dependencies and frontend modules"
	@echo "  make deploy     Build and deploy the SAM stack to AWS"
	@echo "  make collect    Execute the inventory collector once locally"
	@echo "  make test       Run complete unit test suite across all modules"
	@echo "  make verify     Execute the judge-facing verification suite (<2s proof)"
	@echo "  make break      Trigger runaway compute and prove sub-10s fast-path detection"
	@echo "  make demo-up    Deploy standalone demo stack (c5.4xlarge, orphaned EBS, protected)"
	@echo "  make demo-down  Tear down standalone demo stack to eliminate spend"
	@echo "  make demo-seed  Launch the c5.4xlarge runaway demonstration resource"
	@echo "  make demo-reset Terminate demo resources and clean demo state"
	@echo ""

setup:
	@echo "==> Setting up backend dependencies..."
	$(PYTHON) -m pip install -r backend/requirements.txt
	@if [ -f frontend/package.json ]; then \
		echo "==> Setting up frontend dependencies..."; \
		cd frontend && npm install; \
		cd frontend && npm run build; \
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

break:
	@echo "==> Injecting fault to demonstrate sub-10-second fast-path detection..."
	PYTHONPATH=backend $(PYTHON) scripts/break.py

demo-up:
	@echo "==> Deploying reproducible judge demo stack (≈₹70/hr)..."
	cd demo-stack && sam build && sam deploy --stack-name netra-demo-stack --resolve-s3 --capabilities CAPABILITY_IAM

demo-down:
	@echo "==> Destroying demo stack..."
	aws cloudformation delete-stack --stack-name netra-demo-stack --region ap-south-1

demo-seed:
	@echo "==> Seeding demo runaway resource..."
	PYTHONPATH=backend $(PYTHON) scripts/seed_demo.py

demo-reset:
	@echo "==> Resetting demo state..."
	PYTHONPATH=backend $(PYTHON) scripts/reset_demo.py

