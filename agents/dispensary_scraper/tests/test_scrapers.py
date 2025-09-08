"""Tests for scraping logic and data extraction functions."""

import pytest
from unittest.mock import Mock, patch
from typing import List

from ..scrapers.data_extractors import (
    grams_from_size,
    looks_like_florida,
    product_slug,
    extract_size_from_text,
    extract_strain_type_from_text,
    extract_thc_from_text,
    PRICE_RE,
    SIZE_RE,
    THC_SINGLE_RE,
    THC_RANGE_RE
)
from ..models import ProductData


class TestDataExtractors:
    """Test data extraction functions."""
    
    def test_grams_from_size(self):
        """Test grams conversion from size strings."""
        assert grams_from_size("3.5g") == 3.5
        assert grams_from_size("1g") == 1.0
        assert grams_from_size("7G") == 7.0  # Case insensitive
        assert grams_from_size("invalid") is None
        assert grams_from_size(None) is None
        assert grams_from_size("") is None
    
    def test_looks_like_florida(self):
        """Test Florida location detection."""
        # Positive cases
        assert looks_like_florida("/dispensaries/miami-fl", "Miami Beach, FL")
        assert looks_like_florida("/dispensaries/orlando", "Orlando FL")
        assert looks_like_florida("/dispensaries/tampa", "Tampa Store FL")
        assert looks_like_florida("/florida/miami", "Miami Store")
        assert looks_like_florida("/dispensaries/test-fl/", "Test Store")
        
        # Negative cases
        assert not looks_like_florida("/dispensaries/california", "Los Angeles, CA")
        assert not looks_like_florida("/dispensaries/new-york", "New York Store")
        assert not looks_like_florida("/dispensaries/test", "Generic Store")
    
    def test_product_slug(self):
        """Test product slug extraction."""
        assert product_slug("/product/blue-dream-3-5g") == "blue-dream-3-5g"
        assert product_slug("/product/og-kush-preroll?ref=test") == "og-kush-preroll"
        assert product_slug("/product/mixed-ground#section") == "mixed-ground"
        assert product_slug("/product/test/") == "test"
        assert product_slug("invalid-url") == "invalid-url"
        assert product_slug(None) == ""
    
    def test_extract_size_from_text(self):
        """Test size extraction from text."""
        assert extract_size_from_text("Blue Dream 3.5g Premium") == "3.5g"
        assert extract_size_from_text("Pre-Roll 1G Available") == "1g"
        assert extract_size_from_text("Ground 7g Mix") == "7g"
        assert extract_size_from_text("No size here") is None
        assert extract_size_from_text("") is None
    
    def test_extract_strain_type_from_text(self):
        """Test strain type extraction from text."""
        assert extract_strain_type_from_text("Blue Dream Hybrid Premium") == "Hybrid"
        assert extract_strain_type_from_text("OG Kush Indica Strong") == "Indica"
        assert extract_strain_type_from_text("Green Crack Sativa Energetic") == "Sativa"
        assert extract_strain_type_from_text("No strain type here") is None
        assert extract_strain_type_from_text("") is None
    
    def test_extract_thc_from_text(self):
        """Test THC percentage extraction from text."""
        # Single THC value
        assert extract_thc_from_text("Blue Dream THC: 18.5%") == 18.5
        assert extract_thc_from_text("High THC 22.0% content") == 22.0
        assert extract_thc_from_text("THC 15%") == 15.0
        
        # THC range (should return first value)
        assert extract_thc_from_text("THC: 18.5% - 20.2%") == 18.5
        
        # No THC found
        assert extract_thc_from_text("No THC information") is None
        assert extract_thc_from_text("") is None
    
    def test_regex_patterns(self):
        """Test regex patterns from notebook."""
        # Price pattern
        price_matches = list(PRICE_RE.finditer("Product costs $25.99 on sale"))
        assert len(price_matches) == 1
        assert float(price_matches[0].group(1)) == 25.99
        
        # Size pattern
        size_matches = list(SIZE_RE.finditer("Available in 3.5g and 7g sizes"))
        assert len(size_matches) == 2
        assert size_matches[0].group(1).lower() == "3.5g"
        assert size_matches[1].group(1).lower() == "7g"
        
        # THC single pattern
        thc_matches = list(THC_SINGLE_RE.finditer("THC content: 18.5%"))
        assert len(thc_matches) == 1
        assert float(thc_matches[0].group(1)) == 18.5
        
        # THC range pattern
        thc_range_matches = list(THC_RANGE_RE.finditer("THC: 18.5% - 22.0%"))
        assert len(thc_range_matches) == 1
        assert float(thc_range_matches[0].group(1)) == 18.5
        assert float(thc_range_matches[0].group(2)) == 22.0


