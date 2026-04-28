# 1. We place ourselves in the right directory
cd "$(dirname "$0")"

# 2. Activate API
exec uvicorn src.api.main:app --host 0.0.0.0  --port 8000
