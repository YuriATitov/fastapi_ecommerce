from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, update, desc, func, and_
from sqlalchemy.orm import Session 
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.categories import Category as CategoryModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.db_depends import get_db
from app.db_depends import get_async_db
from app.auth import get_current_seller

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags = ["products"],
)

@router.get("/", response_model= ProductList, status_code= status.HTTP_200_OK)
async def get_all_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int | None = Query(None, description="ID категории для фильтрации"),
    search: str | None = Query(None, min_length=1, description= "Поиск по названию товара"),
    min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
    max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
    in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
    seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
    sort_by_created_at: str | None = Query("asc", pattern="^(asc|desc)$", description= "Сортировка товаров по дате создания"),
    db: AsyncSession = Depends(get_async_db)
    ):

    """
    Возвращает список всех товаров.
    """
    # Проверка логики min_price <= max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "min_price не может быть больше max_price"
        )
        
    # Формируем список фильтров
    filters = [ProductModel.is_active == True]
    
    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)
        
    if sort_by_created_at is not None and sort_by_created_at == 'asc':
        order_by_clause = (ProductModel.created_at.asc())
    elif sort_by_created_at is not None and sort_by_created_at == 'desc':
        order_by_clause = (ProductModel.created_at.desc())
    else: 
        order_by_clause = (ProductModel.id)

    
    # Подсчёт общего количества с учётом фильтров


    total_query = select(func.count()).select_from(ProductModel).where(*filters)
    
    rank_col = None 
    if search:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(ProductModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")
            # total с учётом полнотекстового фильтра
            total_query = select(func.count()).select_from(ProductModel).where(*filters)
        
    total = await db.scalar(total_query) or 0
    
    # Основной запрос (если есть поиск — добавим ранг в выборку и сортировку)
    if rank_col is not None:
        product_query = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(product_query)
        rows = result.all()
        items = [row[0] for row in rows] # сами объекты
        # при желании можно вернуть ранг в ответе
        # ranks = [row.rank for row in rows]
    else:
        product_query = (
            select(ProductModel)
            .where(*filters)
            .order_by(order_by_clause)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.scalars(product_query)).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    
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
