from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviews import Review as ReviewModel 
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.db_depends import get_db
from app.db_depends import get_async_db
from app.auth import get_current_user


# Создаём маршрутизатор для отзывов
router = APIRouter(
    #prefix="/reviews",
    tags= ["reviews"],
)

# Функция для расчета рейтинга 
async def update_rating(product_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.scalars(select(func.avg(ReviewModel.grade)).where(ReviewModel.product_id == product_id,
                                                                       ReviewModel.is_active == True))
    avg_rating = result.first() or 0.0 
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


@router.get("/reviews", response_model= list[ReviewSchema], status_code= status.HTTP_200_OK)
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    query = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    return query.all()

@router.get("/products/{product_id}/reviews", response_model= list[ReviewSchema], status_code= status.HTTP_200_OK)
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов на конкретный товар.
    """
    query = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True,
                                                     ReviewModel.product_id == product_id))
    db_review = query.all()
    
    if db_review is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Product is not found or inactive")
    
    return db_review

@router.post("/reviews", response_model= ReviewSchema, status_code= status.HTTP_201_CREATED)
async def create_review(review: ReviewCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    """
    Создаёт новый отзыв, привязанный к текущему покупателю (только для 'buyer').
    """ 
    
    # Проверяем юзера, что он активен и с ролью buyer 
    if current_user.role != 'buyer':
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail= "Only users with role buyer can write review")
    
    # Проверяем активный ли товар к которому создается отзыв 
    product_query = await db.scalars(select(ProductModel).where(ProductModel.id == review.product_id,
                                                                ProductModel.is_active == True))
    db_product = product_query.first()
    
    if db_product is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Product is not found or inactive")
    
    
    # Проверяем есть ли у этого юзера уже опубликованный отзыв 
    review_query = await db.scalars(select(ReviewModel).where(ReviewModel.product_id == review.product_id,
                                                              ReviewModel.user_id == current_user.id,
                                                              ReviewModel.is_active == True))
    db_review = review_query.first()
    
    if db_review is not None: 
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail= "User can give only one review per product")
    
    
    # Проверяем границы оценки
    if review.grade != int(review.grade) or review.grade < 1 or review.grade > 5:
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_CONTENT, detail= "Grade is incorrect. Should be integer 1-5")
    
    
    review = ReviewModel(**review.model_dump(), user_id = current_user.id)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    # Обновляем рейтинг 
    await update_rating(review.product_id, db)
    
    return review
    
@router.delete("/reviews/{review_id}")
async def delete_review(review_id: int, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    """
    Выполняет мягкое удаление отзыва, если он принадлежит текущему юзеру или админу.
    """

    review_query = await db.scalars(select(ReviewModel).where(ReviewModel.id == review_id,
                                                              ReviewModel.is_active == True))
    review = review_query.first()
    
    # Проверяем существует ли активный отзыв
    if review is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Review not found or inactive")

    # Проверяем является ли клиент автором отзыва или админом 
    if current_user.role != 'admin' and review.user_id != current_user.id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail= "Only admin or user who create review can delete")
    
    review.is_active = False
    await db.commit()
    await db.refresh(review)
    
    await update_rating(review.product_id, db)
    
    return {"message": "Review deleted"}