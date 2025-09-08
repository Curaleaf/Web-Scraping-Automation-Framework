name: "Dispensary Web Scraping Automation Framework PRP"
description: |
  Comprehensive PRP for building a web scraping automation framework to extract pricing data from dispensary websites using Playwright and Python, with recursive iteration through categories and Snowflake integration.

---

## Goal
Build a production-ready automation framework that scrapes pricing data from dispensary websites (specifically Trulieve) using Playwright and Python. The framework must handle recursive iteration through parent and child categories, extract structured pricing data, save results as CSV files locally, and upload to Snowflake database tables.

## Why
- **Business Value**: Automated competitive pricing intelligence for dispensary market analysis
- **Data Pipeline**: Structured data collection feeding into Snowflake data warehouse for analytics
- **Scalability**: Framework foundation that can expand to multiple dispensary chains
- **Automation**: Replace manual data collection with automated, scheduled scraping

## What
A complete web scraping framework that:
- Navigates dispensary websites (starting with Trulieve) using Playwright 
- Recursively scrapes through category hierarchies (Flower → Whole Flower, Pre-Rolls, etc.)
- Extracts structured product data (name, brand, price, THC%, strain type, size)
- Saves data as timestamped CSV files with naming convention `{OUT_PREFIX}-{date_time}.csv`
- Uploads collected data to Snowflake database tables
- Includes comprehensive testing and error handling
- Provides agent-based architecture for maintainability

### Success Criteria
- [ ] Successfully scrapes all specified Trulieve categories (Whole Flower, Pre-Rolls, Ground & Shake)
- [ ] Extracts complete product data fields with >95% accuracy
- [ ] Saves properly formatted CSV files locally 
- [ ] Uploads data to Snowflake database without errors
- [ ] Handles rate limiting and anti-bot detection gracefully
- [ ] Includes comprehensive test coverage >80%
- [ ] Framework supports easy extension to new dispensaries/categories

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://playwright.dev/python/docs/api/class-playwright
  why: Core Playwright async API patterns, browser automation
  section: BrowserContext, Page locators, network handling
  
- url: https://docs.snowflake.com/en/developer-guide/sql-api/index
  why: Snowflake SQL API for data upload integration
  section: Authentication, data loading operations
  
- url: https://oxylabs.io/blog/playwright-web-scraping
  why: 2024 Playwright web scraping best practices
  critical: Async patterns, rate limiting, anti-detection strategies
  
- url: https://scrapfly.io/blog/posts/web-scraping-with-playwright-and-python  
  why: Advanced Playwright techniques for production scraping
  section: Error handling, retry mechanisms, dynamic content
  
- file: examples/Web scrape attempt.ipynb
  why: Working implementation reference with exact logic patterns
  critical: Contains proven regex patterns, locator strategies, data extraction
  
- file: use-cases/agent-factory-with-subagents/examples/basic_chat_agent/agent.py
  why: Agent architecture pattern to follow
  pattern: Settings, dependencies, environment configuration
  
- file: use-cases/agent-factory-with-subagents/examples/main_agent_reference/tools.py  
  why: Tool function patterns for external API integration
  pattern: Async HTTP client patterns, error handling, validation
```

### Current Codebase Structure
```bash
Web-Scraping-Automation-Framework/
├── examples/
│   └── Web scrape attempt.ipynb          # Working scraping logic reference
├── use-cases/
│   ├── agent-factory-with-subagents/
│   │   ├── agents/rag_agent/             # Agent structure pattern
│   │   │   ├── agent.py                  # Main agent logic
│   │   │   ├── tools.py                  # Tool functions
│   │   │   ├── settings.py               # Configuration
│   │   │   └── tests/                    # Test patterns
│   │   └── examples/
│   │       ├── basic_chat_agent/         # Agent architecture reference
│   │       └── main_agent_reference/     # Tool patterns reference
├── PRPs/
│   └── templates/prp_base.md            # PRP template structure
├── CLAUDE.md                            # Global project rules
└── PLANNING.md                          # Architecture guidelines
```

### Desired Codebase Structure (New Framework)
```bash
Web-Scraping-Automation-Framework/
└── agents/
    └── dispensary_scraper/
        ├── agent.py                     # Main scraping agent orchestration
        ├── settings.py                  # Environment configuration 
        ├── providers.py                 # LLM model providers
        ├── dependencies.py              # External service connections
        ├── tools.py                     # Scraping tool implementations  
        ├── prompts.py                   # System prompts for agent
        ├── scrapers/                    # Scraping logic modules
        │   ├── __init__.py
        │   ├── base_scraper.py          # Abstract base scraper class
        │   ├── trulieve_scraper.py      # Trulieve-specific implementation
        │   └── data_extractors.py       # Data extraction utilities
        ├── storage/                     # Data persistence modules  
        │   ├── __init__.py
        │   ├── csv_storage.py           # Local CSV file operations
        │   └── snowflake_storage.py     # Snowflake database operations
        ├── tests/                       # Comprehensive test suite
        │   ├── conftest.py              # Test configuration
        │   ├── test_agent.py            # Agent integration tests
        │   ├── test_scrapers.py         # Scraping logic tests
        │   └── test_storage.py          # Storage operations tests
        ├── cli.py                       # Command line interface
        ├── requirements.txt             # Python dependencies
        ├── .env.example                 # Environment variables template
        └── README.md                    # Usage documentation
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Playwright async context management
# Pattern: Always use async context managers for browser lifecycle
async with playwright.async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."  # Anti-detection
    )
    # Always close browser to prevent resource leaks
    await browser.close()

