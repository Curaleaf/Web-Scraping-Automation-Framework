"""Tests for storage operations (CSV and Snowflake)."""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from ..storage.csv_storage import CSVStorage
from ..storage.snowflake_storage import SnowflakeStorage
from ..models import ProductData, ScrapingResult


class TestCSVStorage:
    """Test CSV storage operations."""
    
    def test_csv_storage_initialization(self, temp_csv_directory):
        """Test CSV storage initialization."""
        storage = CSVStorage(str(temp_csv_directory))
        assert storage.output_directory == temp_csv_directory
        assert temp_csv_directory.exists()
    
    def test_generate_filename(self, csv_storage):
        """Test filename generation."""
        prefix = "trulieve_FL_whole_flower"
        timestamp = datetime(2024, 1, 15, 14, 30, 0)
        
        filename = csv_storage._generate_filename(prefix, timestamp)
        assert filename == "trulieve_FL_whole_flower-20240115_143000.csv"
        
        # Test with current timestamp
        filename_current = csv_storage._generate_filename(prefix)
        assert filename_current.startswith("trulieve_FL_whole_flower-")
        assert filename_current.endswith(".csv")
    
    def test_save_products_to_csv(self, csv_storage, sample_product_data):
        """Test saving products to CSV file."""
        prefix = "test_FL_whole_flower"
        
        # Save products
        filepath = csv_storage.save_products_to_csv(sample_product_data, prefix)
        
        # Verify file was created
        assert Path(filepath).exists()
        assert filepath.endswith(".csv")
        
        # Verify content
        df = pd.read_csv(filepath)
        assert len(df) == len(sample_product_data)
        assert "store" in df.columns
        assert "subcategory" in df.columns
        assert "name" in df.columns
        assert "price" in df.columns
        
        # Check data integrity
        assert df.iloc[0]["name"] == "Blue Dream"
        assert df.iloc[0]["price"] == 25.99
        assert df.iloc[1]["subcategory"] == "Pre-Rolls"
    
    def test_save_products_empty_list(self, csv_storage):
        """Test saving empty product list raises error."""
        with pytest.raises(ValueError, match="No products provided"):
            csv_storage.save_products_to_csv([], "test_prefix")
    
    def test_save_by_category(self, csv_storage, sample_product_data):
        """Test saving products grouped by category."""
        saved_files = csv_storage.save_by_category(sample_product_data)
        
        # Should create files for each unique subcategory
        assert len(saved_files) == 3  # Whole Flower, Pre-Rolls, Ground & Shake
        
        # Verify all files exist
        for filepath in saved_files:
            assert Path(filepath).exists()
        
        # Check that files contain appropriate products
        whole_flower_file = next(f for f in saved_files if "whole_flower" in f)
        df_wf = pd.read_csv(whole_flower_file)
        assert len(df_wf) == 1
        assert df_wf.iloc[0]["subcategory"] == "Whole Flower"
        
        prerolls_file = next(f for f in saved_files if "pre_rolls" in f)
        df_pr = pd.read_csv(prerolls_file)
        assert len(df_pr) == 1
        assert df_pr.iloc[0]["subcategory"] == "Pre-Rolls"
    
    def test_load_products_from_csv(self, csv_storage, sample_product_data):
        """Test loading products from CSV file."""
        # First save some data
        filepath = csv_storage.save_products_to_csv(sample_product_data, "test_load")
        
        # Then load it back
        loaded_products = csv_storage.load_products_from_csv(filepath)
        
        assert len(loaded_products) == len(sample_product_data)
        
        # Check data integrity (order might differ due to sorting)
        loaded_names = {p.name for p in loaded_products}
        original_names = {p.name for p in sample_product_data}
        assert loaded_names == original_names
        
        # Check specific product
        blue_dream = next(p for p in loaded_products if p.name == "Blue Dream")
        assert blue_dream.price == 25.99
        assert blue_dream.grams == 3.5
        assert blue_dream.brand == "Test Brand"
    
    def test_load_nonexistent_csv(self, csv_storage):
        """Test loading from non-existent CSV file."""
        with pytest.raises(FileNotFoundError):
            csv_storage.load_products_from_csv("/nonexistent/file.csv")
    
    def test_list_csv_files(self, csv_storage, sample_product_data):
        """Test listing CSV files in directory."""
        # Create some test files
        csv_storage.save_products_to_csv(sample_product_data[:1], "test_file_1")
        csv_storage.save_products_to_csv(sample_product_data[1:2], "test_file_2")
        
        # List files
        csv_files = csv_storage.list_csv_files()
        
        assert len(csv_files) >= 2
        assert all(f.suffix == ".csv" for f in csv_files)
        
        # Test pattern matching
        test_files = csv_storage.list_csv_files("test_file_*.csv")
        assert len(test_files) >= 2
    
    def test_products_to_dataframe(self, csv_storage, sample_product_data):
        """Test conversion of products to DataFrame."""
        df = csv_storage._products_to_dataframe(sample_product_data)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_product_data)
        
        # Check column order
        expected_first_cols = ["state", "store", "subcategory", "name", "brand"]
        actual_first_cols = df.columns[:5].tolist()
        assert actual_first_cols == expected_first_cols
        
        # Check data types and content
        assert df.iloc[0]["state"] == "FL"
        assert df.iloc[0]["price"] == 25.99
        assert pd.isna(df.iloc[2]["brand"])  # Missing brand test


