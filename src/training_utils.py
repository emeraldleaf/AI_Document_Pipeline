"""Training and evaluation utilities for improving classification accuracy."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from loguru import logger

from src.classifier import DocumentClassifier, ClassificationResult


class TrainingDataCollector:
    """Collect training data from user feedback and classifications."""

    def __init__(self, output_file: Path = Path("training_data.jsonl")):
        """Initialize collector.

        Args:
            output_file: Path to store training data
        """
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def record_classification(
        self,
        content: str,
        predicted_category: str,
        correct_category: str,
        metadata: Optional[Dict] = None,
        confidence: Optional[str] = None,
    ):
        """Record a classification result for training.

        Args:
            content: Document content
            predicted_category: What the model predicted
            correct_category: The correct category
            metadata: Document metadata
            confidence: Model confidence/reasoning
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "content_preview": content[:1000],  # Store preview for privacy
            "predicted": predicted_category,
            "correct": correct_category,
            "was_correct": predicted_category == correct_category,
            "metadata": metadata or {},
            "confidence": confidence,
        }

        with open(self.output_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(
            f"Recorded classification: {predicted_category} → {correct_category} "
            f"({'✓' if entry['was_correct'] else '✗'})"
        )

    def get_examples_by_category(
        self, min_confidence: bool = True, max_per_category: int = 10
    ) -> Dict[str, List[str]]:
        """Generate few-shot examples from collected data.

        Args:
            min_confidence: Only include correct classifications
            max_per_category: Maximum examples per category

        Returns:
            Dict mapping categories to example content
        """
        if not self.output_file.exists():
            return {}

        examples = defaultdict(list)

        with open(self.output_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Only use correct classifications
                    if min_confidence and not entry.get("was_correct", False):
                        continue

                    category = entry["correct"]
                    content = entry["content_preview"]

                    if len(examples[category]) < max_per_category:
                        examples[category].append(content)

                except json.JSONDecodeError:
                    continue

        return dict(examples)

    def get_statistics(self) -> Dict[str, any]:
        """Get training data statistics.

        Returns:
            Statistics about collected data
        """
        if not self.output_file.exists():
            return {}

        total = 0
        correct = 0
        by_category = defaultdict(lambda: {"correct": 0, "total": 0})

        with open(self.output_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    total += 1

                    category = entry["correct"]
                    by_category[category]["total"] += 1

                    if entry.get("was_correct", False):
                        correct += 1
                        by_category[category]["correct"] += 1

                except json.JSONDecodeError:
                    continue

        return {
            "total_examples": total,
            "overall_accuracy": correct / total if total > 0 else 0,
            "by_category": dict(by_category),
        }

    def export_for_finetuning(self, output_file: Path):
        """Export data in format suitable for model fine-tuning.

        Args:
            output_file: Path to export formatted data
        """
        if not self.output_file.exists():
            logger.warning("No training data to export")
            return

        formatted_data = []

        with open(self.output_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Only export correct classifications
                    if entry.get("was_correct", False):
                        formatted_data.append(
                            {
                                "prompt": "Classify this document:",
                                "completion": entry["correct"],
                                "context": entry["content_preview"],
                            }
                        )

                except json.JSONDecodeError:
                    continue

        with open(output_file, "w") as f:
            for item in formatted_data:
                f.write(json.dumps(item) + "\n")

        logger.success(f"Exported {len(formatted_data)} examples to {output_file}")


class ClassificationEvaluator:
    """Evaluate classification model performance."""

    def __init__(self, classifier: DocumentClassifier):
        """Initialize evaluator.

        Args:
            classifier: DocumentClassifier instance to evaluate
        """
        self.classifier = classifier

    def evaluate(
        self, test_data: Dict[str, List[Path]], verbose: bool = True
    ) -> Dict[str, any]:
        """Evaluate classifier on labeled test data.

        Args:
            test_data: Dict mapping true categories to file paths
            verbose: Print detailed results

        Returns:
            Evaluation metrics
        """
        results = {
            "correct": 0,
            "total": 0,
            "per_category": {},
            "confusion_matrix": defaultdict(lambda: defaultdict(int)),
        }

        for true_category, files in test_data.items():
            category_correct = 0
            category_total = len(files)

            for file_path in files:
                try:
                    result = self.classifier.classify_document(file_path)
                    results["total"] += 1

                    if result:
                        predicted = result.category
                        results["confusion_matrix"][true_category][predicted] += 1

                        if predicted == true_category:
                            results["correct"] += 1
                            category_correct += 1
                    else:
                        logger.warning(f"Failed to classify {file_path.name}")

                except Exception as e:
                    logger.error(f"Error evaluating {file_path.name}: {e}")

            accuracy = category_correct / category_total if category_total > 0 else 0
            results["per_category"][true_category] = {
                "accuracy": accuracy,
                "correct": category_correct,
                "total": category_total,
            }

        results["overall_accuracy"] = (
            results["correct"] / results["total"] if results["total"] > 0 else 0
        )

        if verbose:
            self._print_results(results)

        return results

    def _print_results(self, results: Dict):
        """Print formatted evaluation results."""
        print("\n" + "=" * 60)
        print("CLASSIFICATION EVALUATION RESULTS")
        print("=" * 60)

        print(
            f"\nOverall Accuracy: {results['overall_accuracy']:.2%} "
            f"({results['correct']}/{results['total']})"
        )

        print("\nPer-Category Accuracy:")
        for category, stats in results["per_category"].items():
            print(
                f"  {category:20s}: {stats['accuracy']:.2%} "
                f"({stats['correct']}/{stats['total']})"
            )

        print("\nConfusion Matrix:")
        print(f"{'True ↓ / Pred →':20s}", end="")

        # Header
        all_categories = sorted(
            set(
                list(results["confusion_matrix"].keys())
                + [
                    pred
                    for preds in results["confusion_matrix"].values()
                    for pred in preds.keys()
                ]
            )
        )

        for cat in all_categories:
            print(f"{cat:12s}", end="")
        print()

        # Matrix
        for true_cat in all_categories:
            print(f"{true_cat:20s}", end="")
            for pred_cat in all_categories:
                count = results["confusion_matrix"][true_cat][pred_cat]
                print(f"{count:12d}", end="")
            print()

        print("\n" + "=" * 60)

    def compare_models(
        self, test_data: Dict[str, List[Path]], models: List[str]
    ) -> Dict[str, Dict]:
        """Compare different models on the same test data.

        Args:
            test_data: Test dataset
            models: List of model names to compare

        Returns:
            Comparison results
        """
        results = {}

        for model in models:
            logger.info(f"Evaluating model: {model}")

            # Update classifier model
            self.classifier.ollama.model = model

            # Evaluate
            model_results = self.evaluate(test_data, verbose=False)
            results[model] = model_results

            print(f"\n{model}: {model_results['overall_accuracy']:.2%}")

        return results


class FewShotLearning:
    """Implement few-shot learning for classification."""

    def __init__(self, examples: Optional[Dict[str, List[str]]] = None):
        """Initialize with examples.

        Args:
            examples: Dict mapping categories to example documents
        """
        self.examples = examples or {}

    def add_example(self, category: str, content: str):
        """Add a training example.

        Args:
            category: Document category
            content: Document content
        """
        if category not in self.examples:
            self.examples[category] = []
        self.examples[category].append(content)

    def load_from_file(self, file_path: Path):
        """Load examples from JSON file.

        Args:
            file_path: Path to examples file
        """
        with open(file_path, "r") as f:
            self.examples = json.load(f)

        logger.info(f"Loaded {len(self.examples)} category examples")

    def save_to_file(self, file_path: Path):
        """Save examples to JSON file.

        Args:
            file_path: Path to save examples
        """
        with open(file_path, "w") as f:
            json.dump(self.examples, f, indent=2)

        logger.info(f"Saved examples to {file_path}")

    def get_prompt_with_examples(
        self, content: str, metadata: Dict, categories: List[str], max_examples: int = 2
    ) -> Tuple[str, str]:
        """Generate prompt with few-shot examples.

        Args:
            content: Document to classify
            metadata: Document metadata
            categories: Available categories
            max_examples: Max examples per category

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Build examples section
        examples_text = "Learn from these example classifications:\n\n"

        for category in categories:
            if category in self.examples:
                examples_text += f"Category: {category}\n"
                for i, example in enumerate(self.examples[category][:max_examples], 1):
                    # Truncate example
                    truncated = example[:200] + "..." if len(example) > 200 else example
                    examples_text += f"  Example {i}: {truncated}\n"
                examples_text += "\n"

        system_prompt = f"""You are an expert document classifier.

{examples_text}

Classify new documents following these patterns. Be consistent with the examples."""

        user_prompt = f"""Classify this document based on the examples above:

File: {metadata.get('file_name', 'N/A')}
Type: {metadata.get('file_type', 'N/A')}

Content:
{content[:2000]}

Choose ONE category from: {', '.join(categories)}

Category:"""

        return system_prompt, user_prompt


def generate_modelfile(
    base_model: str,
    examples: Dict[str, List[str]],
    output_file: Path,
    system_message: Optional[str] = None,
):
    """Generate an Ollama Modelfile for custom model creation.

    Args:
        base_model: Base model to use (e.g., "llama3.2:3b")
        examples: Training examples by category
        output_file: Path to save Modelfile
        system_message: Optional custom system message
    """
    modelfile = f"""FROM {base_model}

# Set parameters for classification
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40

# System message
SYSTEM \"\"\"{system_message or 'You are an expert document classifier trained on specific document types.'}\"\"\"

"""

    # Add examples as message pairs
    for category, example_list in examples.items():
        for example in example_list[:5]:  # Max 5 examples per category
            # Clean the example
            clean_example = example.replace('"', '\\"').replace("\n", " ")[:500]

            modelfile += f'MESSAGE user Classify this document: "{clean_example}"\n'
            modelfile += f"MESSAGE assistant {category}\n\n"

    with open(output_file, "w") as f:
        f.write(modelfile)

    logger.success(f"Generated Modelfile: {output_file}")
    logger.info(f"Create model with: ollama create my-classifier -f {output_file}")