# CRITICAL: Trulieve website specific patterns from notebook
BASE = "https://www.trulieve.com"
# Requires "Shop At This Store" button click before category access
# Uses "Load More" button pagination for complete product listings
# Product cards use specific CSS patterns: .price, [class*='price']

# CRITICAL: Rate limiting and anti-bot detection
# Trulieve implements rate limiting - use random delays between requests
await page.wait_for_timeout(random.randint(700, 1500))  
# User-agent rotation recommended for production use

# CRITICAL: Snowflake SQL API authentication
# Requires OAuth or Key Pair authentication - never hardcode credentials
# Use environment variables with python-dotenv pattern from existing agents

# CRITICAL: Windows async event loop policy (from notebook)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## Implementation Blueprint

### Data Models and Structure
Create core data models ensuring type safety and consistency:
```python
# Pydantic models for data validation and structure
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductData(BaseModel):
    """Core product data structure matching notebook schema."""
    state: str = "FL"
    store: str
    subcategory: str  # "Whole Flower", "Pre-Rolls", "Ground & Shake"  
    name: str
    brand: Optional[str] = None
    strain_type: Optional[str] = None  # "Indica", "Sativa", "Hybrid"
    thc_pct: Optional[float] = None
    size_raw: Optional[str] = None  # "3.5g", "7g", etc.
    grams: Optional[float] = None
    price: Optional[float] = None
    price_per_g: Optional[float] = None
    url: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.now)

class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""
    base_url: str = "https://www.trulieve.com"
    dispensaries_url: str = "https://www.trulieve.com/dispensaries"  
    categories: List[dict] = [
        {"url": "/category/flower/whole-flower", "subcategory": "Whole Flower", "prefix": "trulieve_FL_whole_flower"},
        {"url": "/category/flower/pre-rolls", "subcategory": "Pre-Rolls", "prefix": "trulieve_FL_pre_rolls"}, 
        {"url": "/category/flower/minis", "subcategory": "Ground & Shake", "prefix": "trulieve_FL_ground_shake"}
    ]
    output_dir: str = "~/local/trulieve/"
    headless: bool = True
    rate_limit_delay: tuple = (700, 1500)  # Random delay range in ms
```

### List of Tasks (Implementation Order)

