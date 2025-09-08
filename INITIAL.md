## FEATURE:
Act as a world-class Software Engineer specializing in web scraping automation using Playwright and Python. Given the following context, criteria, and instructions, build an automation framework to scrape pricing data from dispensary websites and store it appropriately.

A Context Engineering template repository aimed at automating the extraction of pricing data from dispensary websites using Playwright and Python. The framework must handle recursive iteration through parent and child nodes for categories, extracting relevant pricing data while saving it in CSV format locally before moving the data to a Snowflake database.

Build an automation framework that can scrape pricing data from dispensary websites.
The automation process will recursively iterate through each parent and child node for every category, read the pricing data for each listed subcategory, and then save each subcategory dataframe first as CSV files and afterward into a Snowflake database.

1. Set up the project structure in accordance with best practices.
2. Utilize Playwright for navigating through the dispensary websites, specifically using the provided URLs to extract pricing data for each category.
3. Implement the recursive function to scrape data from every category, subcategory, and child node. 
4. Store the scraped pricing data in local CSV files using the naming convention `{OUT_PREFIX}-{date_time}.csv` in `~\local\{COMP}\`.
5. After completion of data extraction, connect to the Snowflake database using the Snowflake API and upload the data into the specified tables based on the categories.
6. Include test scripts for unit testing each scraping agent.

## Response Format
Provide a structured Python code base along with:
- CSV file outputs at the specified location.
- A connection script for uploading the data into the Snowflake database.
- Test scripts for each agent.
- A .env.example file for handling environmental variables.
- A README file that includes setup instructions and project structure documentation.     

Include test scripts to test each agent. 

## EXAMPLES:

1. Follow the examples provided in `example\Web scrape attempt.ipynb` for logic references.
2. Refer to `examples\CLAUDE.md` for the architecture of the automation framework.

## DOCUMENTATION:

COMP = "trulieve"

BASE = "https://www.trulieve.com"
DISPENSARIES_URL = f"{BASE}/dispensaries"
CATEGORY_URL = f"{BASE}/category/flower/whole-flower"
SUBCATEGORY   = "Whole Flower"
OUT_PREFIX    = "trulieve_FL_whole_flower"

BASE = "https://www.trulieve.com"
DISPENSARIES_URL = f"{BASE}/dispensaries"
CATEGORY_URL = f"{BASE}/category/flower/minis"
SUBCATEGORY  = "Ground & Shake"
OUT_PREFIX   = "trulieve_FL_ground_shake"

BASE = "https://www.trulieve.com"
DISPENSARIES_URL = f"{BASE}/dispensaries"
CATEGORY_URL = f"{BASE}/category/flower/pre-rolls"
SUBCATEGORY  = "Pre-Rolls"
OUT_PREFIX   = "trulieve_FL_pre_rolls"

BASE = "https://www.trulieve.com"
DISPENSARIES_URL = f"{BASE}/dispensaries"
CATEGORY_URL = f"{BASE}/category/flower/ground-shake"
SUBCATEGORY  = "Ground & Shake"
OUT_PREFIX   = "trulieve_FL_ground_shake"

Snowflake API documentation: https://docs.snowflake.com/en/developer-guide/sql-api/index
Snowflake Instance - CURALEAF-CURAPROD.snowflakecomputing.com

Database
    SANDBOX_EDW
Schema
    ANALYTICS
Table type
    Static
Table name
    TL_Scrape_WHOLE_FLOWER
    TL_Scrape_Pre_Rolls
    TL_Scrape_Ground_Shake



## OTHER CONSIDERATIONS:
- Include a .env.example, README with instructions for setup
- Include the project structure in the README.
- Virtual environment has already been set up with the necessary dependencies.
- Use python_dotenv and load_env() for environment variables




