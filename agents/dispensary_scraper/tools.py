"""PydanticAI tools for the dispensary scraper agent."""

import logging
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_ai import RunContext

from .agent import scraper_agent
from .dependencies import AgentDependencies

logger = logging.getLogger(__name__)


@scraper_agent.tool
async def scrape_dispensary_categories(
    ctx: RunContext[AgentDependencies],
    categories: List[str] = Field(..., description="List of category names to scrape (e.g., ['Whole Flower', 'Pre-Rolls'])"),
    save_csv: bool = Field(default=True, description="Whether to save results as CSV files"),
    upload_snowflake: bool = Field(default=True, description="Whether to upload results to Snowflake database")
) -> Dict[str, Any]:
    """
    Scrape specific dispensary categories and store the results.
    
    This tool runs the complete scraping workflow for the specified categories,
    including data extraction, CSV file generation, and Snowflake database upload.
    
    Args:
        categories: List of category names to scrape
        save_csv: Whether to save CSV files locally
        upload_snowflake: Whether to upload to Snowflake
        
    Returns:
        Dictionary with scraping results and statistics
    """
    try:
        logger.info(f"Starting scraping workflow for categories: {categories}")
        
        # Run the scraping workflow
        result = await ctx.deps.run_scraping_workflow(
            categories=categories,
            save_csv=save_csv,
            upload_snowflake=upload_snowflake
        )
        
        # Format results for the agent
        if result["success"]:
            return {
                "status": "success",
                "products_scraped": result["products_scraped"],
                "categories_completed": result["categories_scraped"],
                "stores_processed": result["stores_scraped"],
                "duration_minutes": round(result["duration_seconds"] / 60, 2) if result["duration_seconds"] else 0,
                "csv_files_saved": len(result["csv_files_saved"]),
                "csv_file_paths": result["csv_files_saved"],
                "snowflake_uploads": result["snowflake_upload_results"],
                "total_uploaded_to_snowflake": sum(result["snowflake_upload_results"].values()) if isinstance(result["snowflake_upload_results"], dict) else 0
            }
        else:
            return {
                "status": "failed",
                "error": result["error_message"],
                "products_scraped": 0,
                "categories_completed": 0,
                "stores_processed": 0
            }
            
    except Exception as e:
        logger.error(f"Error in scrape_dispensary_categories tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "products_scraped": 0
        }


@scraper_agent.tool
async def test_connections(
    ctx: RunContext[AgentDependencies]
) -> Dict[str, Any]:
    """
    Test connections to all external services (storage systems).
    
    This tool verifies connectivity to CSV storage directory and Snowflake database
    to ensure the scraping workflow can complete successfully.
    
    Returns:
        Dictionary with connection test results
    """
    try:
        logger.info("Testing connections to external services")
        
        # Run connection tests
        connection_results = ctx.deps.test_connections()
        
        # Format results for the agent
        all_connected = all(connection_results.values())
        
        return {
            "status": "success",
            "all_connections_healthy": all_connected,
            "csv_storage": connection_results.get("csv_storage", False),
            "snowflake_database": connection_results.get("snowflake", False),
            "details": connection_results
        }
        
    except Exception as e:
        logger.error(f"Error in test_connections tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "all_connections_healthy": False
        }