class TestProductDataModel:
    """Test ProductData model validation and methods."""
    
    def test_product_data_validation(self, sample_product_data):
        """Test ProductData model validates correctly."""
        product = sample_product_data[0]
        
        assert product.store == "Test Store FL"
        assert product.subcategory == "Whole Flower"
        assert product.name == "Blue Dream"
        assert product.price == 25.99
        assert product.grams == 3.5
        assert product.price_per_g is None  # Not calculated by default
    
    def test_calculate_price_per_g(self):
        """Test price per gram calculation."""
        product = ProductData(
            store="Test Store",
            subcategory="Whole Flower",
            name="Test Product",
            price=35.00,
            grams=3.5
        )
        
        # Initially None
        assert product.price_per_g is None
        
        # Calculate price per gram
        product.calculate_price_per_g()
        assert product.price_per_g == 10.0  # 35.00 / 3.5
        
        # Test with missing data
        product_no_price = ProductData(
            store="Test Store",
            subcategory="Whole Flower", 
            name="Test Product",
            grams=3.5
        )
        product_no_price.calculate_price_per_g()
        assert product_no_price.price_per_g is None
        
        product_no_grams = ProductData(
            store="Test Store",
            subcategory="Whole Flower",
            name="Test Product", 
            price=35.00
        )
        product_no_grams.calculate_price_per_g()
        assert product_no_grams.price_per_g is None
    
    def test_product_data_defaults(self):
        """Test ProductData default values."""
        product = ProductData(
            store="Test Store",
            subcategory="Test Category",
            name="Test Product"
        )
        
        assert product.state == "FL"
        assert product.brand is None
        assert product.strain_type is None
        assert product.thc_pct is None
        assert product.size_raw is None
        assert product.grams is None
        assert product.price is None
        assert product.price_per_g is None
        assert product.url is None
        assert product.scraped_at is not None  # Should be set to current time


@pytest.mark.asyncio
class TestMockScrapingOperations:
    """Test scraping operations with mocked components."""
    
    async def test_extract_price_from_card_mock(self, mock_playwright_locator):
        """Test price extraction from mocked card element."""
        from ..scrapers.data_extractors import extract_price_from_card
        
        # Mock price element with text containing price
        mock_playwright_locator.text_content.return_value = "$25.99"
        mock_playwright_locator.count.return_value = 1
        
        # Mock the price locator
        mock_card = Mock()
        mock_card.locator.return_value = mock_playwright_locator
        
        price = await extract_price_from_card(mock_card)
        assert price == 25.99
    
    async def test_extract_brand_from_card_mock(self, mock_playwright_locator):
        """Test brand extraction from mocked card element."""
        from ..scrapers.data_extractors import extract_brand_from_card
        
        # Mock brand element
        mock_playwright_locator.text_content.return_value = "Premium Cannabis"
        mock_playwright_locator.count.return_value = 1
        
        mock_card = Mock()
        mock_card.locator.return_value = mock_playwright_locator
        
        brand = await extract_brand_from_card(mock_card)
        assert brand == "Premium Cannabis"
    
    async def test_extract_strain_type_from_card_mock(self, mock_playwright_locator):
        """Test strain type extraction from mocked card element."""
        from ..scrapers.data_extractors import extract_strain_type_from_card
        
        # Mock strain type element
        mock_playwright_locator.text_content.return_value = "This is a Hybrid strain"
        mock_playwright_locator.count.return_value = 1
        
        mock_card = Mock()
        mock_card.locator.return_value = mock_playwright_locator
        
        strain_type = await extract_strain_type_from_card(mock_card)
        assert strain_type == "Hybrid"
    
    @patch('..scrapers.data_extractors.extract_price_from_card')
    @patch('..scrapers.data_extractors.extract_brand_from_card') 
    @patch('..scrapers.data_extractors.extract_strain_type_from_card')
    async def test_extract_product_data_from_card_integration(
        self,
        mock_strain_extract,
        mock_brand_extract, 
        mock_price_extract,
        mock_playwright_locator
    ):
        """Test complete product data extraction integration."""
        from ..scrapers.data_extractors import extract_product_data_from_card
        
        # Setup mocks
        mock_price_extract.return_value = 25.99
        mock_brand_extract.return_value = "Premium Cannabis"
        mock_strain_extract.return_value = "Hybrid"
        
        # Mock the name link
        mock_name_link = Mock()
        mock_name_link.first.text_content.return_value = "Blue Dream"
        mock_name_link.first.get_attribute.return_value = "/product/blue-dream-3-5g"
        mock_name_link.count.return_value = 1
        
        mock_card = Mock()
        mock_card.locator.return_value = mock_name_link
        mock_card.inner_text.return_value = "Blue Dream Premium Cannabis $25.99 3.5g THC: 18.5% Hybrid"
        
        category_config = {
            "subcategory": "Whole Flower",
            "url": "/category/flower/whole-flower",
            "prefix": "trulieve_FL_whole_flower"
        }
        
        product = await extract_product_data_from_card(
            card=mock_card,
            category_config=category_config,
            store_name="Test Store FL",
            base_url="https://www.trulieve.com"
        )
        
        assert product is not None
        assert product.name == "Blue Dream"
        assert product.store == "Test Store FL"
        assert product.subcategory == "Whole Flower"
        assert product.price == 25.99
        assert product.brand == "Premium Cannabis"
        assert product.strain_type == "Hybrid"
        assert product.size_raw == "3.5g"
        assert product.grams == 3.5
        assert product.thc_pct == 18.5
        assert product.url == "https://www.trulieve.com/product/blue-dream-3-5g"