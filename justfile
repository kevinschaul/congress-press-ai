help:
    @just --list

# Start observable framework
dev:
    npm run dev

# Install dependencies
install:
    npm install
    # Set up a symlink so that data also appears inside of observable/data
    cd observable && ln -s ../data data

# Run tests
test:
    npm run test

# Fetch AI keyword data; defaults to current month. e.g.: just fetch 2026-01 2026-02
fetch *months:
    python scripts/check_keywords.py $([ -z "{{months}}" ] && date +%Y-%m || echo "{{months}}")


