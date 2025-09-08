"""Snowflake storage operations for scraped data."""

import logging
import pandas as pd
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import snowflake.connector
from snowflake.connector import DictCursor
import json

from ..models import ProductData, ScrapingResult
from ..settings import load_settings

logger = logging.getLogger(__name__)


class SnowflakeStorage:
    """Handles Snowflake database storage operations."""
    
    def __init__(self, settings=None):
        """
        Initialize Snowflake storage.
        
        Args:
            settings: Optional settings object, defaults to loaded settings
        """
        self.settings = settings or load_settings()
        self._connection = None
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Get Snowflake connection parameters from settings."""
        return {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password,
            "warehouse": self.settings.snowflake_warehouse,
            "database": self.settings.snowflake_database,
            "schema": self.settings.snowflake_schema,
            "application": "DispensaryScraper"
        }
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Async context manager for Snowflake connections.
        
        Yields:
            Snowflake connection object
        """
        connection = None
        try:
            connection_params = self._get_connection_params()
            connection = snowflake.connector.connect(**connection_params)
            logger.debug("Snowflake connection established")
            yield connection
        except Exception as e:
            logger.error(f"Error connecting to Snowflake: {e}")
            raise
        finally:
            if connection:
                connection.close()
                logger.debug("Snowflake connection closed")
    
    def test_connection(self) -> bool:
        """
        Test Snowflake connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection_params = self._get_connection_params()
            with snowflake.connector.connect(**connection_params) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                success = result == (1,)
                
            logger.info(f"Snowflake connection test {'successful' if success else 'failed'}")
            return success
            
        except Exception as e:
            logger.error(f"Snowflake connection test failed: {e}")
            return False
    
    def _get_table_name(self, subcategory: str) -> str:
        """
        Get Snowflake table name for a subcategory.
        
        Args:
            subcategory: Product subcategory
            
        Returns:
            Snowflake table name
        """
        # Table mapping from PRP
        table_mapping = {
            "Whole Flower": "TL_Scrape_WHOLE_FLOWER",
            "Pre-Rolls": "TL_Scrape_Pre_Rolls",
            "Ground & Shake": "TL_Scrape_Ground_Shake"
        }
        
        return table_mapping.get(subcategory, f"TL_Scrape_{subcategory.replace(' ', '_').upper()}")
    
    def _products_to_dataframe(self, products: List[ProductData]) -> pd.DataFrame:
        """
        Convert products to DataFrame for Snowflake upload.
        
        Args:
            products: List of ProductData
            
        Returns:
            pandas DataFrame ready for Snowflake
        """
        # Convert to dictionaries
        data = []
        for product in products:
            product_dict = product.model_dump()
            
            # Convert datetime to string for Snowflake
            if 'scraped_at' in product_dict and product_dict['scraped_at']:
                product_dict['scraped_at'] = product_dict['scraped_at'].isoformat()
            
            data.append(product_dict)
        
        df = pd.DataFrame(data)
        
        # Ensure proper column types for Snowflake
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        if 'thc_pct' in df.columns:
            df['thc_pct'] = pd.to_numeric(df['thc_pct'], errors='coerce')
        if 'grams' in df.columns:
            df['grams'] = pd.to_numeric(df['grams'], errors='coerce')
        if 'price_per_g' in df.columns:
            df['price_per_g'] = pd.to_numeric(df['price_per_g'], errors='coerce')
        
        return df
    
    async def create_table_if_not_exists(self, table_name: str) -> bool:
        """
        Create Snowflake table if it doesn't exist.
        
        Args:
            table_name: Name of table to create
            
        Returns:
            True if table exists/created, False on error
        """
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            state VARCHAR(10),
            store VARCHAR(255),
            subcategory VARCHAR(100),
            name VARCHAR(500),
            brand VARCHAR(255),
            strain_type VARCHAR(50),
            thc_pct FLOAT,
            size_raw VARCHAR(50),
            grams FLOAT,
            price FLOAT,
            price_per_g FLOAT,
            url VARCHAR(1000),
            scraped_at TIMESTAMP_NTZ,
            created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_sql)
                logger.info(f"Table {table_name} ready")
                return True
                
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            return False
    
    async def upload_products(self, products: List[ProductData], overwrite: bool = False) -> Dict[str, int]:
        """
        Upload products to Snowflake tables grouped by subcategory.
        
        Args:
            products: List of ProductData to upload
            overwrite: Whether to truncate tables before insert
            
        Returns:
            Dictionary with upload counts by table
        """
        if not products:
            logger.warning("No products provided for upload")
            return {}
        
        # Group products by subcategory
        category_groups = {}
        for product in products:
            subcategory = product.subcategory
            if subcategory not in category_groups:
                category_groups[subcategory] = []
            category_groups[subcategory].append(product)
        
        upload_counts = {}
        
        for subcategory, category_products in category_groups.items():
            try:
                table_name = self._get_table_name(subcategory)
                count = await self.upload_products_to_table(category_products, table_name, overwrite)
                upload_counts[table_name] = count
                logger.info(f"Uploaded {count} {subcategory} products to {table_name}")
                
            except Exception as e:
                logger.error(f"Error uploading {subcategory} products: {e}")
                upload_counts[f"ERROR_{subcategory}"] = 0
                continue
        
        return upload_counts
    
    async def upload_products_to_table(
        self,
        products: List[ProductData],
        table_name: str,
        overwrite: bool = False
    ) -> int:
        """
        Upload products to a specific Snowflake table.
        
        Args:
            products: List of ProductData to upload
            table_name: Target table name
            overwrite: Whether to truncate table before insert
            
        Returns:
            Number of products uploaded
            
        Raises:
            Exception: If upload fails
        """
        if not products:
            return 0
        
        try:
            # Ensure table exists
            await self.create_table_if_not_exists(table_name)
            
            # Convert to DataFrame
            df = self._products_to_dataframe(products)
            
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Truncate if overwrite requested
                if overwrite:
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                    logger.info(f"Truncated table {table_name}")
                
                # Insert data using batch insert
                await self._batch_insert_dataframe(cursor, df, table_name)
                
                # Commit transaction
                conn.commit()
                
                logger.info(f"Successfully uploaded {len(products)} products to {table_name}")
                return len(products)
                
        except Exception as e:
            logger.error(f"Error uploading to table {table_name}: {e}")
            raise
    
    async def _batch_insert_dataframe(self, cursor, df: pd.DataFrame, table_name: str) -> None:
        """
        Perform batch insert of DataFrame into Snowflake table.
        
        Args:
            cursor: Snowflake cursor
            df: DataFrame to insert
            table_name: Target table name
        """
        # Prepare column list
        columns = df.columns.tolist()
        column_str = ", ".join(columns)
        placeholder_str = ", ".join(["%s"] * len(columns))
        
        insert_sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholder_str})"
        
        # Convert DataFrame to list of tuples
        data_tuples = []
        for _, row in df.iterrows():
            # Convert row values to appropriate types
            values = []
            for value in row.values:
                if pd.isna(value):
                    values.append(None)
                else:
                    values.append(value)
            data_tuples.append(tuple(values))
        
        # Execute batch insert
        try:
            cursor.executemany(insert_sql, data_tuples)
            logger.debug(f"Batch inserted {len(data_tuples)} rows into {table_name}")
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            raise
    
    async def upload_scraping_result(self, result: ScrapingResult, overwrite: bool = False) -> Dict[str, int]:
        """
        Upload scraping result to Snowflake.
        
        Args:
            result: ScrapingResult containing products
            overwrite: Whether to truncate tables before insert
            
        Returns:
            Dictionary with upload counts by table
        """
        if not result.success or not result.products:
            logger.warning("Scraping result has no products or was unsuccessful")
            return {}
        
        return await self.upload_products(result.products, overwrite)
    
    async def get_table_count(self, table_name: str) -> int:
        """
        Get record count for a Snowflake table.
        
        Args:
            table_name: Table name
            
        Returns:
            Record count or -1 on error
        """
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting count for table {table_name}: {e}")
            return -1
    
    async def query_recent_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query recent data from a Snowflake table.
        
        Args:
            table_name: Table name
            limit: Number of records to return
            
        Returns:
            List of dictionaries representing rows
        """
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor(DictCursor)
                cursor.execute(f"""
                    SELECT * FROM {table_name} 
                    ORDER BY created_at DESC 
                    LIMIT {limit}
                """)
                results = cursor.fetchall()
                return results or []
                
        except Exception as e:
            logger.error(f"Error querying recent data from {table_name}: {e}")
            return []