class TestSnowflakeStorage:
    """Test Snowflake storage operations with mocks."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for Snowflake testing."""
        mock_settings = Mock()
        mock_settings.snowflake_account = "test-account.snowflakecomputing.com"
        mock_settings.snowflake_user = "test_user"
        mock_settings.snowflake_password = "test_password"
        mock_settings.snowflake_warehouse = "TEST_WH"
        mock_settings.snowflake_database = "TEST_DB"
        mock_settings.snowflake_schema = "TEST_SCHEMA"
        return mock_settings
    
    def test_snowflake_storage_initialization(self, mock_settings):
        """Test Snowflake storage initialization."""
        storage = SnowflakeStorage(mock_settings)
        assert storage.settings == mock_settings
    
    def test_get_connection_params(self, mock_settings):
        """Test connection parameter generation."""
        storage = SnowflakeStorage(mock_settings)
        params = storage._get_connection_params()
        
        expected_params = {
            "account": "test-account.snowflakecomputing.com",
            "user": "test_user",
            "password": "test_password",
            "warehouse": "TEST_WH",
            "database": "TEST_DB",
            "schema": "TEST_SCHEMA",
            "application": "DispensaryScraper"
        }
        
        assert params == expected_params
    
    def test_get_table_name(self, mock_settings):
        """Test table name mapping."""
        storage = SnowflakeStorage(mock_settings)
        
        assert storage._get_table_name("Whole Flower") == "TL_Scrape_WHOLE_FLOWER"
        assert storage._get_table_name("Pre-Rolls") == "TL_Scrape_Pre_Rolls"
        assert storage._get_table_name("Ground & Shake") == "TL_Scrape_Ground_Shake"
        assert storage._get_table_name("Custom Category") == "TL_Scrape_CUSTOM_CATEGORY"
    
    def test_products_to_dataframe(self, mock_settings, sample_product_data):
        """Test product to DataFrame conversion for Snowflake."""
        storage = SnowflakeStorage(mock_settings)
        df = storage._products_to_dataframe(sample_product_data)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_product_data)
        
        # Check numeric columns are properly typed
        if 'price' in df.columns:
            assert pd.api.types.is_numeric_dtype(df['price'])
        if 'thc_pct' in df.columns:
            assert pd.api.types.is_numeric_dtype(df['thc_pct'])
        if 'grams' in df.columns:
            assert pd.api.types.is_numeric_dtype(df['grams'])
    
    @patch('snowflake.connector.connect')
    def test_test_connection(self, mock_connect, mock_settings, mock_snowflake_connection):
        """Test Snowflake connection testing."""
        mock_connect.return_value.__enter__.return_value = mock_snowflake_connection
        mock_connect.return_value.__exit__.return_value = None
        
        storage = SnowflakeStorage(mock_settings)
        result = storage.test_connection()
        
        assert result is True
        mock_connect.assert_called_once()
        mock_snowflake_connection.cursor.assert_called_once()
        mock_snowflake_connection.cursor().execute.assert_called_with("SELECT 1")
    
    @patch('snowflake.connector.connect')
    def test_test_connection_failure(self, mock_connect, mock_settings):
        """Test Snowflake connection test failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        storage = SnowflakeStorage(mock_settings)
        result = storage.test_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('snowflake.connector.connect')
    async def test_create_table_if_not_exists(self, mock_connect, mock_settings, mock_snowflake_connection):
        """Test table creation."""
        # Setup async context manager mock
        mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_snowflake_connection)
        mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        storage = SnowflakeStorage(mock_settings)
        
        # Mock the get_connection context manager
        with patch.object(storage, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_snowflake_connection)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await storage.create_table_if_not_exists("TL_Scrape_WHOLE_FLOWER")
            
            assert result is True
            mock_snowflake_connection.cursor().execute.assert_called_once()
            
            # Check that CREATE TABLE statement was executed
            executed_sql = mock_snowflake_connection.cursor().execute.call_args[0][0]
            assert "CREATE TABLE IF NOT EXISTS TL_Scrape_WHOLE_FLOWER" in executed_sql
    
    @pytest.mark.asyncio
    async def test_upload_products(self, mock_settings, sample_product_data):
        """Test product upload to Snowflake."""
        storage = SnowflakeStorage(mock_settings)
        
        # Mock the upload_products_to_table method
        with patch.object(storage, 'upload_products_to_table') as mock_upload:
            mock_upload.return_value = 1
            
            result = await storage.upload_products(sample_product_data)
            
            # Should call upload for each unique subcategory
            assert mock_upload.call_count == 3  # Whole Flower, Pre-Rolls, Ground & Shake
            assert isinstance(result, dict)
            assert len(result) == 3
    
    def test_generate_data_quality_recommendations(self):
        """Test data quality recommendation generation."""
        from ..tools import _generate_data_quality_recommendations
        
        # High quality data
        recommendations = _generate_data_quality_recommendations(95, 90, 85, 80, 90)
        assert len(recommendations) == 1
        assert "quality looks good" in recommendations[0].lower()
        
        # Low quality data
        recommendations = _generate_data_quality_recommendations(60, 50, 40, 30, 70)
        assert len(recommendations) > 1
        assert any("price" in rec.lower() for rec in recommendations)
        assert any("brand" in rec.lower() for rec in recommendations)
        assert any("thc" in rec.lower() for rec in recommendations)


class TestScrapingResult:
    """Test ScrapingResult model."""
    
    def test_scraping_result_creation(self, sample_product_data):
        """Test ScrapingResult model creation."""
        result = ScrapingResult(
            success=True,
            products=sample_product_data,
            categories_scraped=2,
            stores_scraped=5,
            duration_seconds=120.5
        )
        
        assert result.success is True
        assert len(result.products) == 3
        assert result.total_products == 3
        assert result.categories_scraped == 2
        assert result.stores_scraped == 5
        assert result.duration_seconds == 120.5
        assert result.error_message is None
    
    def test_scraping_result_failure(self):
        """Test ScrapingResult for failed scraping."""
        result = ScrapingResult(
            success=False,
            error_message="Network timeout",
            duration_seconds=30.0
        )
        
        assert result.success is False
        assert result.error_message == "Network timeout"
        assert result.total_products == 0
        assert len(result.products) == 0