```yaml
Task 1: Project Structure Setup
CREATE agents/dispensary_scraper/ directory structure:
  - Copy settings.py pattern from use-cases/agent-factory-with-subagents/examples/basic_chat_agent/
  - MODIFY for Snowflake credentials and scraping configuration
  - CREATE .env.example with required environment variables
  - SETUP requirements.txt with Playwright, Snowflake, Pydantic dependencies

Task 2: Base Scraper Architecture  
CREATE scrapers/base_scraper.py:
  - ABSTRACT base class defining scraper interface
  - Common browser management and anti-detection patterns
  - Rate limiting and retry mechanisms
  - Error handling patterns from main_agent_reference/tools.py

Task 3: Data Extraction Logic
CREATE scrapers/data_extractors.py:
  - COPY regex patterns from examples/Web scrape attempt.ipynb
  - IMPLEMENT extract_price_from_card() and extract_brand_from_card() functions  
  - PATTERN: Extract all data field functions (THC, strain type, size parsing)
  - VALIDATE data extraction with Pydantic models

Task 4: Trulieve Specific Implementation
CREATE scrapers/trulieve_scraper.py:
  - INHERIT from base_scraper.py
  - IMPLEMENT extract_fl_store_links() - copy from notebook
  - IMPLEMENT load_all() pagination function - copy from notebook  
  - IMPLEMENT scrape_category() - adapt notebook logic to class structure
  - HANDLE "Shop At This Store" button clicking workflow

Task 5: Storage Layer Implementation
CREATE storage/csv_storage.py:
  - IMPLEMENT save_to_csv() with naming convention {OUT_PREFIX}-{date_time}.csv
  - CREATE local directory management (~\local\{COMP}\)
  - PATTERN: Follow pandas DataFrame.to_csv() from notebook
  
CREATE storage/snowflake_storage.py:  
  - IMPLEMENT Snowflake SQL API connection management
  - CREATE table upload functions for TL_Scrape_WHOLE_FLOWER, TL_Scrape_Pre_Rolls, TL_Scrape_Ground_Shake
  - USE python-dotenv pattern for credentials
  - HANDLE authentication and connection pooling

Task 6: Agent Orchestration Layer
CREATE agent.py:
  - COMBINE all components into cohesive agent
  - IMPLEMENT run_scraping_workflow() main function
  - PATTERN: Follow basic_chat_agent.py structure  
  - INTEGRATE with PydanticAI agent patterns for monitoring/logging
  - CREATE async execution flow matching notebook's run() function

Task 7: Tool Integration
CREATE tools.py:
  - IMPLEMENT scrape_dispensary_category() tool function
  - IMPLEMENT upload_to_snowflake() tool function
  - PATTERN: Follow main_agent_reference/tools.py async client patterns
  - ADD comprehensive error handling and retries

Task 8: Testing Infrastructure  
CREATE tests/ directory with comprehensive coverage:
  - test_scrapers.py: Test data extraction functions with mock data
  - test_storage.py: Test CSV and Snowflake operations
  - test_agent.py: Integration tests with TestModel
  - conftest.py: Test fixtures and configuration
  - PATTERN: Follow existing test patterns from agents/rag_agent/tests/

Task 9: CLI and Documentation
CREATE cli.py:
  - Command-line interface for running scraping operations
  - Configuration options and help text
  - PATTERN: Follow agents/rag_agent/cli.py structure

CREATE README.md:
  - Setup instructions and environment configuration  
  - Usage examples and API documentation
  - Troubleshooting guide and FAQ
```

### Task Implementation Details

#### Task 1 Pseudocode: Project Structure Setup
```python
# settings.py - Based on basic_chat_agent pattern
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

class ScrapingSettings(BaseSettings):
    """Environment configuration for dispensary scraping."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8", 
        case_sensitive=False
    )
    
    # Snowflake Configuration
    snowflake_account: str = Field(..., description="Snowflake account URL")
    snowflake_user: str = Field(..., description="Snowflake username")  
    snowflake_password: str = Field(..., description="Snowflake password")
    snowflake_warehouse: str = Field(default="COMPUTE_WH")
    snowflake_database: str = Field(default="SANDBOX_EDW")
    snowflake_schema: str = Field(default="ANALYTICS")
    
    # Scraping Configuration  
    scraping_headless: bool = Field(default=True)
    scraping_delay_min: int = Field(default=700)
    scraping_delay_max: int = Field(default=1500)
    output_directory: str = Field(default="~/local/trulieve/")
```

#### Task 4 Pseudocode: Trulieve Implementation
```python
# scrapers/trulieve_scraper.py - Core scraping logic
class TrulieveScraper(BaseScraper):
    """Trulieve-specific scraping implementation."""
    
    async def scrape_all_categories(self) -> List[ProductData]:
        """Main scraping workflow - mirrors notebook run() function."""
        async with async_playwright() as playwright:
            browser = await self._launch_browser(playwright)
            context = await self._create_context(browser)
            page = await context.new_page()
            
            # PATTERN: Extract FL store links (from notebook)
            stores = await self.extract_fl_store_links(page)
            
            all_products = []
            for category in self.config.categories:
                # CRITICAL: Set store location first
                await self._set_store_location(page)
                
                # PATTERN: Scrape category products  
                products = await self.scrape_category(page, category)
                all_products.extend(products)
                
                # CRITICAL: Rate limiting between categories
                await self._apply_rate_limit()
            
            await browser.close()
            return all_products
    
    async def scrape_category(self, page, category_config) -> List[ProductData]:
        """Scrape single category - adapted from notebook."""
        await page.goto(category_config["url"])
        
        # PATTERN: Load all products (handles pagination)
        await self.load_all_products(page)
        
        # PATTERN: Extract product data
        product_links = await page.locator("a[href*='/product/']:not(:has(img))").all()
        
        products = []
        for link in product_links:
            product_data = await self._extract_product_from_element(link, category_config)
            if product_data:
                products.append(product_data)
        
        return products
```

