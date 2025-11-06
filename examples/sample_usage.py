"""Example usage of the AI Document Classification Pipeline."""

from pathlib import Path
from src.classifier import DocumentClassifier, DocumentOrganizer
from src.ollama_service import OllamaService
from config import settings
from loguru import logger


def example_1_single_document():
    """Example: Classify a single document."""
    print("\n" + "="*60)
    print("Example 1: Classify a Single Document")
    print("="*60)

    # Initialize services
    ollama = OllamaService()

    # Check if Ollama is available
    if not ollama.is_available():
        print("Error: Ollama service is not available. Please start it with: ollama serve")
        return

    classifier = DocumentClassifier(ollama_service=ollama)

    # Classify a document
    doc_path = Path("path/to/your/document.pdf")
    if doc_path.exists():
        result = classifier.classify_document(doc_path, include_reasoning=True)

        if result:
            print(f"\nFile: {result.file_path.name}")
            print(f"Category: {result.category}")
            print(f"Reasoning: {result.confidence}")
    else:
        print(f"Document not found: {doc_path}")


def example_2_batch_classification():
    """Example: Classify multiple documents."""
    print("\n" + "="*60)
    print("Example 2: Batch Classification")
    print("="*60)

    ollama = OllamaService()
    if not ollama.is_available():
        print("Error: Ollama service not available")
        return

    classifier = DocumentClassifier(ollama_service=ollama)

    # List of documents to classify
    documents = [
        Path("documents/invoice.pdf"),
        Path("documents/contract.docx"),
        Path("documents/report.xlsx"),
    ]

    # Filter existing files
    existing_docs = [doc for doc in documents if doc.exists()]

    if existing_docs:
        # Classify batch
        results = classifier.classify_batch(
            file_paths=existing_docs,
            include_reasoning=True,
            show_progress=True
        )

        # Display results
        print(f"\nClassified {len(results)} documents:")
        for result in results:
            print(f"  • {result.file_path.name} → {result.category}")

        # Show distribution
        distribution = classifier.get_category_distribution()
        print("\nCategory Distribution:")
        for category, count in distribution.items():
            if count > 0:
                print(f"  • {category}: {count}")
    else:
        print("No documents found to classify")


def example_3_directory_classification():
    """Example: Classify all documents in a directory."""
    print("\n" + "="*60)
    print("Example 3: Directory Classification")
    print("="*60)

    ollama = OllamaService()
    if not ollama.is_available():
        print("Error: Ollama service not available")
        return

    classifier = DocumentClassifier(ollama_service=ollama)

    # Classify directory
    input_dir = Path("documents/input")

    if input_dir.exists():
        results = classifier.classify_directory(
            input_dir=input_dir,
            recursive=True,
            include_reasoning=False
        )

        print(f"\nClassified {len(results)} documents")

        # Export results
        output_file = Path("classification_results.json")
        classifier.export_results(output_file)
        print(f"Results exported to: {output_file}")
    else:
        print(f"Directory not found: {input_dir}")


def example_4_classify_and_organize():
    """Example: Classify documents and organize into folders."""
    print("\n" + "="*60)
    print("Example 4: Classify and Auto-Organize")
    print("="*60)

    # Setup
    settings.ensure_directories()

    ollama = OllamaService()
    if not ollama.is_available():
        print("Error: Ollama service not available")
        return

    classifier = DocumentClassifier(ollama_service=ollama)

    # Classify
    input_dir = settings.input_folder
    if not input_dir.exists() or not list(input_dir.iterdir()):
        print(f"No documents found in: {input_dir}")
        return

    print(f"Classifying documents in: {input_dir}")
    results = classifier.classify_directory(
        input_dir=input_dir,
        recursive=True,
        include_reasoning=True
    )

    if not results:
        print("No documents were classified")
        return

    # Organize
    print(f"\nOrganizing {len(results)} documents...")
    organizer = DocumentOrganizer(output_dir=settings.output_folder)

    summary = organizer.organize(
        results=results,
        copy_files=True,  # Use True to keep originals
        create_manifest=True
    )

    print(f"\n✓ Organization complete!")
    print(f"  • {summary['successful']} files {summary['operation']}")
    print(f"  • Output directory: {settings.output_folder}")
    print(f"  • Manifest: {settings.output_folder / 'organization_manifest.json'}")


def example_5_custom_categories():
    """Example: Use custom categories."""
    print("\n" + "="*60)
    print("Example 5: Custom Categories")
    print("="*60)

    # Define custom categories
    custom_categories = ["urgent", "normal", "archive", "delete"]

    ollama = OllamaService()
    if not ollama.is_available():
        print("Error: Ollama service not available")
        return

    classifier = DocumentClassifier(ollama_service=ollama)

    # Override default categories
    classifier.categories = custom_categories

    print(f"Using custom categories: {', '.join(custom_categories)}")

    doc_path = Path("path/to/document.pdf")
    if doc_path.exists():
        result = classifier.classify_document(doc_path, include_reasoning=True)
        if result:
            print(f"\nClassified as: {result.category}")
            print(f"Reasoning: {result.confidence}")


def example_6_different_models():
    """Example: Use different Ollama models."""
    print("\n" + "="*60)
    print("Example 6: Different Ollama Models")
    print("="*60)

    # List available models
    ollama = OllamaService()
    if not ollama.is_available():
        print("Error: Ollama service not available")
        return

    print("Available Ollama models:")
    models = ollama.list_models()
    for model in models:
        print(f"  • {model}")

    # Use a specific model
    # Make sure the model is pulled first: ollama pull llama3.1:8b
    specific_model = "llama3.2:3b"

    print(f"\nUsing model: {specific_model}")
    ollama_custom = OllamaService(model=specific_model)
    classifier = DocumentClassifier(ollama_service=ollama_custom)

    # Classify with the custom model
    doc_path = Path("path/to/document.pdf")
    if doc_path.exists():
        result = classifier.classify_document(doc_path)
        if result:
            print(f"Classified as: {result.category}")


def example_7_error_handling():
    """Example: Proper error handling."""
    print("\n" + "="*60)
    print("Example 7: Error Handling")
    print("="*60)

    try:
        ollama = OllamaService()

        # Check service availability
        if not ollama.is_available():
            raise ConnectionError("Ollama service is not available")

        # Check if model exists
        models = ollama.list_models()
        if settings.ollama_model not in [m.split(":")[0] for m in models]:
            print(f"Warning: Model {settings.ollama_model} may not be available")
            print(f"Available models: {', '.join(models)}")

        classifier = DocumentClassifier(ollama_service=ollama)

        # Try to classify non-existent file
        doc_path = Path("nonexistent_file.pdf")
        result = classifier.classify_document(doc_path)

        if result is None:
            print(f"Failed to classify: {doc_path}")

    except ConnectionError as e:
        print(f"Connection error: {e}")
        print("Please ensure Ollama is running: ollama serve")
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("\n" + "#"*60)
    print("# AI Document Classification Pipeline - Examples")
    print("#"*60)

    # Run examples
    # Uncomment the examples you want to run

    # example_1_single_document()
    # example_2_batch_classification()
    # example_3_directory_classification()
    example_4_classify_and_organize()
    # example_5_custom_categories()
    # example_6_different_models()
    # example_7_error_handling()

    print("\n" + "#"*60)
    print("# Examples completed")
    print("#"*60 + "\n")


if __name__ == "__main__":
    main()
