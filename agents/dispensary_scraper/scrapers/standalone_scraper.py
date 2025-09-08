#!/usr/bin/env python3
"""Standalone scraper script that can be run in a separate process."""

import sys
import json
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.dispensary_scraper.scrapers.trulieve_scraper_sync import TrulieveScraperSync
from agents.dispensary_scraper.models import ScrapingConfig
from agents.dispensary_scraper.settings import load_settings

def main():
    """Main function to run scraping and return results as JSON."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No categories provided"}))
        return
    
    try:
        # Parse arguments - can be JSON string or file path
        categories_input = sys.argv[1]
        
        # Check if it's a file path
        if categories_input.endswith('.json'):
            with open(categories_input, 'r') as f:
                categories = json.load(f)
        else:
            # Parse as JSON string
            categories = json.loads(categories_input)
        
        # Load settings
        settings = load_settings()
        
        # Create scraper config
        config = ScrapingConfig(
            categories=categories,
            headless=True,
            rate_limit_delay=(settings.scraping_delay_min, settings.scraping_delay_max)
        )
        
        # Create and run scraper
        print("Creating scraper...", file=sys.stderr)
        scraper = TrulieveScraperSync(config)
        print("Starting scraping...", file=sys.stderr)
        result = scraper.scrape_all_categories()
        print(f"Scraping completed: {result.success}, {len(result.products)} products", file=sys.stderr)
        
        # Convert result to JSON-serializable format
        result_dict = {
            "success": result.success,
            "products": [
                {
                    "name": p.name,
                    "brand": p.brand,
                    "price": p.price,
                    "thc_percentage": p.thc_percentage,
                    "strain_type": p.strain_type,
                    "size": p.size,
                    "category": p.category,
                    "store_name": p.store_name,
                    "store_url": p.store_url,
                    "product_url": p.product_url,
                    "scraped_at": p.scraped_at.isoformat() if p.scraped_at else None
                }
                for p in result.products
            ],
            "categories_scraped": result.categories_scraped,
            "stores_scraped": result.stores_scraped,
            "duration_seconds": result.duration_seconds,
            "error_message": result.error_message
        }
        
        print(json.dumps(result_dict))
        
    except Exception as e:
        error_result = {
            "success": False,
            "products": [],
            "categories_scraped": 0,
            "stores_scraped": 0,
            "duration_seconds": 0,
            "error_message": str(e)
        }
        print(json.dumps(error_result))

if __name__ == "__main__":
    main()
