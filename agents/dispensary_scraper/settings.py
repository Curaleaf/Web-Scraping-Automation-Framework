"""Settings configuration for Dispensary Scraper Agent."""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Snowflake Configuration
    snowflake_account: str = Field(
        ...,
        description="Snowflake account URL"
    )
    
    snowflake_user: str = Field(
        ...,
        description="Snowflake username"
    )
    
    snowflake_password: str = Field(
        ...,
        description="Snowflake password"
    )
    
    snowflake_warehouse: str = Field(
        default="COMPUTE_WH",
        description="Snowflake warehouse"
    )
    
    snowflake_database: str = Field(
        default="SANDBOX_EDW",
        description="Snowflake database"
    )
    
    snowflake_schema: str = Field(
        default="ANALYTICS",
        description="Snowflake schema"
    )
    
    # LLM Configuration (for agent orchestration)
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, gemini, etc.)"
    )
    
    llm_api_key: str = Field(
        ...,
        description="API key for the LLM provider"
    )
    
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="Model to use for agent orchestration"
    )
    
    llm_base_url: Optional[str] = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the LLM API"
    )
    
    # Scraping Configuration
    scraping_headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    
    scraping_delay_min: int = Field(
        default=700,
        description="Minimum delay between requests (ms)"
    )
    
    scraping_delay_max: int = Field(
        default=1500,
        description="Maximum delay between requests (ms)"
    )
    
    output_directory: str = Field(
        default="~/local/trulieve/",
        description="Directory for CSV output files"
    )
    
    # Trulieve Configuration
    base_url: str = Field(
        default="https://www.trulieve.com",
        description="Trulieve base URL"
    )
    
    dispensaries_url: str = Field(
        default="https://www.trulieve.com/dispensaries",
        description="Trulieve dispensaries URL"
    )
    
    # Categories configuration
    categories: List[Dict[str, Any]] = Field(
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
        ],
        description="Categories to scrape"
    )


def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "snowflake_account" in str(e).lower():
            error_msg += "\nMake sure to set SNOWFLAKE_ACCOUNT in your .env file"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        if "snowflake_password" in str(e).lower():
            error_msg += "\nMake sure to set SNOWFLAKE_PASSWORD in your .env file"
        raise ValueError(error_msg) from e