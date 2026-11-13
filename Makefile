.PHONY: setup seed reset-demo dev test e2e lint clean

setup:
	@echo "Setting up backend and frontend dependencies..."
	cd backend && python -m pip install -r requirements.txt
	cd frontend && npm install

seed:
	@echo "Seeding Karnataka comprehensive demo dataset..."
	cd backend && python -m app.seed.full_seed

reset-demo:
	@echo "Resetting demo database and re-seeding..."
	cd backend && alembic downgrade base
	cd backend && alembic upgrade head
	cd backend && python -m app.seed.full_seed

sample-docs:
	@echo "Generating and uploading Phase 2 sample audit documents..."
	cd backend && python -m app.seed.sample_docs
	cd backend && python -m app.seed.upload_samples

dev:
	@echo "Starting development servers..."
	@echo "Run backend: cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "Run frontend: cd frontend && npm run dev"

test:
	@echo "Running backend test suite..."
	cd backend && pytest -v
	@echo "Running frontend unit/component tests..."
	cd frontend && npm test

e2e:
	@echo "Running Playwright smoke tests..."
	cd frontend && npx playwright test

clean:
	@echo "Cleaning cache and build artifacts..."
	rm -rf backend/__pycache__ backend/.pytest_cache frontend/dist frontend/node_modules/.vite
