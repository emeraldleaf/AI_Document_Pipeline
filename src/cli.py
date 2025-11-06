"""Command-line interface for the document classification pipeline."""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from config import settings
from src.classifier import DocumentClassifier, DocumentOrganizer
from src.ollama_service import OllamaService
from src.training_utils import (
    TrainingDataCollector,
    ClassificationEvaluator,
    FewShotLearning,
    generate_modelfile,
)

# Optional database support
try:
    from src.database import DatabaseService, check_database_available
    DATABASE_AVAILABLE = check_database_available()
except ImportError:
    DATABASE_AVAILABLE = False


console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity."""
    logger.remove()  # Remove default handler

    if verbose:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="DEBUG",
        )
    else:
        logger.add(
            sys.stderr,
            format="<level>{level: <8}</level> | <level>{message}</level>",
            level="INFO",
        )


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """AI-Powered Document Classification Pipeline using Ollama.

    Automatically classify and organize multi-format documents
    (PDF, Excel, Word, etc.) using local LLMs.
    """
    pass


@cli.command()
@click.option(
    "--host",
    default=None,
    help=f"Ollama host URL (default: {settings.ollama_host})",
)
@click.option(
    "--model",
    default=None,
    help=f"Ollama model name (default: {settings.ollama_model})",
)
def check(host: Optional[str], model: Optional[str]):
    """Check Ollama service availability and list models."""
    console.print(Panel.fit("Ollama Service Check", style="bold blue"))

    ollama = OllamaService(host=host, model=model)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Checking Ollama service...", total=None)

        if ollama.is_available():
            console.print("[green]✓[/green] Ollama service is available")
            console.print(f"[blue]Host:[/blue] {ollama.host}")
            console.print(f"[blue]Model:[/blue] {ollama.model}")

            models = ollama.list_models()
            if models:
                console.print(f"\n[blue]Available models:[/blue]")
                for m in models:
                    console.print(f"  • {m}")
            else:
                console.print("\n[yellow]No models found. Pull a model first:[/yellow]")
                console.print("  ollama pull llama3.2:3b")
        else:
            console.print("[red]✗[/red] Ollama service is not available")
            console.print("\n[yellow]Please ensure Ollama is running:[/yellow]")
            console.print("  ollama serve")
            sys.exit(1)


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output directory (default: from config)",
)
@click.option(
    "-c",
    "--categories",
    help="Comma-separated list of categories (default: from config)",
)
@click.option(
    "--copy",
    is_flag=True,
    help="Copy files instead of moving them",
)
@click.option(
    "--reasoning",
    is_flag=True,
    help="Include AI reasoning in classification",
)
@click.option(
    "--no-organize",
    is_flag=True,
    help="Only classify, don't organize files",
)
@click.option(
    "--export",
    type=click.Path(),
    help="Export results to JSON file",
)
@click.option(
    "--split",
    type=click.Choice(["none", "pages", "sections", "chunks", "smart"]),
    help="Split documents into sections (default: none)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def classify(
    input_path: str,
    output: Optional[str],
    categories: Optional[str],
    copy: bool,
    reasoning: bool,
    no_organize: bool,
    export: Optional[str],
    split: Optional[str],
    verbose: bool,
):
    """Classify and organize documents.

    INPUT_PATH can be a single file or directory.
    """
    setup_logging(verbose)

    console.print(Panel.fit(
        "AI Document Classification Pipeline",
        subtitle="Powered by Ollama",
        style="bold blue",
    ))

    # Setup
    input_path_obj = Path(input_path)
    settings.ensure_directories()

    if output:
        settings.output_folder = Path(output)
        settings.output_folder.mkdir(parents=True, exist_ok=True)

    if categories:
        settings.categories = categories

    # Set split mode
    if split:
        settings.split_documents = split

    # Check Ollama
    ollama = OllamaService()
    if not ollama.is_available():
        console.print("[red]Error:[/red] Ollama service not available")
        console.print("Please start Ollama: [cyan]ollama serve[/cyan]")
        sys.exit(1)

    console.print(f"[green]✓[/green] Using model: {ollama.model}")
    console.print(f"[green]✓[/green] Categories: {', '.join(settings.category_list)}")
    if settings.split_documents != "none":
        console.print(f"[green]✓[/green] Split mode: {settings.split_documents}")
    console.print()

    # Classify
    classifier = DocumentClassifier(ollama_service=ollama)

    try:
        if input_path_obj.is_file():
            console.print(f"Classifying file: [cyan]{input_path_obj.name}[/cyan]")
            result = classifier.classify_document(input_path_obj, include_reasoning=reasoning)
            results = [result] if result else []
        else:
            console.print(f"Classifying directory: [cyan]{input_path_obj}[/cyan]\n")
            results = classifier.classify_directory(
                input_path_obj,
                recursive=settings.process_subdirectories,
                include_reasoning=reasoning,
            )

        if not results:
            console.print("[yellow]No documents were classified[/yellow]")
            sys.exit(0)

        # Display results
        console.print(f"\n[green]Successfully classified {len(results)} documents[/green]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan")
        table.add_column("Category", style="green")
        if reasoning:
            table.add_column("Reasoning", style="yellow")

        for result in results:
            if reasoning and result.confidence:
                table.add_row(result.file_path.name, result.category, result.confidence)
            else:
                table.add_row(result.file_path.name, result.category)

        console.print(table)

        # Show distribution
        distribution = classifier.get_category_distribution()
        console.print("\n[bold]Category Distribution:[/bold]")
        for category, count in distribution.items():
            if count > 0:
                console.print(f"  • {category}: {count}")

        # Export results
        if export:
            export_path = Path(export)
            classifier.export_results(export_path)
            console.print(f"\n[green]✓[/green] Results exported to: {export_path}")

        # Organize files
        if not no_organize:
            console.print(f"\n[bold]Organizing files into: {settings.output_folder}[/bold]")
            organizer = DocumentOrganizer(output_dir=settings.output_folder)
            summary = organizer.organize(results, copy_files=copy, create_manifest=True)

            console.print(f"\n[green]✓[/green] Organization complete!")
            console.print(f"  • {summary['successful']} files {summary['operation']}")
            if summary['failed'] > 0:
                console.print(f"  • {summary['failed']} files failed")
            console.print(f"  • Manifest created: {settings.output_folder / 'organization_manifest.json'}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.option(
    "--categories",
    help="Comma-separated list of categories",
)
def init(categories: Optional[str]):
    """Initialize the document pipeline structure."""
    console.print(Panel.fit("Initializing Document Pipeline", style="bold blue"))

    if categories:
        settings.categories = categories

    settings.ensure_directories()

    console.print("[green]✓[/green] Created input directory: ", settings.input_folder)
    console.print("[green]✓[/green] Created output directory: ", settings.output_folder)
    console.print("[green]✓[/green] Created temp directory: ", settings.temp_folder)
    console.print("\n[bold]Category folders created:[/bold]")

    for category in settings.category_list:
        console.print(f"  • {settings.output_folder / category}")

    console.print(f"\n[cyan]Place documents to classify in:[/cyan] {settings.input_folder}")
    console.print(f"[cyan]Classified documents will be organized in:[/cyan] {settings.output_folder}")


@cli.command()
def config():
    """Show current configuration."""
    console.print(Panel.fit("Current Configuration", style="bold blue"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Ollama Host", settings.ollama_host)
    table.add_row("Ollama Model", settings.ollama_model)
    table.add_row("Input Folder", str(settings.input_folder))
    table.add_row("Output Folder", str(settings.output_folder))
    table.add_row("Temp Folder", str(settings.temp_folder))
    table.add_row("Categories", ", ".join(settings.category_list))
    table.add_row("Max File Size", f"{settings.max_file_size_mb} MB")
    table.add_row("Process Subdirectories", str(settings.process_subdirectories))
    table.add_row("Database Enabled", str(settings.use_database))
    if settings.use_database:
        table.add_row("Database URL", settings.database_url)

    console.print(table)

    console.print("\n[cyan]To modify settings:[/cyan]")
    console.print("  1. Copy .env.example to .env")
    console.print("  2. Edit .env with your preferences")


@cli.command()
@click.argument("results_file", type=click.Path(exists=True))
@click.option(
    "--output",
    type=click.Path(),
    default="training_data.jsonl",
    help="Output file for training data",
)
def review(results_file: str, output: str):
    """Review and correct classifications to build training data.

    Allows you to review classification results and provide corrections,
    building a dataset for model improvement.
    """
    setup_logging(False)

    console.print(Panel.fit(
        "Classification Review & Training Data Collection",
        style="bold blue",
    ))

    collector = TrainingDataCollector(output_file=Path(output))

    # Load results
    import json
    with open(results_file) as f:
        data = json.load(f)

    results = data.get("results", [])

    if not results:
        console.print("[yellow]No results found in file[/yellow]")
        return

    console.print(f"\n[cyan]Reviewing {len(results)} classifications[/cyan]")
    console.print("[dim]Press Ctrl+C to stop at any time[/dim]\n")

    corrected = 0
    confirmed = 0

    try:
        for i, result in enumerate(results, 1):
            console.print(f"\n[bold]Document {i}/{len(results)}[/bold]")
            console.print(f"  File: [cyan]{result['file_name']}[/cyan]")
            console.print(f"  Predicted: [yellow]{result['category']}[/yellow]")

            if result.get("confidence"):
                console.print(f"  Reasoning: [dim]{result['confidence']}[/dim]")

            correct = click.prompt(
                "\n  Correct category (or press Enter if correct)",
                default=result["category"],
                show_default=False,
            )

            if correct != result["category"]:
                corrected += 1
                console.print(f"  [green]✓[/green] Corrected to: {correct}")
            else:
                confirmed += 1
                console.print(f"  [green]✓[/green] Confirmed")

            # Record for training
            collector.record_classification(
                content=result.get("content", ""),
                predicted_category=result["category"],
                correct_category=correct,
                metadata=result.get("metadata", {}),
                confidence=result.get("confidence"),
            )

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Review stopped by user[/yellow]")

    # Show summary
    console.print(f"\n[bold]Review Summary:[/bold]")
    console.print(f"  Confirmed: {confirmed}")
    console.print(f"  Corrected: {corrected}")
    console.print(f"  Total: {confirmed + corrected}")

    # Show training data stats
    stats = collector.get_statistics()
    console.print(f"\n[bold]Training Data:[/bold]")
    console.print(f"  Total examples: {stats.get('total_examples', 0)}")
    console.print(f"  Accuracy: {stats.get('overall_accuracy', 0):.2%}")
    console.print(f"  Saved to: [cyan]{output}[/cyan]")


@cli.command()
@click.argument("test_dir", type=click.Path(exists=True))
@click.option(
    "--model",
    help="Model to evaluate (default: from config)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
def evaluate(test_dir: str, model: Optional[str], verbose: bool):
    """Evaluate classification accuracy on labeled test data.

    TEST_DIR should contain subdirectories named after categories,
    with test documents inside:

        test_data/
        ├── invoices/
        │   ├── invoice1.pdf
        │   └── invoice2.pdf
        ├── contracts/
        │   └── contract1.docx
        └── reports/
            └── report1.xlsx
    """
    setup_logging(verbose)

    console.print(Panel.fit("Model Evaluation", style="bold blue"))

    # Check Ollama
    ollama = OllamaService(model=model) if model else OllamaService()

    if not ollama.is_available():
        console.print("[red]Error:[/red] Ollama service not available")
        sys.exit(1)

    console.print(f"[green]✓[/green] Evaluating model: {ollama.model}\n")

    # Load test data
    test_dir_path = Path(test_dir)
    test_data = {}

    for category_dir in test_dir_path.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            files = list(category_dir.glob("*.*"))
            if files:
                test_data[category] = files

    if not test_data:
        console.print("[red]Error:[/red] No test data found")
        console.print("\nExpected structure:")
        console.print("  test_dir/")
        console.print("  ├── category1/")
        console.print("  │   └── documents...")
        console.print("  └── category2/")
        console.print("      └── documents...")
        sys.exit(1)

    console.print(f"[cyan]Found test data:[/cyan]")
    for category, files in test_data.items():
        console.print(f"  • {category}: {len(files)} documents")

    # Evaluate
    classifier = DocumentClassifier(ollama_service=ollama)
    evaluator = ClassificationEvaluator(classifier)

    console.print(f"\n[cyan]Running evaluation...[/cyan]\n")

    results = evaluator.evaluate(test_data, verbose=True)

    # Save results
    output_file = Path("evaluation_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[green]✓[/green] Results saved to: {output_file}")


@cli.command()
@click.option(
    "--training-data",
    type=click.Path(exists=True),
    default="training_data.jsonl",
    help="Training data file",
)
@click.option(
    "--output",
    type=click.Path(),
    default="examples.json",
    help="Output file for examples",
)
@click.option(
    "--max-per-category",
    type=int,
    default=10,
    help="Maximum examples per category",
)
def export_examples(training_data: str, output: str, max_per_category: int):
    """Export training data as few-shot examples.

    Extracts the best examples from training data for use in few-shot learning.
    """
    console.print(Panel.fit("Export Few-Shot Examples", style="bold blue"))

    collector = TrainingDataCollector(output_file=Path(training_data))

    if not Path(training_data).exists():
        console.print(f"[red]Error:[/red] Training data not found: {training_data}")
        sys.exit(1)

    # Get statistics
    stats = collector.get_statistics()
    console.print(f"\n[cyan]Training Data Statistics:[/cyan]")
    console.print(f"  Total examples: {stats.get('total_examples', 0)}")
    console.print(f"  Overall accuracy: {stats.get('overall_accuracy', 0):.2%}")

    # Export examples
    examples = collector.get_examples_by_category(
        min_confidence=True, max_per_category=max_per_category
    )

    if not examples:
        console.print("\n[yellow]No examples found to export[/yellow]")
        sys.exit(0)

    # Save
    output_path = Path(output)
    with open(output_path, "w") as f:
        json.dump(examples, f, indent=2)

    console.print(f"\n[green]✓[/green] Exported examples to: {output_path}")
    console.print(f"\n[cyan]Examples by category:[/cyan]")
    for category, example_list in examples.items():
        console.print(f"  • {category}: {len(example_list)} examples")


@cli.command()
@click.option(
    "--examples",
    type=click.Path(exists=True),
    required=True,
    help="Examples JSON file",
)
@click.option(
    "--base-model",
    default="llama3.2:3b",
    help="Base model to use",
)
@click.option(
    "--output",
    type=click.Path(),
    default="Modelfile",
    help="Output Modelfile path",
)
@click.option(
    "--model-name",
    default="doc-classifier",
    help="Name for the custom model",
)
def create_model(examples: str, base_model: str, output: str, model_name: str):
    """Create a custom Ollama model from training examples.

    This generates a Modelfile and provides instructions for creating
    a custom fine-tuned model using Ollama.
    """
    console.print(Panel.fit("Create Custom Model", style="bold blue"))

    # Load examples
    with open(examples) as f:
        example_data = json.load(f)

    console.print(f"\n[cyan]Loaded examples:[/cyan]")
    total = 0
    for category, example_list in example_data.items():
        count = len(example_list)
        total += count
        console.print(f"  • {category}: {count} examples")

    console.print(f"\n[bold]Total examples: {total}[/bold]")

    if total < 10:
        console.print(
            "\n[yellow]Warning:[/yellow] Less than 10 examples total. "
            "Model may not train well."
        )
        console.print("Consider collecting more training data with: doc-classify review")

    # Generate Modelfile
    output_path = Path(output)
    generate_modelfile(
        base_model=base_model,
        examples=example_data,
        output_file=output_path,
        system_message=f"You are an expert document classifier trained on {total} examples.",
    )

    console.print(f"\n[green]✓[/green] Generated Modelfile: {output_path}")

    console.print(f"\n[bold]Next steps:[/bold]")
    console.print(f"  1. Review the Modelfile: [cyan]cat {output_path}[/cyan]")
    console.print(
        f"  2. Create the model: [cyan]ollama create {model_name} -f {output_path}[/cyan]"
    )
    console.print(f"  3. Test the model: [cyan]ollama run {model_name}[/cyan]")
    console.print(
        f"  4. Update .env: [cyan]OLLAMA_MODEL={model_name}[/cyan]"
    )


@cli.command()
@click.option(
    "--search",
    help="Search query for documents",
)
@click.option(
    "--category",
    help="Filter by category",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum results to show",
)
def db_search(search: Optional[str], category: Optional[str], limit: int):
    """Search documents in the database.

    Requires database to be enabled in configuration.
    """
    if not settings.use_database:
        console.print("[red]Error:[/red] Database not enabled")
        console.print("Enable in .env: USE_DATABASE=true")
        sys.exit(1)

    if not DATABASE_AVAILABLE:
        console.print("[red]Error:[/red] SQLAlchemy not installed")
        console.print("Install with: pip install sqlalchemy")
        sys.exit(1)

    console.print(Panel.fit("Database Search", style="bold blue"))

    try:
        db = DatabaseService(database_url=settings.database_url)

        if search:
            console.print(f"\n[cyan]Searching for:[/cyan] {search}")
            results = db.search_documents(search, category=category, limit=limit)
        elif category:
            console.print(f"\n[cyan]Category:[/cyan] {category}")
            results = db.get_documents_by_category(category, limit=limit)
        else:
            console.print("[yellow]Please provide --search or --category[/yellow]")
            return

        if not results:
            console.print("\n[yellow]No documents found[/yellow]")
            return

        # Display results
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("File", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("Date", style="dim")

        for doc in results:
            table.add_row(
                str(doc["id"]),
                doc["file_name"],
                doc["category"],
                doc.get("processed_date", "N/A")[:10] if doc.get("processed_date") else "N/A"
            )

        console.print(f"\n[bold]Found {len(results)} documents:[/bold]\n")
        console.print(table)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
def db_stats():
    """Show database statistics.

    Requires database to be enabled in configuration.
    """
    if not settings.use_database:
        console.print("[red]Error:[/red] Database not enabled")
        console.print("Enable in .env: USE_DATABASE=true")
        sys.exit(1)

    if not DATABASE_AVAILABLE:
        console.print("[red]Error:[/red] SQLAlchemy not installed")
        console.print("Install with: pip install sqlalchemy")
        sys.exit(1)

    console.print(Panel.fit("Database Statistics", style="bold blue"))

    try:
        db = DatabaseService(database_url=settings.database_url)
        stats = db.get_statistics()

        console.print(f"\n[bold]Total Documents:[/bold] {stats['total_documents']}")
        console.print(f"[bold]Processed Today:[/bold] {stats['processed_today']}")
        console.print(f"[bold]Organized:[/bold] {stats['organized']}")
        console.print(f"[bold]Unorganized:[/bold] {stats['unorganized']}")

        console.print(f"\n[bold]By Category:[/bold]")
        for category, count in stats['by_category'].items():
            console.print(f"  • {category}: {count}")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    type=click.Path(),
    default="database_export.json",
    help="Output file path",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of records (default: all)",
)
def db_export(output: str, limit: Optional[int]):
    """Export database to JSON file.

    Requires database to be enabled in configuration.
    """
    if not settings.use_database:
        console.print("[red]Error:[/red] Database not enabled")
        console.print("Enable in .env: USE_DATABASE=true")
        sys.exit(1)

    if not DATABASE_AVAILABLE:
        console.print("[red]Error:[/red] SQLAlchemy not installed")
        console.print("Install with: pip install sqlalchemy")
        sys.exit(1)

    console.print(Panel.fit("Database Export", style="bold blue"))

    try:
        db = DatabaseService(database_url=settings.database_url)
        db.export_to_json(Path(output), limit=limit)

        console.print(f"\n[green]✓[/green] Exported to: {output}")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option(
    "--mode",
    type=click.Choice(["keyword", "semantic", "hybrid"]),
    default="hybrid",
    help="Search mode (default: hybrid)",
)
@click.option(
    "--category",
    help="Filter by category",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of results (default: 20)",
)
@click.option(
    "--keyword-weight",
    type=float,
    default=0.6,
    help="Keyword weight for hybrid search (default: 0.6)",
)
@click.option(
    "--semantic-weight",
    type=float,
    default=0.4,
    help="Semantic weight for hybrid search (default: 0.4)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
def search(
    query: str,
    mode: str,
    category: Optional[str],
    limit: int,
    keyword_weight: float,
    semantic_weight: float,
    verbose: bool
):
    """Search documents using keyword, semantic, or hybrid search.

    Examples:

        \b
        # Hybrid search (best of both worlds)
        doc-classify search "contract amendment"

        \b
        # Keyword search (fast, exact matches)
        doc-classify search "invoice #12345" --mode keyword

        \b
        # Semantic search (finds similar concepts)
        doc-classify search "how to cancel subscription" --mode semantic

        \b
        # Filter by category
        doc-classify search "Q3 results" --category reports

        \b
        # Adjust hybrid weights
        doc-classify search "payment terms" --keyword-weight 0.8 --semantic-weight 0.2
    """
    setup_logging(verbose)

    try:
        from src.search_service import SearchService, SearchMode

        console.print(Panel.fit(f"Document Search: {mode.upper()}", style="bold blue"))
        console.print(f"[blue]Query:[/blue] {query}")
        if category:
            console.print(f"[blue]Category:[/blue] {category}")

        # Initialize search service
        search_service = SearchService(
            database_url=settings.database_url,
            embedding_provider=getattr(settings, "embedding_provider", "ollama")
        )

        # Test connection
        if not search_service.test_connection():
            console.print("\n[red]Error:[/red] Could not connect to database")
            console.print("[yellow]Make sure PostgreSQL is running:[/yellow]")
            console.print("  docker-compose up -d")
            sys.exit(1)

        # Perform search
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description=f"Searching...", total=None)

            results = search_service.search(
                query=query,
                mode=SearchMode(mode),
                category=category,
                limit=limit,
                keyword_weight=keyword_weight,
                semantic_weight=semantic_weight
            )

        # Display results
        if not results:
            console.print("\n[yellow]No results found[/yellow]")
            return

        console.print(f"\n[green]Found {len(results)} results[/green]\n")

        # Create results table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("File Name", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("Title", style="blue")

        if mode == "hybrid":
            table.add_column("Score", justify="right", style="magenta")
        elif mode == "keyword":
            table.add_column("Rank", justify="right", style="magenta")
        else:
            table.add_column("Similarity", justify="right", style="magenta")

        for i, result in enumerate(results, 1):
            score = result.combined_score
            if mode == "keyword":
                score = result.keyword_rank
            elif mode == "semantic":
                score = result.semantic_rank

            table.add_row(
                str(i),
                result.file_name,
                result.category,
                result.title or "-",
                f"{score:.4f}"
            )

        console.print(table)

        # Show previews if verbose
        if verbose:
            console.print("\n[bold]Preview of top 3 results:[/bold]\n")
            for i, result in enumerate(results[:3], 1):
                console.print(f"[cyan]{i}. {result.file_name}[/cyan]")
                preview = result.content_preview[:200]
                console.print(f"   {preview}...\n")

    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing dependencies: {e}")
        console.print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option(
    "--include-vectors",
    is_flag=True,
    help="Generate embeddings for semantic search",
)
@click.option(
    "--category",
    help="Only reindex documents in this category",
)
@click.option(
    "--batch-size",
    type=int,
    default=10,
    help="Number of documents to process at once (default: 10)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
def reindex(include_vectors: bool, category: Optional[str], batch_size: int, verbose: bool):
    """Reindex documents for search.

    This updates the full-text search and optionally generates
    embeddings for semantic search.

    Examples:

        \b
        # Reindex FTS only (fast)
        doc-classify reindex

        \b
        # Reindex with embeddings (slower but enables semantic search)
        doc-classify reindex --include-vectors

        \b
        # Reindex specific category
        doc-classify reindex --category invoices --include-vectors
    """
    setup_logging(verbose)

    try:
        from src.search_service import SearchService
        import sqlalchemy as sa
        from sqlalchemy import text

        console.print(Panel.fit("Reindex Documents", style="bold blue"))

        # Initialize search service
        search_service = SearchService(
            database_url=settings.database_url,
            embedding_provider=getattr(settings, "embedding_provider", "ollama")
        )

        # Test connection
        if not search_service.test_connection():
            console.print("\n[red]Error:[/red] Could not connect to database")
            console.print("[yellow]Make sure PostgreSQL is running:[/yellow]")
            console.print("  docker-compose up -d")
            sys.exit(1)

        # Get documents to reindex
        with search_service.engine.connect() as conn:
            sql = "SELECT id, full_content FROM documents WHERE full_content IS NOT NULL"
            params = {}

            if category:
                sql += " AND category = :category"
                params["category"] = category

            result = conn.execute(text(sql), params)
            documents = result.fetchall()

        if not documents:
            console.print("\n[yellow]No documents found to reindex[/yellow]")
            return

        console.print(f"\n[blue]Documents to reindex:[/blue] {len(documents)}")
        console.print(f"[blue]Include embeddings:[/blue] {'Yes' if include_vectors else 'No'}")

        # Reindex
        success_count = 0
        error_count = 0

        with Progress(console=console) as progress:
            task = progress.add_task(
                "[cyan]Reindexing...",
                total=len(documents)
            )

            for doc_id, content in documents:
                try:
                    if search_service.reindex_document(
                        doc_id,
                        content or "",
                        generate_embedding=include_vectors
                    ):
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error reindexing document {doc_id}: {e}")
                    error_count += 1

                progress.update(task, advance=1)

        # Show results
        console.print(f"\n[green]✓[/green] Reindexed: {success_count} documents")
        if error_count > 0:
            console.print(f"[yellow]![/yellow] Errors: {error_count} documents")

        # Show statistics
        stats = search_service.get_statistics()
        if stats:
            console.print(f"\n[bold]Index Statistics:[/bold]")
            console.print(f"  FTS Coverage: {stats.get('fts_coverage', '0%')}")
            console.print(f"  Embedding Coverage: {stats.get('embedding_coverage', '0%')}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
def search_stats(verbose: bool):
    """Show search index statistics.

    Displays information about indexed documents,
    FTS coverage, and embedding coverage.
    """
    setup_logging(verbose)

    try:
        from src.search_service import SearchService

        console.print(Panel.fit("Search Statistics", style="bold blue"))

        # Initialize search service
        search_service = SearchService(
            database_url=settings.database_url,
            embedding_provider=getattr(settings, "embedding_provider", "ollama")
        )

        # Test connection
        if not search_service.test_connection():
            console.print("\n[red]Error:[/red] Could not connect to database")
            sys.exit(1)

        # Get statistics
        stats = search_service.get_statistics()

        if not stats:
            console.print("\n[yellow]No statistics available[/yellow]")
            return

        # Display statistics
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="blue")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Documents", str(stats.get("total_documents", 0)))
        table.add_row("Total Categories", str(stats.get("total_categories", 0)))
        table.add_row("Documents with FTS", str(stats.get("documents_with_fts", 0)))
        table.add_row("Documents with Embeddings", str(stats.get("documents_with_embeddings", 0)))
        table.add_row("FTS Coverage", stats.get("fts_coverage", "0%"))
        table.add_row("Embedding Coverage", stats.get("embedding_coverage", "0%"))

        avg_size = stats.get("avg_file_size_bytes", 0)
        total_size = stats.get("total_storage_bytes", 0)

        table.add_row("Average File Size", f"{avg_size:,} bytes")
        table.add_row("Total Storage", f"{total_size:,} bytes")

        console.print("\n")
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output directory for results export",
)
@click.option(
    "-c",
    "--categories",
    help="Comma-separated list of categories (default: from config)",
)
@click.option(
    "-w",
    "--workers",
    type=int,
    help="Number of worker processes (default: CPU count)",
)
@click.option(
    "--chunk-size",
    type=int,
    default=10,
    help="Number of documents per worker chunk (default: 10)",
)
@click.option(
    "--reasoning",
    is_flag=True,
    help="Include AI reasoning in classification",
)
@click.option(
    "--use-database",
    is_flag=True,
    help="Store results in database",
)
@click.option(
    "--export",
    is_flag=True,
    help="Export results to JSON file",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def classify_parallel(
    input_path: str,
    output: Optional[str],
    categories: Optional[str],
    workers: Optional[int],
    chunk_size: int,
    reasoning: bool,
    use_database: bool,
    export: bool,
    verbose: bool,
):
    """Classify documents using parallel processing (HIGH THROUGHPUT).

    This command uses multiprocessing to classify documents across multiple CPU cores,
    providing 5-10x faster performance than the standard classify command.

    Ideal for processing large batches (1000+ documents).

    Examples:

      # Process entire directory with all CPU cores
      doc-classify classify-parallel documents/input

      # Use specific number of workers
      doc-classify classify-parallel documents/input -w 8

      # Export results and store in database
      doc-classify classify-parallel documents/input --export --use-database -o results/
    """
    from src.parallel_processor import ParallelDocumentProcessor

    setup_logging(verbose)

    console.print(Panel.fit("Parallel Document Classification", style="bold magenta"))

    input_path_obj = Path(input_path)
    output_dir = Path(output) if output else Path("./parallel_results")

    # Parse categories if provided
    category_list = None
    if categories:
        category_list = [cat.strip() for cat in categories.split(",")]
        console.print(f"[blue]Categories:[/blue] {', '.join(category_list)}")
    else:
        category_list = settings.category_list
        console.print(f"[blue]Categories:[/blue] {', '.join(category_list)} (from config)")

    # Display configuration
    worker_count = workers if workers else None
    console.print(f"[blue]Workers:[/blue] {worker_count or 'auto (CPU count)'}")
    console.print(f"[blue]Chunk size:[/blue] {chunk_size}")
    console.print(f"[blue]Database:[/blue] {'enabled' if use_database else 'disabled'}")
    console.print(f"[blue]Export:[/blue] {'enabled' if export else 'disabled'}")
    console.print()

    try:
        # Create processor
        processor = ParallelDocumentProcessor(
            categories=category_list,
            num_workers=worker_count,
            use_database=use_database,
            chunk_size=chunk_size,
        )

        # Process documents
        if input_path_obj.is_file():
            console.print(f"[yellow]Processing single file:[/yellow] {input_path_obj.name}")
            stats = processor.process_batch(
                [input_path_obj],
                include_reasoning=reasoning,
                show_progress=True
            )
        else:
            console.print(f"[yellow]Processing directory:[/yellow] {input_path_obj}")
            stats = processor.process_directory(
                input_path_obj,
                recursive=True,
                include_reasoning=reasoning
            )

        # Print summary
        processor.print_summary()

        # Export results if requested
        if export:
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = output_dir / f"parallel_results_{timestamp}.json"
            processor.export_results(results_file)
            console.print(f"\n[green]✓[/green] Results exported to: {results_file}")

        # Show performance estimate for 500K documents
        if stats.documents_per_second > 0:
            hours_for_500k = 500000 / stats.documents_per_second / 3600
            console.print(
                f"\n[cyan]Performance Projection:[/cyan] "
                f"500,000 documents would take ~{hours_for_500k:.1f} hours "
                f"({hours_for_500k/24:.1f} days)"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
