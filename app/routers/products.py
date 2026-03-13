from fastapi import APIRouter, Depends, HTTPException, status 
from sqlalchemy import select, update 
from sqlalchemy.orm import Session 
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.categories import Category as CategoryModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.db_depends import get_db
from app.db_depends import get_async_db
from app.auth import get_current_seller

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags = ["products"],
)

@router.get("/", response_model= list[ProductSchema], status_code= status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    query = await db.scalars(select(ProductModel).where(ProductModel.is_active == True))
    return query.all()
    
@router.post("/", response_model= ProductSchema, status_code=status.HTTP_201_CREATED) 
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_seller)):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """ 
    # Проверка существоваяния категории 
    cat_query = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True))
    db_cat = cat_query.first()
    
    if db_cat is None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "Category not found or inactive")
    
    db_product = ProductModel(**product.model_dump(), seller_id =current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product
    
    
@router.get("/category/{category_id}", response_model= list[ProductSchema], status_code= status.HTTP_200_OK)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    cat_query = await db.scalars(select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True))
    db_cat = cat_query.first()
    
    if db_cat is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Category not found or inactive")
    
    all_cats = await db.scalars(select(ProductModel).where(ProductModel.category_id == category_id,
                                                 ProductModel.is_active == True))
    return all_cats.all()
    

@router.get("/{product_id}", response_model= ProductSchema, status_code= status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    prd_query = await db.scalars(select(ProductModel).where(ProductModel.id == product_id, 
                                           ProductModel.is_active == True))
    db_prd = prd_query.first()
    
    if db_prd is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Product not found")
    
    # Проверяем активная ли категория у товара
    cat_query = await db.scalars(select(CategoryModel).where(CategoryModel.is_active == True,
                                            CategoryModel.id == db_prd.category_id))
    db_cat = cat_query.first()
    
    if db_cat is None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="Category is not found or inactive")
    
    return db_prd
    

@router.put("/{product_id}", response_model= ProductSchema, status_code= status.HTTP_200_OK)
async def update_product(product_id: int, product: ProductCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_seller)):
    """
    Обновляет товар по его ID.
    """
    # Проверяем существование товара
    prd_query = await db.scalars(select(ProductModel).where(ProductModel.id == product_id, 
                                           ProductModel.is_active == True))
    db_prd = prd_query.first()
    
    if db_prd is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Product not found")
    
    if db_prd.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
    
    # Проверяем активная ли категория у товара
    cat_query = await db.scalars(select(CategoryModel).where(CategoryModel.is_active == True,
                                            CategoryModel.id == product.category_id))
    db_cat = cat_query.first()
    
    if db_cat is None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "Category is not found or inactive")
   
    # Обновление товара
    update_data = product.model_dump(exclude_unset= True)
    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(db_prd)
    return db_prd


@router.delete("/{product_id}", response_model=ProductSchema)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_seller)):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    # Проверяем, существует ли активный товар
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = product_result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail= "You can only delete your own products")
    # Проверяем, существует ли активная категория
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id,
                                    CategoryModel.is_active == True)
    )
    category = category_result.first()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Category not found or inactive")

    # Устанавливаем is_active=False
    product.is_active = False
    await db.commit()
    await db.refresh(product)  # Для возврата is_active = False
    return product
