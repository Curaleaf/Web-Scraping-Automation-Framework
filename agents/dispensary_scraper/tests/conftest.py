"""Test configuration and fixtures for dispensary scraper tests."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Generator, List
from unittest.mock import Mock, MagicMock

from ..models import ProductData, ScrapingConfig, StoreInfo
from ..dependencies import AgentDependencies
from ..storage.csv_storage import CSVStorage


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_product_data() -> List[ProductData]:
    """Sample product data for testing."""
    return [
        ProductData(
            store="Test Store FL",
            subcategory="Whole Flower",
            name="Blue Dream",
            brand="Test Brand",
            strain_type="Hybrid",
            thc_pct=18.5,
            size_raw="3.5g",
            grams=3.5,
            price=25.99,
            url="https://example.com/product/blue-dream"
        ),
        ProductData(
            store="Test Store FL",
            subcategory="Pre-Rolls",
            name="OG Kush Pre-Roll",
            brand="Premium Brand",
            strain_type="Indica",
            thc_pct=22.0,
            size_raw="1g",
            grams=1.0,
            price=12.50,
            url="https://example.com/product/og-kush-preroll"
        ),
        ProductData(
            store="Another Store FL",
            subcategory="Ground & Shake",
            name="Mixed Ground",
            brand=None,  # Test missing brand
            strain_type="Hybrid",
            thc_pct=None,  # Test missing THC
            size_raw="7g",
            grams=7.0,
            price=30.00,
            url="https://example.com/product/mixed-ground"
        )
    ]


@pytest.fixture
def sample_store_info() -> List[StoreInfo]:
    """Sample store information for testing."""
    return [
        StoreInfo(
            name="Miami Beach, FL",
            url="https://example.com/dispensaries/miami-beach-fl",
            location="Miami Beach, FL",
            state="FL"
        ),
        StoreInfo(
            name="Orlando South, FL",
            url="https://example.com/dispensaries/orlando-south-fl",
            location="Orlando South, FL",
            state="FL"
        )
    ]


@pytest.fixture
def scraping_config() -> ScrapingConfig:
    """Sample scraping configuration for testing."""
    return ScrapingConfig(
        base_url="https://test-example.com",
        dispensaries_url="https://test-example.com/dispensaries",
        categories=[
            {
                "url": "/category/flower/whole-flower",
                "subcategory": "Whole Flower",
                "prefix": "test_FL_whole_flower"
            },
            {
                "url": "/category/flower/pre-rolls",
                "subcategory": "Pre-Rolls",
                "prefix": "test_FL_pre_rolls"
            }
        ],
        output_dir="/tmp/test_output/",
        headless=True,
        rate_limit_delay=(100, 200)
    )


@pytest.fixture
def temp_csv_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for CSV file testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def csv_storage(temp_csv_directory) -> CSVStorage:
    """CSV storage instance with temporary directory."""
    return CSVStorage(str(temp_csv_directory))


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page for testing."""
    mock_page = Mock()
    
    # Mock common page methods
    mock_page.goto = Mock()
    mock_page.wait_for_timeout = Mock()
    mock_page.wait_for_load_state = Mock()
    mock_page.locator = Mock()
    mock_page.get_by_role = Mock()
    mock_page.mouse.wheel = Mock()
    mock_page.context = Mock()
    
    return mock_page


@pytest.fixture
def mock_playwright_locator():
    """Mock Playwright locator for testing."""
    mock_locator = Mock()
    
    # Mock locator methods
    mock_locator.count = Mock(return_value=1)
    mock_locator.first = Mock()
    mock_locator.nth = Mock(return_value=mock_locator)
    mock_locator.all = Mock(return_value=[mock_locator])
    mock_locator.text_content = Mock(return_value="Sample Text")
    mock_locator.inner_text = Mock(return_value="Sample Inner Text")
    mock_locator.get_attribute = Mock(return_value="/test/href")
    mock_locator.is_visible = Mock(return_value=True)
    mock_locator.click = Mock()
    
    return mock_locator


@pytest.fixture
def mock_browser_context():
    """Mock browser context for testing."""
    mock_context = Mock()
    mock_context.new_page = Mock()
    return mock_context


@pytest.fixture
def mock_browser():
    """Mock browser for testing."""
    mock_browser = Mock()
    mock_browser.new_context = Mock()
    mock_browser.close = Mock()
    return mock_browser


@pytest.fixture
def mock_playwright():
    """Mock Playwright instance for testing."""
    mock_playwright = Mock()
    mock_playwright.chromium.launch = Mock()
    return mock_playwright


@pytest.fixture
def mock_snowflake_connection():
    """Mock Snowflake connection for testing."""
    mock_connection = Mock()
    mock_cursor = Mock()
    
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.commit = Mock()
    mock_connection.close = Mock()
    
    mock_cursor.execute = Mock()
    mock_cursor.executemany = Mock()
    mock_cursor.fetchone = Mock(return_value=(1,))
    mock_cursor.fetchall = Mock(return_value=[])
    
    return mock_connection


@pytest.fixture
def mock_agent_dependencies() -> AgentDependencies:
    """Mock agent dependencies for testing."""
    deps = AgentDependencies()
    deps.session_id = "test-session-123"
    deps.user_preferences = {"test_pref": "test_value"}
    return deps


@pytest.fixture
def test_html_content() -> str:
    """Sample HTML content for testing data extraction."""
    return """
    <div class="product-card">
        <a href="/product/blue-dream-3-5g">Blue Dream</a>
        <div class="price">$25.99</div>
        <div class="brand">Premium Cannabis</div>
        <div class="details">
            <span>3.5g</span>
            <span>THC: 18.5%</span>
            <span>Hybrid</span>
        </div>
    </div>
    """


@pytest.fixture
def test_product_card_text() -> str:
    """Sample product card text for regex testing."""
    return """
    Blue Dream
    Premium Cannabis
    $25.99
    3.5g
    THC: 18.5%
    Hybrid
    Add to Cart
    """


# Environment variable fixtures
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ.update({
        "SNOWFLAKE_ACCOUNT": "test-account.snowflakecomputing.com",
        "SNOWFLAKE_USER": "test_user",
        "SNOWFLAKE_PASSWORD": "test_password",
        "SNOWFLAKE_WAREHOUSE": "TEST_WH",
        "SNOWFLAKE_DATABASE": "TEST_DB",
        "SNOWFLAKE_SCHEMA": "TEST_SCHEMA",
        "LLM_API_KEY": "test-api-key",
        "LLM_MODEL": "gpt-4o-mini",
        "SCRAPING_HEADLESS": "true",
        "OUTPUT_DIRECTORY": "/tmp/test_output/"
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Async test helpers
@pytest.fixture
def async_mock():
    """Create an async mock that can be awaited."""
    mock = MagicMock()
    mock.return_value = asyncio.Future()
    mock.return_value.set_result(None)
    return mock