@scraper_agent.tool
async def get_scraper_status(
    ctx: RunContext[AgentDependencies]
) -> Dict[str, Any]:
    """
    Get current status and configuration of the scraper agent.
    
    This tool provides information about the agent's current state,
    configuration, and recent scraping results.
    
    Returns:
        Dictionary with status information
    """
    try:
        logger.debug("Getting scraper status")
        
        # Get status summary from dependencies
        status = ctx.deps.get_status_summary()
        
        # Add configuration details
        config_info = {}
        if ctx.deps.settings:
            config_info = {
                "base_url": ctx.deps.settings.base_url,
                "output_directory": ctx.deps.settings.output_directory,
                "headless_mode": ctx.deps.settings.scraping_headless,
                "rate_limit_delay": f"{ctx.deps.settings.scraping_delay_min}-{ctx.deps.settings.scraping_delay_max}ms",
                "available_categories": [cat["subcategory"] for cat in ctx.deps.settings.categories]
            }
        
        return {
            "status": "success",
            "agent_initialized": status["initialized"],
            "session_id": status["session_id"],
            "user_preferences": status["user_preferences"],
            "last_scraping_result": status["last_scraping"],
            "configuration": config_info
        }
        
    except Exception as e:
        logger.error(f"Error in get_scraper_status tool: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@scraper_agent.tool
async def analyze_scraped_data(
    ctx: RunContext[AgentDependencies],
    category: Optional[str] = Field(None, description="Specific category to analyze, or None for all data")
) -> Dict[str, Any]:
    """
    Analyze the most recent scraped data for quality and completeness.
    
    This tool examines the results of the last scraping operation and provides
    insights about data quality, missing fields, and potential issues.
    
    Args:
        category: Optional category to focus analysis on
        
    Returns:
        Dictionary with analysis results
    """
    try:
        logger.info(f"Analyzing scraped data{' for category: ' + category if category else ''}")
        
        # Check if we have recent scraping results
        if not ctx.deps.last_scraping_result or not ctx.deps.last_scraping_result.products:
            return {
                "status": "no_data",
                "message": "No recent scraping data available to analyze"
            }
        
        products = ctx.deps.last_scraping_result.products
        
        # Filter by category if specified
        if category:
            products = [p for p in products if p.subcategory.lower() == category.lower()]
            if not products:
                return {
                    "status": "no_data",
                    "message": f"No data found for category: {category}"
                }
        
        # Analyze data quality
        total_products = len(products)
        
        # Count missing fields
        missing_prices = sum(1 for p in products if p.price is None)
        missing_brands = sum(1 for p in products if p.brand is None)
        missing_thc = sum(1 for p in products if p.thc_pct is None)
        missing_strain_types = sum(1 for p in products if p.strain_type is None)
        missing_sizes = sum(1 for p in products if p.grams is None)
        
        # Calculate completeness percentages
        price_completeness = round((1 - missing_prices / total_products) * 100, 1)
        brand_completeness = round((1 - missing_brands / total_products) * 100, 1)
        thc_completeness = round((1 - missing_thc / total_products) * 100, 1)
        strain_completeness = round((1 - missing_strain_types / total_products) * 100, 1)
        size_completeness = round((1 - missing_sizes / total_products) * 100, 1)
        
        # Analyze price distribution
        valid_prices = [p.price for p in products if p.price is not None]
        price_stats = {}
        if valid_prices:
            price_stats = {
                "min_price": min(valid_prices),
                "max_price": max(valid_prices),
                "avg_price": round(sum(valid_prices) / len(valid_prices), 2),
                "price_range_count": len(set(valid_prices))
            }
        
        # Count unique values
        unique_stores = len(set(p.store for p in products))
        unique_brands = len(set(p.brand for p in products if p.brand))
        unique_categories = len(set(p.subcategory for p in products))
        
        return {
            "status": "success",
            "analysis_summary": {
                "total_products": total_products,
                "unique_stores": unique_stores,
                "unique_brands": unique_brands,
                "unique_categories": unique_categories
            },
            "data_completeness": {
                "prices": f"{price_completeness}% ({total_products - missing_prices}/{total_products})",
                "brands": f"{brand_completeness}% ({total_products - missing_brands}/{total_products})",
                "thc_content": f"{thc_completeness}% ({total_products - missing_thc}/{total_products})",
                "strain_types": f"{strain_completeness}% ({total_products - missing_strain_types}/{total_products})",
                "sizes": f"{size_completeness}% ({total_products - missing_sizes}/{total_products})"
            },
            "price_analysis": price_stats,
            "data_quality_score": round((price_completeness + brand_completeness + thc_completeness + strain_completeness + size_completeness) / 5, 1),
            "recommendations": _generate_data_quality_recommendations(
                price_completeness, brand_completeness, thc_completeness, 
                strain_completeness, size_completeness
            )
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_scraped_data tool: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@scraper_agent.tool
async def set_scraper_preferences(
    ctx: RunContext[AgentDependencies],
    preferences: Dict[str, Any] = Field(..., description="Dictionary of preference key-value pairs to set")
) -> Dict[str, Any]:
    """
    Set user preferences for the scraper agent.
    
    This tool allows users to configure scraper behavior and preferences
    that persist for the current session.
    
    Args:
        preferences: Dictionary of preferences to set
        
    Returns:
        Dictionary confirming the preferences were set
    """
    try:
        logger.info(f"Setting scraper preferences: {preferences}")
        
        # Set each preference
        for key, value in preferences.items():
            ctx.deps.set_user_preference(key, value)
        
        return {
            "status": "success",
            "message": f"Set {len(preferences)} preferences",
            "preferences_set": preferences,
            "all_preferences": ctx.deps.user_preferences.copy()
        }
        
    except Exception as e:
        logger.error(f"Error in set_scraper_preferences tool: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _generate_data_quality_recommendations(
    price_completeness: float,
    brand_completeness: float,
    thc_completeness: float,
    strain_completeness: float,
    size_completeness: float
) -> List[str]:
    """
    Generate data quality recommendations based on completeness percentages.
    
    Args:
        Completeness percentages for different fields
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if price_completeness < 90:
        recommendations.append("Price data extraction could be improved - check price selectors and PDP extraction logic")
    
    if brand_completeness < 80:
        recommendations.append("Brand extraction needs attention - consider improving brand detection from breadcrumbs and product pages")
    
    if thc_completeness < 70:
        recommendations.append("THC content extraction is incomplete - verify regex patterns for THC percentage detection")
    
    if strain_completeness < 60:
        recommendations.append("Strain type detection could be enhanced - check for strain type keywords in product descriptions")
    
    if size_completeness < 85:
        recommendations.append("Size/weight extraction needs improvement - verify regex patterns for size detection")
    
    if not recommendations:
        recommendations.append("Data quality looks good! All fields have acceptable completeness rates.")
    
    return recommendations