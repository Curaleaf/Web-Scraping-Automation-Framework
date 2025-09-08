#!/usr/bin/env python3
"""Basic validation script to test core functionality."""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from models import ProductData, ScrapingConfig, ScrapingResult
        print("[OK] Models imported successfully")
    except Exception as e:
        print(f"[FAIL] Models import failed: {e}")
        return False
    
    try:
        from settings import load_settings
        print("[OK] Settings imported successfully")
    except Exception as e:
        print(f"[FAIL] Settings import failed: {e}")
        return False
    
    try:
        from scrapers.data_extractors import grams_from_size, extract_thc_from_text
        print("[OK] Data extractors imported successfully")
    except Exception as e:
        print(f"[FAIL] Data extractors import failed: {e}")
        return False
    
    try:
        from storage.csv_storage import CSVStorage
        print("[OK] CSV storage imported successfully")
    except Exception as e:
        print(f"[FAIL] CSV storage import failed: {e}")
        return False
    
    return True

def test_data_models():
    """Test data model creation and validation."""
    print("\nTesting data models...")
    
    try:
        from models import ProductData, ScrapingConfig
        
        # Test ProductData creation
        product = ProductData(
            store="Test Store FL",
            subcategory="Whole Flower",
            name="Blue Dream",
            price=25.99,
            grams=3.5
        )
        
        # Test price per gram calculation
        product.calculate_price_per_g()
        expected_price_per_g = round(25.99 / 3.5, 2)
        
        if product.price_per_g == expected_price_per_g:
            print("[OK] ProductData creation and price calculation working")
        else:
            print(f"[FAIL] Price per gram calculation failed: expected {expected_price_per_g}, got {product.price_per_g}")
            return False
        
        # Test ScrapingConfig
        config = ScrapingConfig()
        if config.base_url == "https://www.trulieve.com":
            print("[OK] ScrapingConfig default values working")
        else:
            print(f"[FAIL] ScrapingConfig default values failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] Data model test failed: {e}")
        return False

def test_data_extractors():
    """Test data extraction functions."""
    print("\nTesting data extractors...")
    
    try:
        from scrapers.data_extractors import (
            grams_from_size, 
            extract_thc_from_text, 
            extract_size_from_text,
            looks_like_florida
        )
        
        # Test grams conversion
        if grams_from_size("3.5g") == 3.5:
            print("[OK] Grams conversion working")
        else:
            print("[FAIL] Grams conversion failed")
            return False
        
        # Test THC extraction
        thc = extract_thc_from_text("Blue Dream THC: 18.5% Premium")
        if thc == 18.5:
            print("[OK] THC extraction working")
        else:
            print(f"[FAIL] THC extraction failed: expected 18.5, got {thc}")
            return False
        
        # Test size extraction
        size = extract_size_from_text("Blue Dream 3.5g Premium")
        if size == "3.5g":
            print("[OK] Size extraction working")
        else:
            print(f"[FAIL] Size extraction failed: expected '3.5g', got {size}")
            return False
        
        # Test Florida detection
        if looks_like_florida("/dispensaries/miami-fl", "Miami Beach, FL"):
            print("[OK] Florida location detection working")
        else:
            print("[FAIL] Florida location detection failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Data extractor test failed: {e}")
        return False

def test_csv_storage():
    """Test CSV storage functionality."""
    print("\nTesting CSV storage...")
    
    try:
        from storage.csv_storage import CSVStorage
        from models import ProductData
        import tempfile
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = CSVStorage(temp_dir)
            
            # Create test data
            products = [
                ProductData(
                    store="Test Store FL",
                    subcategory="Whole Flower",
                    name="Blue Dream",
                    price=25.99,
                    grams=3.5
                ),
                ProductData(
                    store="Test Store FL",
                    subcategory="Pre-Rolls",
                    name="OG Kush Pre-Roll",
                    price=12.50,
                    grams=1.0
                )
            ]
            
            # Test filename generation
            filename = storage._generate_filename("test_prefix")
            if filename.startswith("test_prefix-") and filename.endswith(".csv"):
                print("[OK] CSV filename generation working")
            else:
                print(f"[FAIL] CSV filename generation failed: {filename}")
                return False
            
            # Test DataFrame conversion
            df = storage._products_to_dataframe(products)
            if len(df) == 2 and "store" in df.columns:
                print("[OK] DataFrame conversion working")
            else:
                print("[FAIL] DataFrame conversion failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"[FAIL] CSV storage test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 50)
    print("Dispensary Scraper Agent - Validation Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_data_models,
        test_data_extractors,
        test_csv_storage
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Validation Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    if failed == 0:
        print("SUCCESS: All validation tests passed!")
        return 0
    else:
        print("ERROR: Some validation tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())