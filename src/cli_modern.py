"""
Modernized CLI using dependency injection and Protocol-based architecture.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
import json

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import logging

from src.domain import load_configuration, ConfigurationProvider, ConfigurationError
from src.services import (
    TesseractOCRService,
    OllamaClassificationService,
    create_ollama_service,
    DocumentProcessingService,
    create_document_processing_service,
)
from src.infrastructure import create_extraction_service


console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure application logging."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler('ai_document_pipeline.log')
        ]
    )


class ApplicationContainer:
    """Dependency injection container for the application."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the application container."""
        self.config = self._load_configuration(config_path)
        self.ocr_service = self._create_ocr_service()
        self.extraction_service = self._create_extraction_service()
        self.classification_service = self._create_classification_service()
        self.document_service = None  # Created lazily
    
    def _load_configuration(self, config_path: Optional[Path]) -> ConfigurationProvider:
        """Load application configuration."""
        try:
            return load_configuration(config_path)
        except ConfigurationError as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Failed to load configuration: {e}[/red]")
            sys.exit(1)
    
    def _create_ocr_service(self) -> TesseractOCRService:
        """Create OCR service."""
        try:
            ocr_settings = self.config.get_ocr_settings()
            return TesseractOCRService(
                language=ocr_settings.get('language', 'eng')
            )
        except Exception as e:
            console.print(f"[yellow]Warning: OCR service unavailable: {e}[/yellow]")
            return None
    
    def _create_extraction_service(self):
        """Create document extraction service."""
        return create_extraction_service(self.ocr_service)
    
    def _create_classification_service(self) -> OllamaClassificationService:
        """Create classification service."""
        return create_ollama_service(self.config)
    
    async def get_document_service(self) -> DocumentProcessingService:
        """Get or create document processing service."""
        if self.document_service is None:
            self.document_service = await create_document_processing_service(
                extraction_service=self.extraction_service,
                classification_service=self.classification_service,
                config=self.config,
            )
        return self.document_service


# Global container (initialized in CLI context)
app_container: Optional[ApplicationContainer] = None


def get_container(config_path: Optional[Path] = None) -> ApplicationContainer:
    """Get or create the application container."""
    global app_container
    if app_container is None:
        app_container = ApplicationContainer(config_path)
    return app_container


@click.group()
@click.version_option(version="1.0.0")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
def cli(config: Optional[Path], verbose: bool, quiet: bool):
    """AI-Powered Document Classification Pipeline.

    Automatically classify and organize multi-format documents
    (PDF, Excel, Word, Images) using local LLMs and OCR.
    
    Built with modern Python practices following SOLID principles.
    """
    setup_logging(verbose, quiet)
    
    # Initialize the container
    global app_container
    app_container = ApplicationContainer(config)
    
    if not quiet:
        console.print(Panel.fit(
            "AI Document Pipeline v1.0.0\nProtocol-based Architecture", 
            style="bold blue"
        ))


