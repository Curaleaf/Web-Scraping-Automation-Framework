# 🏪 Dispensary Scraper Agent

An intelligent web scraping automation framework for extracting pricing data from dispensary websites, built with Playwright and PydanticAI.

## 🚀 Features

- **Intelligent Web Scraping**: Uses Playwright for dynamic content extraction with anti-bot detection measures
- **Agent-Based Architecture**: Built on PydanticAI for intelligent workflow orchestration and error handling
- **Multi-Format Storage**: Saves data as CSV files locally and uploads to Snowflake data warehouse
- **Comprehensive Data Extraction**: Captures product names, brands, prices, THC content, strain types, and sizes
- **Rate Limiting**: Respects website terms with configurable delays and polite scraping practices
- **Robust Error Handling**: Graceful failure recovery with detailed logging and retry mechanisms
- **CLI Interface**: Rich command-line interface for easy operation and monitoring

## 📊 Supported Data Fields

- **Product Information**: Name, brand, category, strain type
- **Pricing Data**: Price, price per gram, size/weight
- **Content Analysis**: THC percentage, product descriptions
- **Metadata**: Store location, scraping timestamp, product URLs

## 🏗️ Architecture

```
agents/dispensary_scraper/
├── agent.py                 # Main PydanticAI agent orchestration
├── cli.py                   # Rich CLI interface
├── dependencies.py          # Dependency injection and lifecycle management
├── models.py                # Pydantic data models
├── providers.py             # LLM provider configuration
├── settings.py              # Environment configuration
├── tools.py                 # PydanticAI tools for agent capabilities
├── scrapers/                # Web scraping logic
│   ├── base_scraper.py      # Abstract base scraper with common patterns
│   ├── trulieve_scraper.py  # Trulieve-specific implementation
│   └── data_extractors.py   # Data extraction utilities and regex patterns
├── storage/                 # Data persistence
│   ├── csv_storage.py       # Local CSV file operations
│   └── snowflake_storage.py # Snowflake database integration
└── tests/                   # Comprehensive test suite
    ├── conftest.py          # Test configuration and fixtures
    ├── test_agent.py        # Agent integration tests
    ├── test_scrapers.py     # Scraping logic tests
    └── test_storage.py      # Storage operations tests
```

## 🚀 Quick Start

### Running the CLI

The Dispensary Scraper Agent provides multiple ways to run the command-line interface:

#### Method 1: Using the Main Entry Point
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run the CLI
python main.py --help
python main.py categories
python main.py test
```

#### Method 2: Using the Console Script (After Installation)
```bash
# After installing with pip install -e .
dispensary-scraper --help
dispensary-scraper categories
dispensary-scraper test
```

#### Method 3: Using the Windows Batch File
```bash
# Double-click or run from command prompt
.\run_scraper.bat --help
.\run_scraper.bat categories
.\run_scraper.bat test
```

#### Method 4: Running as a Python Module
```bash
python -m agents.dispensary_scraper.cli --help
```

### Available Commands

- `categories` - List available scraping categories
- `test` - Test connections to external services
- `scrape` - Run the dispensary scraping workflow
- `status` - Show scraper status and recent files
- `chat` - Start an interactive chat session with the scraper agent

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- Snowflake account (optional, for database storage)
- OpenAI API key (for agent functionality)

### Setup Instructions

1. **Clone and navigate to the project:**
   ```bash
   cd agents/dispensary_scraper/
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install  # Install browser binaries
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Environment Configuration

Create a `.env` file with the following variables:

```env
# Snowflake Configuration (required for database upload)
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SANDBOX_EDW
SNOWFLAKE_SCHEMA=ANALYTICS

# LLM Configuration (required for agent features)
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Scraping Configuration
SCRAPING_HEADLESS=true
SCRAPING_DELAY_MIN=700
SCRAPING_DELAY_MAX=1500
OUTPUT_DIRECTORY=~/local/trulieve/

# Target Website Configuration
BASE_URL=https://www.trulieve.com
DISPENSARIES_URL=https://www.trulieve.com/dispensaries
```

