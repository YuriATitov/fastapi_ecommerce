import os 
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Строка подключения для SQLite
DATABASE_URL = "sqlite:///ecomerce.db"

# Создаём Engine
engine = create_engine(DATABASE_URL, echo = True)

# Настраиваем фабрику сеансов
SessionLocal = sessionmaker(bind = engine)

# --------------- Асинхронное подключение к PostgreSQL -------------------------
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()
# Строка подключения для PostgreSQl
# для postgress формат DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/ecommerce_db"
DATABASE_URL = os.getenv("DATABASE_URL")

# Создаём Engine
async_engine = create_async_engine(DATABASE_URL, echo = True) # echo False в продакшене, для оптимизации

# Настраиваем фабрику сеансов
async_session_maker = async_sessionmaker(async_engine, expire_on_commit= False, class_= AsyncSession)



# Определяем базовый класс для моделей
class Base(DeclarativeBase):
    pass

