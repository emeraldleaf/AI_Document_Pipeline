#!/usr/bin/env python3
"""
Test and compare embedding models: nomic-embed-text vs mxbai-embed-large

This script:
1. Tests context length limits for both models
2. Compares embedding quality and dimensions
3. Measures performance (speed)
4. Helps decide which model to use for production
"""

import requests
import time
from rich.console import Console
from rich.table import Table

console = Console()

OLLAMA_HOST = "http://localhost:11434"

def test_embedding(model: str, text: str, description: str = ""):
    """Test embedding generation for a given text"""
    try:
        start_time = time.time()
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            embedding = data.get("embedding", [])
            return {
                "success": True,
                "dimension": len(embedding),
                "time": elapsed,
                "text_length": len(text),
                "description": description
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "text_length": len(text),
                "description": description
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text_length": len(text),
            "description": description
        }

def find_context_limit(model: str, start_chars: int = 500, max_chars: int = 10000, step: int = 500):
    """Binary search to find the maximum context length"""
    console.print(f"\n[bold cyan]Finding context limit for {model}...[/bold cyan]")

    test_text_base = "This is a test document for measuring embedding context limits. " * 100

    # Test incrementally
    for length in range(start_chars, max_chars + 1, step):
        text = test_text_base[:length]
        result = test_embedding(model, text, f"{length} chars")

        if result["success"]:
            console.print(f"  ✓ {length:,} chars: [green]SUCCESS[/green] ({result['dimension']} dims, {result['time']:.2f}s)")
        else:
            console.print(f"  ✗ {length:,} chars: [red]FAILED[/red] - {result.get('error', 'Unknown error')}")
            return length - step  # Return last successful length

    return max_chars

def compare_models():
    """Compare nomic-embed-text and mxbai-embed-large"""
    console.print("\n[bold magenta]═══ Embedding Model Comparison ═══[/bold magenta]\n")

    models = ["nomic-embed-text", "mxbai-embed-large"]

    # Test 1: Short text (100 chars)
    console.print("[bold yellow]Test 1: Short Text (100 characters)[/bold yellow]")
    short_text = "This is a short test document for semantic search embedding. " * 2
    short_text = short_text[:100]

    short_results = {}
    for model in models:
        result = test_embedding(model, short_text, "Short text")
        short_results[model] = result
        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
        time_str = f"{result.get('time', 0):.3f}s" if result["success"] else "N/A"
        dim_str = str(result.get('dimension', 'N/A'))
        console.print(f"  {status} {model}: {dim_str} dims, {time_str}")

    # Test 2: Medium text (1000 chars)
    console.print("\n[bold yellow]Test 2: Medium Text (1000 characters)[/bold yellow]")
    medium_text = "This is a medium-length document for testing semantic search embeddings with more context. " * 20
    medium_text = medium_text[:1000]

    medium_results = {}
    for model in models:
        result = test_embedding(model, medium_text, "Medium text")
        medium_results[model] = result
        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
        time_str = f"{result.get('time', 0):.3f}s" if result["success"] else "N/A"
        dim_str = str(result.get('dimension', 'N/A'))
        console.print(f"  {status} {model}: {dim_str} dims, {time_str}")

    # Test 3: Large text (3000 chars) - exceeds nomic-embed-text limit
    console.print("\n[bold yellow]Test 3: Large Text (3000 characters)[/bold yellow]")
    large_text = "This is a large document that exceeds the nomic-embed-text context limit. " * 50
    large_text = large_text[:3000]

    large_results = {}
    for model in models:
        result = test_embedding(model, large_text, "Large text")
        large_results[model] = result
        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
        time_str = f"{result.get('time', 0):.3f}s" if result["success"] else "N/A"
        dim_str = str(result.get('dimension', 'N/A'))
        console.print(f"  {status} {model}: {dim_str} dims, {time_str}")

    # Test 4: Very large text (8000 chars)
    console.print("\n[bold yellow]Test 4: Very Large Text (8000 characters)[/bold yellow]")
    very_large_text = "This is a very large document to test maximum context length. " * 150
    very_large_text = very_large_text[:8000]

    very_large_results = {}
    for model in models:
        result = test_embedding(model, very_large_text, "Very large text")
        very_large_results[model] = result
        status = "[green]✓[/green]" if result["success"] else "[red]✗[/red]"
        time_str = f"{result.get('time', 0):.3f}s" if result["success"] else "N/A"
        dim_str = str(result.get('dimension', 'N/A'))
        console.print(f"  {status} {model}: {dim_str} dims, {time_str}")

    # Find exact context limits
    console.print("\n[bold yellow]Finding Exact Context Limits...[/bold yellow]")
    limits = {}
    for model in models:
        limit = find_context_limit(model, start_chars=1000, max_chars=10000, step=500)
        limits[model] = limit
        console.print(f"  {model}: [cyan]{limit:,} characters[/cyan]")

    # Summary table
    console.print("\n[bold magenta]═══ Summary ═══[/bold magenta]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model", style="yellow")
    table.add_column("Dimensions", justify="right")
    table.add_column("Context Limit", justify="right")
    table.add_column("Avg Speed (100 chars)", justify="right")
    table.add_column("Status", justify="center")

    for model in models:
        dim = short_results[model].get('dimension', 'N/A')
        limit = f"{limits[model]:,} chars" if model in limits else "N/A"
        speed = f"{short_results[model].get('time', 0):.3f}s" if short_results[model]['success'] else "N/A"
        status = "[green]✓ Working[/green]" if short_results[model]['success'] else "[red]✗ Failed[/red]"

        table.add_row(
            model,
            str(dim),
            limit,
            speed,
            status
        )

    console.print(table)

    # Recommendation
    console.print("\n[bold magenta]═══ Recommendation ═══[/bold magenta]\n")

    if limits.get("mxbai-embed-large", 0) > limits.get("nomic-embed-text", 0):
        console.print("[bold green]✓ RECOMMENDED: mxbai-embed-large[/bold green]")
        console.print(f"  - Higher context limit: {limits.get('mxbai-embed-large', 0):,} chars vs {limits.get('nomic-embed-text', 0):,} chars")
        console.print(f"  - Embedding dimension: {medium_results.get('mxbai-embed-large', {}).get('dimension', 'N/A')}")
        console.print("  - Better for handling larger documents without chunking")

        nomic_limit = limits.get('nomic-embed-text', 0)
        mxbai_limit = limits.get('mxbai-embed-large', 0)
        if mxbai_limit > 3000:
            console.print(f"\n[yellow]Note:[/yellow] With mxbai-embed-large's {mxbai_limit:,} char limit,")
            console.print("you may still benefit from chunking for very large documents (>8000 chars)")
            console.print("but will need chunking for far fewer documents than with nomic-embed-text.")
    else:
        console.print("[bold yellow]⚠ Both models have similar limits[/bold yellow]")
        console.print("Consider using chunking for both to ensure reliability.")

if __name__ == "__main__":
    try:
        compare_models()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]Error: {e}[/red]")
