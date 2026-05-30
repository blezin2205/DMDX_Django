#!/bin/bash

# Встановлюємо пароль локальної БД
export PGPASSWORD="4646"

# Назви
HEROKU_APP="dmdxstorage"
LOCAL_DB="dmdx"
LOCAL_USER="postgres"

echo "🛑 Переконайтеся, що ваш локальний Django-сервер та pgAdmin вимкнені!"
echo "🗑️  Видаляємо стару локальну базу $LOCAL_DB (якщо вона існує)..."

# Видаляємо локальну БД
dropdb -U $LOCAL_USER -h localhost --if-exists $LOCAL_DB

echo "📥 Починаємо завантаження бази даних з $HEROKU_APP в локальну $LOCAL_DB..."

# Затягуємо нову БД
heroku pg:pull DATABASE_URL $LOCAL_DB --app $HEROKU_APP

echo "✅ Синхронізація успішно завершена!"