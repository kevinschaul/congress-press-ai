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

# Classify AI mention sentiment using LLM (skips already-classified records)
classify *args:
    python scripts/classify.py {{args}}

# Run sentiment eval against manually labeled data/eval/sentiment-eval.csv
eval:
    OPENAI_BASE_URL=http://box.local:1112/v1 OPENAI_API_KEY=local \
        uv run --with inspect-ai --with openai \
        inspect eval scripts/eval_classify.py --model openai/gpt-oss-20b

