# FastAPI Ecommerce

Учебный проект интернет-магазина для изучения **FastAPI**.

Проект демонстрирует базовую архитектуру backend-приложения:

- REST API на FastAPI
- Работа с PostgreSQL через SQLAlchemy
- Миграции базы данных через Alembic
- JWT-аутентификация
- Хеширование паролей
- Разделение проекта на модули (routers, models, schemas)

---

# Стек технологий

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- Passlib
- JWT
- Uvicorn

---

# Установка и запуск проекта

## 1. Клонировать репозиторий

```bash
git clone https://github.com/YuriATitov/fastapi_ecommerce.git
cd fastapi_ecommerce
```


## 2. Создать виртуальное окружение

```python
python -m venv venv
source venv/bin/activate
```

## 3. Установить зависимости

```bash
pip install -r requirements.txt
```

# Настройка переменных окружения

В корне проекта необходимо создать файл:

.env

Пример содержимого:

```
SECRET_KEY=your_secret_key

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db_name

DB_USER=user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=db_name
```

Файл .env не добавляется в git и используется только локально.


# Миграции базы данных

```bash
alembic upgrade head
```


Если база создаётся впервые, Alembic создаст все таблицы.


# Запуск приложения

```bash

uvicorn app.main:app --reload

```

# Структура проекта
```
fastapi_ecommerce
│
├── app
│   ├── routers
│   │   ├── categories.py
│   │   ├── products.py
│   │   ├── users.py
│   │   └── reviews.py
│   │
│   ├── models
│   │
│   ├── schemas
│   │
│   ├── auth.py
│   ├── database.py
│   └── main.py
│
├── migrations
│   └── versions
│
├── alembic.ini
├── requirements.txt
├── .gitignore
└── README.md
```