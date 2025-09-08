"""Tests for the main agent integration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pydantic_ai.models.test import TestModel

from ..agent import (
    scraper_agent,
    run_scraping_workflow,
    chat_with_scraper_agent,
    run_scraping_workflow_sync
)
from ..dependencies import AgentDependencies
from ..models import ScrapingResult


class TestScraperAgent:
    """Test the main scraper agent functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent is properly initialized."""
        assert scraper_agent is not None
        assert scraper_agent.deps_type == AgentDependencies
    
    @pytest.mark.asyncio
    async def test_chat_with_scraper_agent_basic(self):
        """Test basic chat functionality with TestModel."""
        # Use TestModel to avoid API calls
        with patch('..agent.get_llm_model', return_value=TestModel()):
            deps = AgentDependencies()
            await deps.initialize()
            
            response = await chat_with_scraper_agent(
                "Hello, can you help me scrape dispensary data?",
                context=deps
            )
            
            assert isinstance(response, str)
            assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_run_scraping_workflow_success(self, sample_product_data):
        """Test successful scraping workflow execution."""
        # Mock the dependencies and workflow
        mock_deps = Mock(spec=AgentDependencies)
        mock_deps.initialize = AsyncMock()
        mock_deps.cleanup = AsyncMock()
        mock_deps.run_scraping_workflow = AsyncMock(return_value={
            "success": True,
            "products_scraped": 3,
            "categories_scraped": 1,
            "stores_scraped": 2,
            "duration_seconds": 120.0,
            "csv_files_saved": ["/tmp/test.csv"],
            "snowflake_upload_results": {"TL_Scrape_WHOLE_FLOWER": 3},
            "error_message": None
        })
        
        with patch('..agent.AgentDependencies', return_value=mock_deps):
            result = await run_scraping_workflow(
                categories=["Whole Flower"],
                save_csv=True,
                upload_snowflake=True
            )
            
            assert result["success"] is True
            assert result["products_scraped"] == 3
            assert result["categories_scraped"] == 1
            assert result["stores_scraped"] == 2
            assert len(result["csv_files_saved"]) == 1
    
    @pytest.mark.asyncio
    async def test_run_scraping_workflow_failure(self):
        """Test scraping workflow failure handling."""
        mock_deps = Mock(spec=AgentDependencies)
        mock_deps.initialize = AsyncMock()
        mock_deps.cleanup = AsyncMock()
        mock_deps.run_scraping_workflow = AsyncMock(side_effect=Exception("Network error"))
        
        with patch('..agent.AgentDependencies', return_value=mock_deps):
            result = await run_scraping_workflow(
                categories=["Whole Flower"]
            )
            
            assert result["success"] is False
            assert "Network error" in result["error_message"]
            assert result["products_scraped"] == 0
    
    def test_run_scraping_workflow_sync(self):
        """Test synchronous wrapper for scraping workflow."""
        with patch('..agent.run_scraping_workflow') as mock_async_run:
            mock_async_run.return_value = {"success": True, "products_scraped": 5}
            
            # Mock asyncio.run
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = {"success": True, "products_scraped": 5}
                
                result = run_scraping_workflow_sync(categories=["Pre-Rolls"])
                
                assert result["success"] is True
                assert result["products_scraped"] == 5


class TestAgentDependencies:
    """Test AgentDependencies functionality."""
    
    @pytest.mark.asyncio
    async def test_dependencies_initialization(self):
        """Test dependencies initialization."""
        deps = AgentDependencies()
        
        # Mock the load_settings to avoid file system dependencies
        with patch('..dependencies.load_settings') as mock_load_settings:
            mock_settings = Mock()
            mock_settings.output_directory = "/tmp/test/"
            mock_settings.base_url = "https://test.com"
            mock_settings.dispensaries_url = "https://test.com/dispensaries"
            mock_settings.categories = []
            mock_settings.scraping_headless = True
            mock_settings.scraping_delay_min = 700
            mock_settings.scraping_delay_max = 1500
            mock_load_settings.return_value = mock_settings
            
            await deps.initialize()
            
            assert deps.settings == mock_settings
            assert deps.csv_storage is not None
            assert deps.snowflake_storage is not None
            assert deps.scraper is not None
    
    @pytest.mark.asyncio
    async def test_dependencies_cleanup(self):
        """Test dependencies cleanup."""
        deps = AgentDependencies()
        deps.snowflake_storage = Mock()
        
        # Should not raise any exceptions
        await deps.cleanup()
    
    def test_user_preferences(self):
        """Test user preference management."""
        deps = AgentDependencies()
        
        # Set preferences
        deps.set_user_preference("test_key", "test_value")
        deps.set_user_preference("numeric_key", 42)
        
        # Get preferences
        assert deps.get_user_preference("test_key") == "test_value"
        assert deps.get_user_preference("numeric_key") == 42
        assert deps.get_user_preference("nonexistent", "default") == "default"
        
        # Check all preferences
        assert "test_key" in deps.user_preferences
        assert "numeric_key" in deps.user_preferences
    
    def test_connection_tests(self, temp_csv_directory):
        """Test connection testing functionality."""
        deps = AgentDependencies()
        
        # Mock CSV storage with temp directory
        mock_csv_storage = Mock()
        mock_csv_storage.output_directory = temp_csv_directory
        deps.csv_storage = mock_csv_storage
        
        # Mock Snowflake storage
        mock_snowflake_storage = Mock()
        mock_snowflake_storage.test_connection.return_value = True
        deps.snowflake_storage = mock_snowflake_storage
        
        results = deps.test_connections()
        
        assert "csv_storage" in results
        assert "snowflake" in results
        assert results["snowflake"] is True
    
    @pytest.mark.asyncio
    async def test_run_scraping_workflow_integration(self, sample_product_data):
        """Test integrated scraping workflow."""
        deps = AgentDependencies()
        
        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.scrape_all_categories = AsyncMock(return_value=ScrapingResult(
            success=True,
            products=sample_product_data,
            categories_scraped=1,
            stores_scraped=2,
            duration_seconds=60.0
        ))
        mock_scraper.config.categories = []
        deps.scraper = mock_scraper
        
        # Mock storages
        mock_csv_storage = Mock()
        mock_csv_storage.save_by_category.return_value = ["/tmp/test.csv"]
        deps.csv_storage = mock_csv_storage
        
        mock_snowflake_storage = Mock()
        mock_snowflake_storage.upload_products = AsyncMock(return_value={"TL_Scrape_WHOLE_FLOWER": 3})
        deps.snowflake_storage = mock_snowflake_storage
        
        # Run workflow
        result = await deps.run_scraping_workflow(
            categories=["Whole Flower"],
            save_csv=True,
            upload_snowflake=True
        )
        
        assert result["success"] is True
        assert result["products_scraped"] == 3
        assert len(result["csv_files_saved"]) == 1
        assert result["snowflake_upload_results"]["TL_Scrape_WHOLE_FLOWER"] == 3
    
    def test_get_status_summary(self):
        """Test status summary generation."""
        deps = AgentDependencies()
        deps.session_id = "test-session-123"
        deps.user_preferences = {"test_pref": "test_value"}
        
        # Mock settings
        mock_settings = Mock()
        deps.settings = mock_settings
        
        # Mock scraper
        mock_scraper = Mock()
        deps.scraper = mock_scraper
        
        # Mock last scraping result
        mock_result = Mock()
        mock_result.success = True
        mock_result.total_products = 10
        mock_result.duration_seconds = 120.0
        deps.last_scraping_result = mock_result
        
        status = deps.get_status_summary()
        
        assert status["initialized"] is True
        assert status["session_id"] == "test-session-123"
        assert status["user_preferences"]["test_pref"] == "test_value"
        assert status["last_scraping"]["success"] is True
        assert status["last_scraping"]["products_count"] == 10
        assert status["last_scraping"]["duration"] == 120.0


class TestAgentTools:
    """Test agent tools functionality."""
    
    @pytest.mark.asyncio
    async def test_scrape_dispensary_categories_tool(self, sample_product_data):
        """Test the scrape_dispensary_categories tool."""
        from ..tools import scrape_dispensary_categories
        
        # Mock dependencies
        mock_deps = Mock()
        mock_deps.run_scraping_workflow = AsyncMock(return_value={
            "success": True,
            "products_scraped": 3,
            "categories_scraped": 1,
            "stores_scraped": 2,
            "duration_seconds": 120.0,
            "csv_files_saved": ["/tmp/test.csv"],
            "snowflake_upload_results": {"TL_Scrape_WHOLE_FLOWER": 3}
        })
        
        # Mock run context
        mock_ctx = Mock()
        mock_ctx.deps = mock_deps
        
        result = await scrape_dispensary_categories(
            ctx=mock_ctx,
            categories=["Whole Flower"],
            save_csv=True,
            upload_snowflake=True
        )
        
        assert result["status"] == "success"
        assert result["products_scraped"] == 3
        assert result["categories_completed"] == 1
        assert result["stores_processed"] == 2
        assert result["csv_files_saved"] == 1
        assert result["total_uploaded_to_snowflake"] == 3
    
    @pytest.mark.asyncio
    async def test_test_connections_tool(self):
        """Test the test_connections tool."""
        from ..tools import test_connections
        
        # Mock dependencies
        mock_deps = Mock()
        mock_deps.test_connections.return_value = {
            "csv_storage": True,
            "snowflake": True
        }
        
        # Mock run context
        mock_ctx = Mock()
        mock_ctx.deps = mock_deps
        
        result = await test_connections(ctx=mock_ctx)
        
        assert result["status"] == "success"
        assert result["all_connections_healthy"] is True
        assert result["csv_storage"] is True
        assert result["snowflake_database"] is True
    
    @pytest.mark.asyncio
    async def test_get_scraper_status_tool(self):
        """Test the get_scraper_status tool."""
        from ..tools import get_scraper_status
        
        # Mock dependencies
        mock_deps = Mock()
        mock_deps.get_status_summary.return_value = {
            "initialized": True,
            "session_id": "test-session",
            "user_preferences": {"test": "value"},
            "last_scraping": {"success": True, "products_count": 10}
        }
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.base_url = "https://test.com"
        mock_settings.output_directory = "/tmp/test/"
        mock_settings.scraping_headless = True
        mock_settings.scraping_delay_min = 700
        mock_settings.scraping_delay_max = 1500
        mock_settings.categories = [{"subcategory": "Whole Flower"}]
        mock_deps.settings = mock_settings
        
        # Mock run context
        mock_ctx = Mock()
        mock_ctx.deps = mock_deps
        
        result = await get_scraper_status(ctx=mock_ctx)
        
        assert result["status"] == "success"
        assert result["agent_initialized"] is True
        assert result["session_id"] == "test-session"
        assert "configuration" in result
        assert result["configuration"]["base_url"] == "https://test.com"
    
    @pytest.mark.asyncio
    async def test_analyze_scraped_data_tool(self, sample_product_data):
        """Test the analyze_scraped_data tool."""
        from ..tools import analyze_scraped_data
        
        # Mock dependencies with scraping result
        mock_result = Mock()
        mock_result.products = sample_product_data
        
        mock_deps = Mock()
        mock_deps.last_scraping_result = mock_result
        
        # Mock run context
        mock_ctx = Mock()
        mock_ctx.deps = mock_deps
        
        result = await analyze_scraped_data(ctx=mock_ctx)
        
        assert result["status"] == "success"
        assert "analysis_summary" in result
        assert result["analysis_summary"]["total_products"] == 3
        assert "data_completeness" in result
        assert "data_quality_score" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_set_scraper_preferences_tool(self):
        """Test the set_scraper_preferences tool."""
        from ..tools import set_scraper_preferences
        
        # Mock dependencies
        mock_deps = Mock()
        mock_deps.user_preferences = {}
        mock_deps.set_user_preference = Mock()
        
        # Mock run context
        mock_ctx = Mock()
        mock_ctx.deps = mock_deps
        
        preferences = {
            "rate_limit_delay": 1000,
            "save_format": "csv"
        }
        
        result = await set_scraper_preferences(
            ctx=mock_ctx,
            preferences=preferences
        )
        
        assert result["status"] == "success"
        assert result["message"] == "Set 2 preferences"
        assert result["preferences_set"] == preferences
        
        # Verify preferences were set
        assert mock_deps.set_user_preference.call_count == 2