@cli.command()
@click.option("--host", help="Ollama host URL")
@click.option("--model", help="Ollama model name")
async def check(host: Optional[str], model: Optional[str]):
    """Check service availability and configuration."""
    container = get_container()
    
    console.print(Panel.fit("Service Status Check", style="bold blue"))
    
    # Check configuration
    try:
        categories = container.config.get_categories()
        console.print(f"✅ Configuration loaded: {len(categories)} categories")
    except Exception as e:
        console.print(f"❌ Configuration error: {e}")
        return
    
    # Check OCR service
    if container.ocr_service:
        supported_formats = container.ocr_service.get_supported_formats()
        console.print(f"✅ OCR Service: {len(supported_formats)} image formats supported")
    else:
        console.print("❌ OCR Service: Not available")
    
    # Check classification service
    try:
        available = await container.classification_service.is_available()
        if available:
            models = container.classification_service.get_available_models()
            console.print(f"✅ Classification Service: {len(models)} models available")
            
            # Display models
            if models:
                table = Table(title="Available Models")
                table.add_column("Model Name", style="cyan")
                for model in models[:10]:  # Show first 10
                    table.add_row(model)
                console.print(table)
        else:
            console.print("❌ Classification Service: Not available")
    except Exception as e:
        console.print(f"❌ Classification Service error: {e}")
    
    # Check extraction service
    try:
        supported_ext = container.extraction_service.get_supported_extensions()
        console.print(f"✅ Extraction Service: {len(supported_ext)} file types supported")
    except Exception as e:
        console.print(f"❌ Extraction Service error: {e}")


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output directory for organized files"
)
@click.option("--copy", is_flag=True, help="Copy files instead of moving them")
@click.option("--reasoning", is_flag=True, help="Include classification reasoning")
@click.option("--export", type=click.Path(path_type=Path), help="Export results to JSON")
@click.option("--pattern", default="*", help="File pattern to process")
async def process(
    input_path: Path,
    output: Optional[Path],
    copy: bool,
    reasoning: bool,
    export: Optional[Path],
    pattern: str,
):
    """Process documents for classification and organization."""
    container = get_container()
    
    # Override output directory if specified
    if output:
        # This would require updating the config, but for now we'll use it directly
        pass
    
    document_service = await container.get_document_service()
    
    console.print(f"Processing: {input_path}")
    console.print(f"Pattern: {pattern}")
    console.print(f"Copy files: {copy}")
    console.print(f"Include reasoning: {reasoning}")
    
    try:
        if input_path.is_file():
            # Process single file
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Processing {input_path.name}...", total=None)
                
                result = await document_service.process_document(
                    input_path, copy_files=copy, include_reasoning=reasoning
                )
                
                progress.update(task, completed=True)
            
            # Display result
            _display_single_result(result)
            
        else:
            # Process directory
            results = await document_service.process_directory(
                input_path, 
                copy_files=copy, 
                include_reasoning=reasoning,
                pattern=pattern
            )
            
            # Display summary
            _display_processing_summary(document_service, results)
        
        # Export results if requested
        if export:
            document_service.export_results(export)
            console.print(f"Results exported to: {export}")
            
    except Exception as e:
        console.print(f"[red]Processing failed: {e}[/red]")
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def categories():
    """List available classification categories."""
    container = get_container()
    
    try:
        categories = container.config.get_categories()
        
        table = Table(title="Classification Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Description", style="dim")
        
        # Add some descriptions for common categories
        descriptions = {
            "invoice": "Commercial invoices and bills",
            "receipt": "Purchase receipts and vouchers", 
            "contract": "Legal contracts and agreements",
            "report": "Business and technical reports",
            "letter": "Correspondence and letters",
            "form": "Forms and applications",
            "presentation": "Presentation slides",
            "spreadsheet": "Excel and CSV files",
            "manual": "User manuals and documentation",
            "other": "Unclassified documents"
        }
        
        for category in categories:
            description = descriptions.get(category, "")
            table.add_row(category, description)
        
        console.print(table)
        console.print(f"\nTotal: {len(categories)} categories")
        
    except Exception as e:
        console.print(f"[red]Failed to load categories: {e}[/red]")


@cli.command()
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def info(format: str):
    """Display system information and configuration."""
    container = get_container()
    
    if format == "json":
        info_data = {
            "categories": container.config.get_categories(),
            "database_enabled": container.config.use_database(),
            "output_directory": str(container.config.get_output_directory()),
            "ocr_available": container.ocr_service is not None,
        }
        
        if container.ocr_service:
            info_data["ocr_formats"] = container.ocr_service.get_supported_formats()
        
        console.print(json.dumps(info_data, indent=2))
    else:
        # Table format
        table = Table(title="System Information")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Categories", str(len(container.config.get_categories())))
        table.add_row("Database", "Enabled" if container.config.use_database() else "Disabled")
        table.add_row("Output Directory", str(container.config.get_output_directory()))
        table.add_row("OCR Available", "Yes" if container.ocr_service else "No")
        
        if container.ocr_service:
            formats = container.ocr_service.get_supported_formats()
            table.add_row("OCR Formats", f"{len(formats)} formats")
        
        console.print(table)


def _display_single_result(result):
    """Display result for a single processed document."""
    if result.success:
        console.print(f"✅ [green]{result.file_path.name}[/green]")
        console.print(f"   Category: [cyan]{result.category}[/cyan]")
        if result.confidence:
            console.print(f"   Confidence: {result.confidence:.2f}")
        if result.metadata.get("reasoning"):
            console.print(f"   Reasoning: {result.metadata['reasoning']}")
    else:
        console.print(f"❌ [red]{result.file_path.name}[/red]")
        console.print(f"   Error: {result.error}")


def _display_processing_summary(service: DocumentProcessingService, results: List):
    """Display summary of batch processing results."""
    summary = service.get_processing_summary()
    
    # Overall summary
    console.print(Panel.fit(
        f"Processed {summary['total']} documents\n"
        f"✅ Successful: {summary['successful']}\n"
        f"❌ Failed: {summary['failed']}\n"
        f"Average Confidence: {summary['average_confidence']:.2f}",
        title="Processing Summary",
        style="bold"
    ))
    
    # Category breakdown
    if summary['categories']:
        table = Table(title="Documents by Category")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="dim")
        
        total_successful = summary['successful']
        for category, count in sorted(summary['categories'].items()):
            percentage = (count / total_successful * 100) if total_successful > 0 else 0
            table.add_row(category, str(count), f"{percentage:.1f}%")
        
        console.print(table)


def run_async_command(coro):
    """Helper to run async commands."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# Make async commands work with click
def make_async(f):
    """Decorator to make async functions work with click."""
    def wrapper(*args, **kwargs):
        return run_async_command(f(*args, **kwargs))
    return wrapper

# Apply async decorator to commands
check.callback = make_async(check.callback)
process.callback = make_async(process.callback)


if __name__ == "__main__":
    cli()