from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, func, DateTime, Computed, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(primary_key= True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable= True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(200), nullable = True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable= False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 1), default= 0.0, nullable= False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default= func.now(), nullable= False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    tsv: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR,
        Computed(
            """
            setweight(to_tsvector('english', coalesce(name, '')), 'A')
            || 
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
            """,
            persisted= True,
        ),
        nullable=False,
    )
    
    category: Mapped["Category"] = relationship(back_populates="products")
    seller: Mapped["User"] = relationship("User", back_populates= "products")
    reviews: Mapped[list["Review"]] = relationship(
        "Review", 
        back_populates="product"
    )
    cart_items: Mapped[list["CartItems"]] = relationship("CartItem", back_populates= "product", cascade= "all, delete-orphan")
    
    __table_args__ = (
        Index("ix_products_tsv_gin", "tsv", postgresql_using="gin"),
    )
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates= "product")