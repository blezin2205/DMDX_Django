# Беремо офіційну легку версію Python 
FROM python:3.11-slim

# Забороняємо Python створювати зайві кеш-файли і виводимо логи напряму
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Створюємо папку для проєкту всередині контейнера
WORKDIR /app

# Спочатку копіюємо Docker-залежності і встановлюємо їх
COPY requirements_docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі інші файли проєкту
COPY . .