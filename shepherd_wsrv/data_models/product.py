# TODO: just for prototype
from typing import Optional

from beanie import Document, Indexed
from pydantic import BaseModel


class Category(BaseModel):
    name: str
    description: str


# This is the model that will be saved to the database
class Product(Document):
    name: str                          # You can use normal types just like in pydantic
    description: Optional[str] = None
    price: Indexed(float)              # You can also specify that a field should correspond to an index
    category: Category                 # You can include pydantic models as well
    # name: Annotated[str, Indexed(unique=True)]
