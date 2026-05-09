from pydantic import BaseModel, Field
from typing import List, Optional

class EtsyPrice(BaseModel):
    amount: int
    divisor: int
    currency_code: str
    
    @property
    def float_value(self) -> float:
        if self.divisor == 0:
            return 0.0
        return self.amount / self.divisor

class EtsyListing(BaseModel):
    listing_id: int
    title: str
    tags: List[str] = Field(default_factory=list)
    price: EtsyPrice
    views: int = 0
    num_favorers: int = 0
    creation_timestamp: int

class EtsyListingsResponse(BaseModel):
    count: int
    results: List[EtsyListing]
