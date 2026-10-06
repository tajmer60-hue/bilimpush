#!/usr/bin/env bash
# Запуск Bilim+ (backend + frontend одним сервером)
set -e
cd "$(dirname "$0")/backend"

# создать/обновить venv при желании:
# python3 -m venv .venv && source .venv/bin/activate
pip3 install -q -r requirements.txt

# Секреты для продакшена (в dev используются значения по умолчанию):
# export BILIM_SECRET="сгенерируй-случайную-строку"
# export BILIM_ADMIN_EMAIL="admin@example.com"
# export BILIM_ADMIN_PASSWORD="сильный-пароль"

echo "🎓 Bilim+ запускается на http://localhost:8000"
exec python3 run.py