## 📖 Usage

### Command Line Interface

The CLI provides several commands for different operations:

#### 1. Run Scraping Workflow
```bash
# Scrape all categories
python cli.py scrape

# Scrape specific categories
python cli.py scrape -c "Whole Flower" -c "Pre-Rolls"

# Test configuration without scraping
python cli.py scrape --dry-run

# Skip CSV generation
python cli.py scrape --no-csv

# Skip Snowflake upload
python cli.py scrape --no-snowflake
```

#### 2. Test Connections
```bash
# Test all external connections
python cli.py test
```

#### 3. View Status and Configuration
```bash
# Show current status and recent files
python cli.py status

# List available categories
python cli.py categories
```

#### 4. Interactive Chat
```bash
# Start chat session with agent
python cli.py chat
```

### Programmatic Usage

#### Basic Scraping
```python
import asyncio
from agents.dispensary_scraper.agent import run_scraping_workflow

async def main():
    # Run complete workflow
    result = await run_scraping_workflow(
        categories=["Whole Flower", "Pre-Rolls"],
        save_csv=True,
        upload_snowflake=True
    )
    
    print(f"Scraped {result['products_scraped']} products")
    print(f"Saved {len(result['csv_files_saved'])} CSV files")

asyncio.run(main())
```

#### Agent Interaction
```python
import asyncio
from agents.dispensary_scraper.agent import chat_with_scraper_agent
from agents.dispensary_scraper.dependencies import AgentDependencies

async def main():
    # Initialize agent context
    deps = AgentDependencies()
    await deps.initialize()
    
    # Chat with agent
    response = await chat_with_scraper_agent(
        "Can you scrape the Whole Flower category?",
        context=deps
    )
    
    print(response)
    await deps.cleanup()

asyncio.run(main())
```

#### Direct Storage Operations
```python
from agents.dispensary_scraper.storage.csv_storage import CSVStorage
from agents.dispensary_scraper.models import ProductData

# Initialize storage
storage = CSVStorage("~/data/trulieve/")

# Load products from CSV
products = storage.load_products_from_csv("trulieve_FL_whole_flower-20240115_143000.csv")

# Save products by category
saved_files = storage.save_by_category(products)
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_scrapers.py -v

# Run with coverage
python -m pytest tests/ -v --cov

# Run only integration tests
python -m pytest tests/test_agent.py -v
```

### Test Categories

- **Unit Tests**: Test individual functions and data extraction logic
- **Integration Tests**: Test agent workflows and tool interactions
- **Storage Tests**: Test CSV and Snowflake storage operations
- **Mock Tests**: Test scraping logic with mocked browser components

## 📁 Output Structure

### CSV Files
CSV files are saved with timestamps using the naming convention:
```
{category_prefix}-{timestamp}.csv
```

Example files:
- `trulieve_FL_whole_flower-20240115_143000.csv`
- `trulieve_FL_pre_rolls-20240115_143000.csv`
- `trulieve_FL_ground_shake-20240115_143000.csv`

### Snowflake Tables
Data is uploaded to category-specific tables:
- `TL_Scrape_WHOLE_FLOWER`
- `TL_Scrape_Pre_Rolls`
- `TL_Scrape_Ground_Shake`

