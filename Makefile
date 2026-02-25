DGX=23uec552@172.22.2.151
DGX_DIR=/home/23uec552/Synapse

# ── One-time setup ──────────────────────────────────────────────────────────
# Clone repo and create virtualenv on DGX
dgx-init:
	ssh $(DGX) "git clone https://github.com/Axe-08/Synapse.git $(DGX_DIR) && cd $(DGX_DIR) && python3 -m venv venv && venv/bin/pip install -r requirements.txt"

# ── Every session ────────────────────────────────────────────────────────────
# (1) git push from laptop, then:
dgx-pull:
	ssh $(DGX) "cd $(DGX_DIR) && git pull && venv/bin/pip install -r requirements.txt -q"

# ── SSH tunnel: laptop:5432 → DGX postgres:5432 ─────────────────────────────
# Run in background: make tunnel &
tunnel:
	ssh -N -L 5432:localhost:5432 $(DGX)

# ── DGX Docker ───────────────────────────────────────────────────────────────
dgx-up:
	ssh $(DGX) "cd $(DGX_DIR) && docker compose up -d --build"

dgx-down:
	ssh $(DGX) "cd $(DGX_DIR) && docker compose down"

dgx-logs:
	ssh $(DGX) "cd $(DGX_DIR) && docker compose logs -f synapse"

dgx-pg-logs:
	ssh $(DGX) "cd $(DGX_DIR) && docker compose logs -f postgres"

# ── Database ─────────────────────────────────────────────────────────────────
# Run after tunnel is open
init-db:
	python create_database.py --postgres

# ── Local dev (SQLite, no tunnel needed) ─────────────────────────────────────
init-db-local:
	python create_database.py

test:
	venv/bin/python -m pytest tests/unit/ tests/integration/ -q

.PHONY: dgx-init dgx-pull tunnel dgx-up dgx-down dgx-logs dgx-pg-logs init-db init-db-local test
