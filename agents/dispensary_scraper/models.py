"""Data models for the dispensary scraper."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


class ProductData(BaseModel):
    """Core product data structure matching notebook schema."""
    
    state: str = Field(default="FL", description="State code")
    store: str = Field(..., description="Store name")
    subcategory: str = Field(..., description="Product subcategory")
    name: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Product brand")
    strain_type: Optional[str] = Field(None, description="Strain type (Indica, Sativa, Hybrid)")
    thc_pct: Optional[float] = Field(None, description="THC percentage")
    size_raw: Optional[str] = Field(None, description="Raw size string (e.g., '3.5g')")
    grams: Optional[float] = Field(None, description="Weight in grams")
    price: Optional[float] = Field(None, description="Price in dollars")
    price_per_g: Optional[float] = Field(None, description="Price per gram")
    url: Optional[str] = Field(None, description="Product URL")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scraping timestamp")
    
    def calculate_price_per_g(self) -> None:
        """Calculate price per gram if both price and grams are available."""
        if self.price and self.grams and self.grams > 0:
            self.price_per_g = round(self.price / self.grams, 2)


class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""
    
    base_url: str = Field(default="https://www.trulieve.com")
    dispensaries_url: str = Field(default="https://www.trulieve.com/dispensaries")
    categories: List[Dict[str, str]] = Field(
        default=[
            {
                "url": "/category/flower/whole-flower",
                "subcategory": "Whole Flower",
                "prefix": "trulieve_FL_whole_flower"
            },
            {
                "url": "/category/flower/pre-rolls",
                "subcategory": "Pre-Rolls",
                "prefix": "trulieve_FL_pre_rolls"
            },
            {
                "url": "/category/flower/minis",
                "subcategory": "Ground & Shake",
                "prefix": "trulieve_FL_ground_shake"
            }
        ]
    )
    output_dir: str = Field(default="~/local/trulieve/")
    headless: bool = Field(default=True)
    rate_limit_delay: Tuple[int, int] = Field(default=(700, 1500))


class ScrapingResult(BaseModel):
    """Result of a scraping operation."""
    
    success: bool = Field(..., description="Whether scraping was successful")
    products: List[ProductData] = Field(default=[], description="Scraped products")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    categories_scraped: int = Field(default=0, description="Number of categories scraped")
    stores_scraped: int = Field(default=0, description="Number of stores scraped")
    total_products: int = Field(default=0, description="Total products scraped")
    duration_seconds: Optional[float] = Field(None, description="Scraping duration")
    
    def __post_init__(self):
        """Update counts after initialization."""
        self.total_products = len(self.products)
        
        
class StoreInfo(BaseModel):
    """Information about a dispensary store."""
    
    name: str = Field(..., description="Store name")
    url: str = Field(..., description="Store URL")
    location: Optional[str] = Field(None, description="Store location")
    state: str = Field(default="FL", description="State code")