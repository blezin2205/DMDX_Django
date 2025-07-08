# API Documentation

## Аутентифікація

### Логін
**POST** `/api/login`

**Body:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "token": "your_django_token",
    "jwt_token": "your_jwt_token",
    "user": {
        "id": 1,
        "username": "your_username",
        "email": "your_email@example.com",
        "first_name": "Your",
        "last_name": "Name"
    }
}
```

### Логаут
**POST** `/api/logout`

**Headers:**
```
Authorization: Token your_django_token
```

**Response:**
```json
{
    "message": "Successfully logged out"
}
```

### Отримання профілю користувача
**GET** `/api/profile`

**Headers:**
```
Authorization: Token your_django_token
```
або
```
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
    "id": 1,
    "username": "your_username",
    "email": "your_email@example.com",
    "first_name": "Your",
    "last_name": "Name"
}
```

### Оновлення JWT токена
**POST** `/api/refresh-token`

**Headers:**
```
Authorization: Token your_django_token
```

**Response:**
```json
{
    "jwt_token": "new_jwt_token",
    "message": "Token refreshed successfully"
}
```

## Товари (Supplies)

### Отримання всіх товарів
**GET** `/api/supplies`

**Headers:**
```
Authorization: Token your_django_token
```
або
```
Authorization: Bearer your_jwt_token
```

### Додавання товару
**POST** `/api/supplies`

**Headers:**
```
Authorization: Token your_django_token
```

**Body:**
```json
{
    "name": "Товар",
    "supplyLot": "LOT123",
    "count": 10,
    "expiredDate": "25-12-2024"
}
```

### Отримання деталей товару
**PUT** `/api/{id}/`

**Headers:**
```
Authorization: Token your_django_token
```

### Отримання інформації про бронювання товару
**GET** `/api/supply/{supply_id}/hold-info/`

**Headers:**
```
Authorization: Token your_django_token
```

## Загальні товари (General Supplies)

### Отримання всіх загальних товарів
**GET** `/api/general-supplies`

**Headers:**
```
Authorization: Token your_django_token
```

## Замовлення (Orders)

### Отримання всіх замовлень
**GET** `/api/orders`

**Headers:**
```
Authorization: Token your_django_token
```

### Отримання товарів у замовленні
**GET** `/api/orders/{order_id}`

**Headers:**
```
Authorization: Token your_django_token
```

## Організації (Places)

### Отримання всіх організацій
**GET** `/api/places`

**Headers:**
```
Authorization: Token your_django_token
```

### Додавання організації
**POST** `/api/places`

**Headers:**
```
Authorization: Token your_django_token
```

**Body:**
```json
{
    "name": "Назва організації",
    "city": "Київ",
    "address": "Адреса"
}
```

## Сканування товарів

### Пошук товарів для сканування
**GET** `/api/supplies_add_from_scan`

**Headers:**
```
Authorization: Token your_django_token
```

**Body:**
```json
{
    "searchText": "код або назва товару"
}
```

### Додавання товару зі сканування
**POST** `/api/supplies_add_from_scan`

**Headers:**
```
Authorization: Token your_django_token
```

**Body:**
```json
{
    "smn": "SMN123",
    "supplyLot": "LOT123",
    "expiredDate": "25-12-2024",
    "count": 5
}
```

## Приклади використання

### JavaScript (fetch)
```javascript
// Логін
const loginResponse = await fetch('/api/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        username: 'your_username',
        password: 'your_password'
    })
});

const loginData = await loginResponse.json();
const token = loginData.token;
const jwtToken = loginData.jwt_token;

// Використання токена для запитів
const suppliesResponse = await fetch('/api/supplies', {
    headers: {
        'Authorization': `Token ${token}`
    }
});

// Або використання JWT токена
const suppliesResponse = await fetch('/api/supplies', {
    headers: {
        'Authorization': `Bearer ${jwtToken}`
    }
});
```

### Python (requests)
```python
import requests

# Логін
login_data = {
    'username': 'your_username',
    'password': 'your_password'
}

response = requests.post('http://localhost:8000/api/login', json=login_data)
data = response.json()
token = data['token']
jwt_token = data['jwt_token']

# Використання токена для запитів
headers = {'Authorization': f'Token {token}'}
# або
headers = {'Authorization': f'Bearer {jwt_token}'}

supplies_response = requests.get('http://localhost:8000/api/supplies', headers=headers)
supplies = supplies_response.json()
```

## Коди помилок

- `401 Unauthorized` - Неправильні облікові дані або відсутній токен
- `403 Forbidden` - Недостатньо прав для доступу
- `404 Not Found` - Ресурс не знайдено
- `400 Bad Request` - Неправильні дані запиту
- `500 Internal Server Error` - Внутрішня помилка сервера 