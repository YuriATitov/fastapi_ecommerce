from decimal import Decimal
from sqlalchemy import String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base 

class Review(Base):
    __tablename__ = "reviews"
    
    id: Mapped[int] = mapped_column(Integer, primary_key= True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable= False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable= False)
    comment: Mapped[str] = mapped_column(Text, nullable= False)
    comment_date: Mapped[datetime] = mapped_column(DateTime, nullable= False, default= datetime.now())
    grade: Mapped[int] = mapped_column(Integer, nullable= False)
    is_active: Mapped[bool] = mapped_column(Boolean, default= True)

    product: Mapped["Product"] = relationship(
        back_populates="reviews"
    )
    user: Mapped["User"] = relationship(
        back_populates= "reviews"
    )
    