### Integration Points
```yaml
DATABASE:
  - tables: "TL_Scrape_WHOLE_FLOWER, TL_Scrape_Pre_Rolls, TL_Scrape_Ground_Shake"  
  - connection: "CURALEAF-CURAPROD.snowflakecomputing.com"
  - schema: "SANDBOX_EDW.ANALYTICS"
  
CONFIG:
  - add to: agents/dispensary_scraper/settings.py
  - pattern: "SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')"
  
TOOLS:
  - add to: agents/dispensary_scraper/tools.py
  - pattern: "@agent.tool async def scrape_category_tool(ctx, category: str)"
  
CSV_OUTPUT:
  - location: "~/local/trulieve/"  
  - naming: "{OUT_PREFIX}-{date_time}.csv"
  - format: "ProductData model -> pandas DataFrame -> CSV"
```

## Validation Loop

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
ruff check agents/dispensary_scraper/ --fix
mypy agents/dispensary_scraper/

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE comprehensive test suite covering:
def test_product_data_validation():
    """ProductData model validates correctly"""
    valid_product = ProductData(
        store="Test Store FL",
        subcategory="Whole Flower", 
        name="Test Product",
        price=25.99
    )
    assert valid_product.price_per_g is None  # No grams specified

def test_trulieve_regex_extraction():
    """Regex patterns extract data correctly from sample HTML"""
    sample_text = "$25.99 3.5g THC: 18.5%"
    price = extract_price_from_text(sample_text)
    assert price == 25.99
    
def test_csv_storage_operations():
    """CSV storage creates properly named files"""
    products = [ProductData(store="Test", subcategory="Test", name="Test")]
    filename = save_products_to_csv(products, "trulieve_FL_test")
    assert filename.startswith("trulieve_FL_test-")
    assert filename.endswith(".csv")

def test_snowflake_connection():
    """Snowflake connection works with test credentials"""
    with pytest.raises(Exception):  # Should fail without real credentials
        connect_to_snowflake("invalid", "invalid", "invalid")
```

```bash
# Run and iterate until passing:
uv run pytest agents/dispensary_scraper/tests/ -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test the complete workflow
cd agents/dispensary_scraper
python -m pytest tests/test_agent.py::test_end_to_end_scraping -v

# Test CLI interface
uv run python cli.py --categories "whole-flower" --headless --dry-run

# Expected: CSV files created, Snowflake upload attempted (may fail without credentials)
# Verify: Check ~/local/trulieve/ for generated CSV files
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest agents/dispensary_scraper/tests/ -v`
- [ ] No linting errors: `uv run ruff check agents/dispensary_scraper/`  
- [ ] No type errors: `uv run mypy agents/dispensary_scraper/`
- [ ] Manual scraping test: `python cli.py --categories whole-flower --limit 5`
- [ ] CSV files generated with correct naming convention
- [ ] Snowflake connection established (with valid credentials)
- [ ] Error cases handled gracefully (network failures, rate limits)
- [ ] Logs are informative but not verbose
- [ ] README.md provides complete setup instructions

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode URLs, API keys, or database credentials
- ❌ Don't ignore rate limiting - Trulieve will block aggressive scrapers
- ❌ Don't skip browser context cleanup - causes memory leaks
- ❌ Don't use synchronous operations in async context  
- ❌ Don't assume data fields are always present - handle missing/null values
- ❌ Don't create CSV files without proper error handling
- ❌ Don't upload to Snowflake without validating data first

**PRP Confidence Score: 9/10**

This PRP provides comprehensive context including:
✅ Working implementation reference (Jupyter notebook)
✅ Specific technical patterns and gotchas documented  
✅ External API documentation URLs included
✅ Clear task breakdown with implementation order
✅ Executable validation gates at multiple levels
✅ Anti-patterns and common pitfalls identified
✅ Realistic timeline and complexity assessment

The agent should be able to implement this successfully in one pass with the provided context and references.