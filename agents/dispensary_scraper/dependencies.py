"""Dependencies for the dispensary scraper agent."""

import logging
import sys
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

from .settings import load_settings
from .storage.csv_storage import CSVStorage
from .storage.snowflake_storage import SnowflakeStorage
from .scrapers.trulieve_scraper_sync import TrulieveScraperSync

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies for the dispensary scraper agent."""
    
    # Configuration
    settings: Optional[Any] = None
    
    # Storage components
    csv_storage: Optional[CSVStorage] = None
    snowflake_storage: Optional[SnowflakeStorage] = None
    
    # Scraping components
    scraper: Optional[TrulieveScraperSync] = None
    
    # Runtime state
    session_id: Optional[str] = None
    user_preferences: Dict[str, Any] = None
    last_scraping_result: Optional[Any] = None
    
    def __post_init__(self):
        """Initialize dependencies after dataclass creation."""
        if self.user_preferences is None:
            self.user_preferences = {}
    
    async def initialize(self) -> None:
        """Initialize all dependencies asynchronously."""
        try:
            logger.info("Initializing agent dependencies")
            
            # Load settings
            self.settings = load_settings()
            logger.debug("Settings loaded successfully")
            
            # Initialize CSV storage
            self.csv_storage = CSVStorage(self.settings.output_directory)
            logger.debug("CSV storage initialized")
            
            # Initialize Snowflake storage
            self.snowflake_storage = SnowflakeStorage(self.settings)
            logger.debug("Snowflake storage initialized")
            
            # Initialize scraper with configuration
            from .models import ScrapingConfig
            config = ScrapingConfig(
                base_url=self.settings.base_url,
                dispensaries_url=self.settings.dispensaries_url,
                categories=self.settings.categories,
                output_dir=self.settings.output_directory,
                headless=self.settings.scraping_headless,
                rate_limit_delay=(self.settings.scraping_delay_min, self.settings.scraping_delay_max)
            )
            
            self.scraper = TrulieveScraperSync(config)
            logger.debug("Trulieve scraper initialized")
            
            logger.info("All dependencies initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing dependencies: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.debug("Cleaning up agent dependencies")
            
            # Close any open connections
            if self.snowflake_storage:
                # Snowflake storage uses context managers, no explicit cleanup needed
                pass
            
            logger.debug("Dependencies cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference.
        
        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value
        logger.debug(f"Set user preference: {key} = {value}")
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference.
        
        Args:
            key: Preference key
            default: Default value if key not found
            
        Returns:
            Preference value or default
        """
        return self.user_preferences.get(key, default)
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test all external connections.
        
        Returns:
            Dictionary with connection test results
        """
        results = {}
        
        # Test CSV storage (directory access)
        try:
            if self.csv_storage:
                # Try to create a test file
                test_path = Path(self.csv_storage.output_directory) / ".test"
                test_path.touch()
                test_path.unlink()  # Clean up
                results["csv_storage"] = True
            else:
                results["csv_storage"] = False
        except Exception as e:
            logger.warning(f"CSV storage test failed: {e}")
            results["csv_storage"] = False
        
        # Test Snowflake connection
        try:
            if self.snowflake_storage:
                results["snowflake"] = self.snowflake_storage.test_connection()
            else:
                results["snowflake"] = False
        except Exception as e:
            logger.warning(f"Snowflake connection test failed: {e}")
            results["snowflake"] = False
        
        logger.info(f"Connection test results: {results}")
        return results
    
    async def run_scraping_workflow(
        self,
        categories: Optional[List[str]] = None,
        save_csv: bool = True,
        upload_snowflake: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete scraping workflow.
        
        Args:
            categories: List of category names to scrape, None for all
            save_csv: Whether to save CSV files
            upload_snowflake: Whether to upload to Snowflake
            
        Returns:
            Dictionary with workflow results
        """
        if not self.scraper:
            raise RuntimeError("Scraper not initialized")
        
        try:
            logger.info("Starting scraping workflow")
            
            # Filter categories if specified
            if categories:
                original_categories = self.scraper.config.categories.copy()
                filtered_categories = [
                    cat for cat in original_categories
                    if cat["subcategory"].lower() in [c.lower() for c in categories]
                ]
                self.scraper.config.categories = filtered_categories
                logger.info(f"Filtered to categories: {[c['subcategory'] for c in filtered_categories]}")
            
            # Run scraping in a separate process to avoid Playwright issues
            import subprocess
            import json
            import tempfile
            from pathlib import Path
            
            # Create a temporary script to run the standalone scraper
            script_path = Path(__file__).parent / "scrapers" / "standalone_scraper.py"
            
            # Prepare categories for the standalone scraper
            categories_json = json.dumps(self.scraper.config.categories)
            
            # Run the standalone scraper
            try:
                process = subprocess.run(
                    [sys.executable, str(script_path), categories_json],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                if process.returncode != 0:
                    raise Exception(f"Scraper process failed: {process.stderr}")
                
                # Parse the result
                result_data = json.loads(process.stdout)
                
                # Convert back to ScrapingResult object
                from .models import ScrapingResult, ProductData
                from datetime import datetime
                
                products = []
                for p_data in result_data.get("products", []):
                    products.append(ProductData(
                        name=p_data["name"],
                        brand=p_data["brand"],
                        price=p_data["price"],
                        thc_percentage=p_data["thc_percentage"],
                        strain_type=p_data["strain_type"],
                        size=p_data["size"],
                        category=p_data["category"],
                        store_name=p_data["store_name"],
                        store_url=p_data["store_url"],
                        product_url=p_data["product_url"],
                        scraped_at=datetime.fromisoformat(p_data["scraped_at"]) if p_data["scraped_at"] else None
                    ))
                
                result = ScrapingResult(
                    success=result_data["success"],
                    products=products,
                    categories_scraped=result_data["categories_scraped"],
                    stores_scraped=result_data["stores_scraped"],
                    duration_seconds=result_data["duration_seconds"],
                    error_message=result_data.get("error_message")
                )
                
            except Exception as e:
                logger.error(f"Error running standalone scraper: {e}")
                from .models import ScrapingResult
                result = ScrapingResult(
                    success=False,
                    products=[],
                    error_message=str(e),
                    categories_scraped=0,
                    stores_scraped=0,
                    duration_seconds=0
                )
            self.last_scraping_result = result
            
            # Process results
            saved_files = []
            upload_results = {}
            
            if result.success and result.products:
                logger.info(f"Scraping completed: {result.total_products} products")
                
                # Save CSV files
                if save_csv and self.csv_storage:
                    try:
                        saved_files = self.csv_storage.save_by_category(result.products)
                        logger.info(f"Saved {len(saved_files)} CSV files")
                    except Exception as e:
                        logger.error(f"Error saving CSV files: {e}")
                
                # Upload to Snowflake
                if upload_snowflake and self.snowflake_storage:
                    try:
                        upload_results = await self.snowflake_storage.upload_products(result.products)
                        total_uploaded = sum(upload_results.values())
                        logger.info(f"Uploaded {total_uploaded} products to Snowflake")
                    except Exception as e:
                        logger.error(f"Error uploading to Snowflake: {e}")
                        upload_results = {"error": str(e)}
            
            # Restore original categories if they were filtered
            if categories and 'original_categories' in locals():
                self.scraper.config.categories = original_categories
            
            return {
                "success": result.success,
                "products_scraped": result.total_products if result.success else 0,
                "categories_scraped": result.categories_scraped,
                "stores_scraped": result.stores_scraped,
                "duration_seconds": result.duration_seconds,
                "csv_files_saved": saved_files,
                "snowflake_upload_results": upload_results,
                "error_message": result.error_message
            }
            
        except Exception as e:
            logger.error(f"Error in scraping workflow: {e}")
            return {
                "success": False,
                "products_scraped": 0,
                "categories_scraped": 0,
                "stores_scraped": 0,
                "duration_seconds": 0,
                "csv_files_saved": [],
                "snowflake_upload_results": {},
                "error_message": str(e)
            }
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get current status summary of the agent.
        
        Returns:
            Dictionary with status information
        """
        status = {
            "initialized": bool(self.settings and self.scraper),
            "session_id": self.session_id,
            "user_preferences": self.user_preferences.copy(),
            "last_scraping": None
        }
        
        if self.last_scraping_result:
            status["last_scraping"] = {
                "success": self.last_scraping_result.success,
                "products_count": self.last_scraping_result.total_products,
                "duration": self.last_scraping_result.duration_seconds
            }
        
        return status