### Data Schema
```sql
CREATE TABLE TL_Scrape_WHOLE_FLOWER (
    state VARCHAR(10),
    store VARCHAR(255),
    subcategory VARCHAR(100),
    name VARCHAR(500),
    brand VARCHAR(255),
    strain_type VARCHAR(50),
    thc_pct FLOAT,
    size_raw VARCHAR(50),
    grams FLOAT,
    price FLOAT,
    price_per_g FLOAT,
    url VARCHAR(1000),
    scraped_at TIMESTAMP_NTZ,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

## ⚙️ Configuration Options

### Categories
The system supports scraping multiple product categories:

- **Whole Flower**: Traditional cannabis flower products
- **Pre-Rolls**: Pre-rolled joints and blunts  
- **Ground & Shake**: Ground cannabis and shake products

### Rate Limiting
Configure delays to respect website limits:
- `SCRAPING_DELAY_MIN`: Minimum delay between requests (ms)
- `SCRAPING_DELAY_MAX`: Maximum delay between requests (ms)

### Browser Settings
- `SCRAPING_HEADLESS`: Run browser in headless mode (true/false)
- Anti-detection measures automatically applied
- User-agent rotation and realistic browser behavior

## 🔧 Troubleshooting

### Common Issues

#### 1. Connection Errors
```bash
# Test all connections
python cli.py test

# Common fixes:
# - Check .env file configuration
# - Verify Snowflake credentials
# - Ensure network connectivity
```

#### 2. Scraping Failures  
```bash
# Check browser installation
playwright install

# Common fixes:
# - Update Playwright browsers
# - Check target website accessibility
# - Verify rate limiting settings
```

#### 3. Data Quality Issues
```bash
# Analyze recent scraping results
python cli.py chat
# Then ask: "Analyze the quality of my last scraping results"
```

### Debug Mode
Enable verbose logging for troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Development

### Code Quality
```bash
# Format and fix code style
ruff check --fix

# Type checking
mypy .

# Run all quality checks
ruff check --fix && mypy .
```

### Contributing
1. Follow existing code patterns and architecture
2. Add comprehensive tests for new functionality
3. Update documentation for any API changes
4. Ensure all quality checks pass before committing

## 🚨 Important Notes

### Legal and Ethical Considerations
- **Respect robots.txt**: Always check and follow website scraping policies
- **Rate Limiting**: Never overwhelm target websites with excessive requests
- **Terms of Service**: Ensure compliance with website terms and conditions
- **Data Privacy**: Handle scraped data responsibly and securely

### Performance Recommendations
- Use headless mode for production scraping
- Monitor memory usage during large scraping operations
- Implement appropriate retry mechanisms for network failures
- Consider running during off-peak hours to reduce server load

### Data Quality
- Regularly validate scraped data for completeness
- Monitor extraction patterns for website changes
- Implement alerts for significant data quality degradation
- Keep extraction logic updated with website modifications

## 📊 Monitoring and Analytics

### Built-in Analytics
The agent provides built-in data quality analysis:
```python
# Analyze data quality
result = await agent.analyze_scraped_data()
print(f"Data Quality Score: {result['data_quality_score']}%")
```

### Key Metrics to Monitor
- **Extraction Success Rate**: Percentage of successful product extractions
- **Data Completeness**: Percentage of complete product records
- **Scraping Duration**: Time taken for full workflow completion
- **Error Rates**: Frequency and types of scraping errors

## 🔗 Integration

### Snowflake Integration
Automatic data warehouse integration with:
- Schema validation and type conversion
- Batch upload optimization
- Connection pooling and error handling
- Table creation and management

### PydanticAI Tools
The agent includes specialized tools:
- `scrape_dispensary_categories`: Execute scraping workflows
- `test_connections`: Verify external service connectivity
- `analyze_scraped_data`: Perform data quality analysis
- `get_scraper_status`: Monitor system health

## 📈 Scaling Considerations

For large-scale operations:
- Implement distributed scraping across multiple instances
- Use message queues for workflow coordination
- Add monitoring and alerting systems
- Consider proxy rotation for high-volume scraping
- Implement data deduplication mechanisms

## 🎯 Future Enhancements

Planned improvements:
- Support for additional dispensary chains
- Real-time data streaming capabilities
- Advanced analytics and trend detection
- Mobile app integration
- API endpoints for external integrations
- Machine learning for price prediction

## 📞 Support

For issues, questions, or contributions:
- Review the troubleshooting section above
- Check existing test cases for usage examples
- Examine the codebase architecture documentation
- Follow the development guidelines for contributions