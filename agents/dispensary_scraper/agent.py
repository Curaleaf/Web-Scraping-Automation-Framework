"""Main dispensary scraper agent with PydanticAI integration."""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .providers import get_llm_model
from .dependencies import AgentDependencies
from .prompts import SYSTEM_PROMPT, WORKFLOW_GUIDANCE
from .models import ScrapingResult

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Create the dispensary scraper agent
scraper_agent = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT
)


@scraper_agent.system_prompt
def dynamic_context_prompt(ctx: RunContext[AgentDependencies]) -> str:
    """Dynamic system prompt that includes current agent state."""
    prompt_parts = [WORKFLOW_GUIDANCE]
    
    if ctx.deps.session_id:
        prompt_parts.append(f"Session ID: {ctx.deps.session_id}")
    
    # Add connection status if available
    if ctx.deps.settings:
        prompt_parts.append(f"Configured for: {ctx.deps.settings.base_url}")
        prompt_parts.append(f"Output directory: {ctx.deps.settings.output_directory}")
    
    # Add recent scraping results if available
    if ctx.deps.last_scraping_result:
        result = ctx.deps.last_scraping_result
        prompt_parts.append(
            f"Last scraping: {result.total_products} products, "
            f"{result.categories_scraped} categories, "
            f"{'successful' if result.success else 'failed'}"
        )
    
    # Add user preferences
    if ctx.deps.user_preferences:
        prefs_str = ", ".join(f"{k}={v}" for k, v in ctx.deps.user_preferences.items())
        prompt_parts.append(f"User preferences: {prefs_str}")
    
    return "\n\n".join(prompt_parts)


async def run_scraping_workflow(
    categories: Optional[List[str]] = None,
    save_csv: bool = True,
    upload_snowflake: bool = True,
    dependencies: Optional[AgentDependencies] = None
) -> Dict[str, Any]:
    """
    Run the scraping workflow independently of agent interaction.
    
    Args:
        categories: Optional list of categories to scrape
        save_csv: Whether to save CSV files
        upload_snowflake: Whether to upload to Snowflake
        dependencies: Optional pre-initialized dependencies
        
    Returns:
        Dictionary with workflow results
    """
    deps = dependencies
    cleanup_needed = False
    
    try:
        # Initialize dependencies if not provided
        if deps is None:
            deps = AgentDependencies()
            await deps.initialize()
            cleanup_needed = True
        
        # Run the workflow
        result = await deps.run_scraping_workflow(
            categories=categories,
            save_csv=save_csv,
            upload_snowflake=upload_snowflake
        )
        
        logger.info(f"Workflow completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in scraping workflow: {e}")
        return {
            "success": False,
            "error_message": str(e),
            "products_scraped": 0
        }
    
    finally:
        if cleanup_needed and deps:
            await deps.cleanup()


async def chat_with_scraper_agent(
    message: str,
    context: Optional[AgentDependencies] = None
) -> str:
    """
    Chat with the scraper agent.
    
    Args:
        message: User message
        context: Optional agent dependencies for context
        
    Returns:
        Agent response
    """
    if context is None:
        context = AgentDependencies()
        await context.initialize()
    
    try:
        result = await scraper_agent.run(message, deps=context)
        return result.data
    except Exception as e:
        logger.error(f"Error in agent conversation: {e}")
        return f"I encountered an error: {str(e)}"


def run_scraping_workflow_sync(
    categories: Optional[List[str]] = None,
    save_csv: bool = True,
    upload_snowflake: bool = True
) -> Dict[str, Any]:
    """
    Synchronous wrapper for the scraping workflow.
    
    Args:
        categories: Optional list of categories to scrape
        save_csv: Whether to save CSV files
        upload_snowflake: Whether to upload to Snowflake
        
    Returns:
        Dictionary with workflow results
    """
    import sys
    
    # Handle Windows event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        # Use existing event loop if available
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.create_task(run_scraping_workflow(
            categories, save_csv, upload_snowflake
        )).result()
    except RuntimeError:
        # No running loop, create new one
        return asyncio.run(run_scraping_workflow(
            categories, save_csv, upload_snowflake
        ))


# Example usage and demonstration
if __name__ == "__main__":
    async def demo_scraper_agent():
        """Demonstrate the dispensary scraper agent."""
        print("=== Dispensary Scraper Agent Demo ===\n")
        
        # Initialize dependencies
        deps = AgentDependencies()
        await deps.initialize()
        
        # Test connections
        print("Testing connections...")
        connections = deps.test_connections()
        for service, status in connections.items():
            print(f"  {service}: {'✓' if status else '✗'}")
        
        print("\n" + "="*50 + "\n")
        
        # Sample interaction
        messages = [
            "Hello! I need to scrape Trulieve dispensary data. Can you help me get started?",
            "What categories are available for scraping?",
            "Please run a test scrape for just the Whole Flower category",
            "Show me the results of the last scraping operation"
        ]
        
        for message in messages:
            print(f"User: {message}")
            
            response = await chat_with_scraper_agent(message, deps)
            
            print(f"Agent: {response}")
            print("-" * 50)
        
        # Cleanup
        await deps.cleanup()
    
    # Run the demo
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(demo_scraper_agent())