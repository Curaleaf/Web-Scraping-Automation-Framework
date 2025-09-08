"""CSV storage operations for scraped data."""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import pandas as pd

from ..models import ProductData, ScrapingResult

logger = logging.getLogger(__name__)


class CSVStorage:
    """Handles CSV file storage operations."""
    
    def __init__(self, output_directory: str = "~/local/trulieve/"):
        """
        Initialize CSV storage.
        
        Args:
            output_directory: Base directory for CSV files
        """
        self.output_directory = Path(output_directory).expanduser()
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Create output directory if it doesn't exist."""
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Output directory ready: {self.output_directory}")
        except Exception as e:
            logger.error(f"Error creating output directory {self.output_directory}: {e}")
            raise
    
    def _generate_filename(self, prefix: str, timestamp: Optional[datetime] = None) -> str:
        """
        Generate CSV filename using the naming convention from notebook.
        Pattern: {OUT_PREFIX}-{date_time}.csv
        
        Args:
            prefix: File prefix (e.g., "trulieve_FL_whole_flower")
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            Generated filename
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        date_time = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}-{date_time}.csv"
    
    def save_products_to_csv(
        self,
        products: List[ProductData],
        prefix: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Save products to CSV file following notebook pattern.
        
        Args:
            products: List of ProductData to save
            prefix: File prefix for naming
            timestamp: Optional timestamp for filename
            
        Returns:
            Path to saved CSV file
            
        Raises:
            ValueError: If no products provided
            Exception: If save operation fails
        """
        if not products:
            raise ValueError("No products provided to save")
        
        try:
            # Generate filename
            filename = self._generate_filename(prefix, timestamp)
            filepath = self.output_directory / filename
            
            # Convert products to DataFrame
            df = self._products_to_dataframe(products)
            
            # Sort as in notebook: by store, brand, name, grams
            df = df.sort_values(["store", "brand", "name", "grams"], kind="stable")
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            
            logger.info(f"Saved {len(products)} products to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving products to CSV: {e}")
            raise
    
    def save_scraping_result(self, result: ScrapingResult, prefix: str) -> Optional[str]:
        """
        Save scraping result to CSV file.
        
        Args:
            result: ScrapingResult containing products and metadata
            prefix: File prefix for naming
            
        Returns:
            Path to saved CSV file or None if no products
        """
        if not result.products:
            logger.warning("No products in scraping result to save")
            return None
        
        return self.save_products_to_csv(result.products, prefix)
    
    def save_by_category(self, products: List[ProductData]) -> List[str]:
        """
        Save products grouped by category using appropriate prefixes.
        
        Args:
            products: List of ProductData to save
            
        Returns:
            List of saved file paths
        """
        if not products:
            return []
        
        # Group products by subcategory
        category_groups = {}
        for product in products:
            subcategory = product.subcategory
            if subcategory not in category_groups:
                category_groups[subcategory] = []
            category_groups[subcategory].append(product)
        
        # Define prefixes for each category (from PRP)
        category_prefixes = {
            "Whole Flower": "trulieve_FL_whole_flower",
            "Pre-Rolls": "trulieve_FL_pre_rolls",
            "Ground & Shake": "trulieve_FL_ground_shake"
        }
        
        saved_files = []
        timestamp = datetime.now()  # Use same timestamp for all files
        
        for subcategory, category_products in category_groups.items():
            try:
                prefix = category_prefixes.get(subcategory, f"trulieve_FL_{subcategory.lower().replace(' ', '_')}")
                filepath = self.save_products_to_csv(category_products, prefix, timestamp)
                saved_files.append(filepath)
                logger.info(f"Saved {len(category_products)} {subcategory} products")
            except Exception as e:
                logger.error(f"Error saving {subcategory} products: {e}")
                continue
        
        return saved_files
    
    def _products_to_dataframe(self, products: List[ProductData]) -> pd.DataFrame:
        """
        Convert list of ProductData to pandas DataFrame.
        
        Args:
            products: List of ProductData
            
        Returns:
            pandas DataFrame with product data
        """
        # Convert to list of dictionaries
        data = []
        for product in products:
            product_dict = product.model_dump()
            # Convert datetime to string for CSV storage
            if 'scraped_at' in product_dict and product_dict['scraped_at']:
                product_dict['scraped_at'] = product_dict['scraped_at'].isoformat()
            data.append(product_dict)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Ensure consistent column order matching notebook
        column_order = [
            "state", "store", "subcategory", "name", "brand",
            "strain_type", "thc_pct", "size_raw", "grams",
            "price", "price_per_g", "url", "scraped_at"
        ]
        
        # Reorder columns (only include columns that exist)
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        return df
    
    def load_products_from_csv(self, filepath: str) -> List[ProductData]:
        """
        Load products from CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of ProductData instances
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            Exception: If load operation fails
        """
        try:
            df = pd.read_csv(filepath)
            
            products = []
            for _, row in df.iterrows():
                # Convert row to dict and handle datetime
                product_dict = row.to_dict()
                
                # Parse datetime if present
                if 'scraped_at' in product_dict and pd.notna(product_dict['scraped_at']):
                    try:
                        product_dict['scraped_at'] = datetime.fromisoformat(product_dict['scraped_at'])
                    except (ValueError, TypeError):
                        product_dict['scraped_at'] = datetime.now()
                
                # Handle NaN values
                for key, value in product_dict.items():
                    if pd.isna(value):
                        product_dict[key] = None
                
                # Create ProductData instance
                try:
                    product = ProductData(**product_dict)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Error creating ProductData from row: {e}")
                    continue
            
            logger.info(f"Loaded {len(products)} products from {filepath}")
            return products
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Error loading products from CSV {filepath}: {e}")
            raise
    
    def list_csv_files(self, pattern: str = "*.csv") -> List[Path]:
        """
        List CSV files in the output directory.
        
        Args:
            pattern: Glob pattern for file matching
            
        Returns:
            List of Path objects for matching CSV files
        """
        try:
            csv_files = list(self.output_directory.glob(pattern))
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Sort by modification time
            return csv_files
        except Exception as e:
            logger.error(f"Error listing CSV files: {e}")
            return []