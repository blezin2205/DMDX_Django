# DMDX CRM Desktop (Electron + React)

Окремий desktop-додаток для Windows на базі існуючого Django-проєкту.

## Що вже реалізовано

- Electron оболонка для desktop-режиму.
- React + TypeScript UI українською мовою.
- Онлайн-MVP: вхід через `POST /api/login`.
- Перевірка підключення до Django API.

## Налаштування API

1. Скопіюйте приклад оточення:

```bash
cp .env.example .env
```

2. Для dev-режиму використовуйте `.env`:

```env
VITE_API_BASE_URL=/
```

3. Для production build використовуйте `.env.production`:

```env
VITE_API_BASE_URL=https://dmdxstorage.herokuapp.com
```

Під час `vite build` буде використано саме `.env.production`.

## Розробка

```bash
npm install
npm run dev
```

Команда запускає одночасно Vite та Electron.

## Збірка для Windows

```bash
npm run build
```

Готовий інсталятор буде в папці `release`.

## Наступні кроки

- Додати повний auth-flow (refresh token, logout, session guard).
- Підключити реальні CRM-модулі (клієнти, угоди, задачі).
- Реалізувати офлайн-режим (локальна БД + синхронізація).
