# Training & Fine-tuning Guide

This guide explains how to improve classification accuracy through various training and optimization approaches.

## Table of Contents

1. [Understanding the Classification System](#understanding-the-classification-system)
2. [Prompt Engineering (No Training Required)](#prompt-engineering)
3. [Few-Shot Learning](#few-shot-learning)
4. [Fine-tuning Ollama Models](#fine-tuning-ollama-models)
5. [Creating Custom Models](#creating-custom-models)
6. [Training Data Collection](#training-data-collection)
7. [Evaluation & Improvement](#evaluation--improvement)

---

## Understanding the Classification System

The current system uses **zero-shot learning** - the LLM classifies documents without any prior training on your specific documents. The model relies on:

1. **Pre-trained knowledge** from the base model (llama, mistral, etc.)
2. **Prompt engineering** to guide classification
3. **Content + metadata** analysis

### Current Flow

```
Document → Extract Content → Prompt LLM → Classify → Validate
```

---

## Prompt Engineering (No Training Required)

The **fastest and easiest** way to improve accuracy without any training.

### 1. Enhanced System Prompts

Edit [src/ollama_service.py](src/ollama_service.py) to customize the system prompt:

```python
# Current system prompt (line ~145)
system_prompt = """You are an expert document classifier. Your task is to analyze documents and classify them into the most appropriate category based on their content, structure, and metadata.

Be precise and consistent. Only respond with the category name, nothing else."""

# Enhanced version with domain-specific instructions
system_prompt = """You are an expert legal document classifier with 20 years of experience.

Classification Rules:
- Invoices: Look for amounts, invoice numbers, payment terms
- Contracts: Look for agreement language, parties, signatures
- Reports: Look for analysis, findings, conclusions
- Correspondence: Look for emails, letters, memos

Always consider:
1. Document structure and formatting
2. Legal terminology and keywords
3. Document metadata (author, dates)
4. Context clues in content

Be precise and consistent. Only respond with the category name."""
```

### 2. Category-Specific Prompts

Create detailed category definitions:

```python
def get_enhanced_classification_prompt(content, metadata, categories):
    """Enhanced prompt with category descriptions."""

    # Define what each category means
    category_descriptions = {
        "invoices": "Financial documents requesting payment, containing amounts, due dates, and line items",
        "contracts": "Legal agreements between parties with terms, conditions, and signatures",
        "reports": "Analytical documents with findings, data, and conclusions",
        "correspondence": "Emails, letters, and memos for communication"
    }

    descriptions_text = "\n".join([
        f"- {cat}: {category_descriptions.get(cat, 'Documents of this type')}"
        for cat in categories
    ])

    prompt = f"""Classify this document into ONE category.

Category Definitions:
{descriptions_text}

Document Information:
Title: {metadata.get('title', 'N/A')}
File Type: {metadata.get('file_type', 'N/A')}

Content:
{content[:2000]}

Choose the most appropriate category: {', '.join(categories)}

Category:"""

    return prompt
```

### 3. Add Keyword Matching

Enhance classification with keyword hints:

```python
# Add to src/ollama_service.py
CATEGORY_KEYWORDS = {
    "invoices": ["invoice", "amount due", "payment", "bill", "total", "$"],
    "contracts": ["agreement", "party", "terms", "whereas", "hereby"],
    "reports": ["analysis", "findings", "conclusion", "results", "summary"],
    "correspondence": ["dear", "sincerely", "regards", "from:", "to:"]
}

def get_keyword_hints(content, categories):
    """Provide keyword hints to the LLM."""
    hints = []
    content_lower = content.lower()

    for category in categories:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        found = [kw for kw in keywords if kw in content_lower]
        if found:
            hints.append(f"- {category}: found keywords {found}")

    return "\n".join(hints) if hints else "No obvious keywords found"
```

---

## Few-Shot Learning

Provide examples to guide the model - **no training required**!

### Implementation

Create a new method in [src/ollama_service.py](src/ollama_service.py):

```python
def classify_with_examples(
    self,
    content: str,
    metadata: Dict[str, Any],
    categories: List[str],
    examples: Dict[str, List[str]]
) -> Optional[str]:
    """Classify with few-shot examples.

    Args:
        content: Document content
        metadata: Document metadata
        categories: Available categories
        examples: Dict mapping categories to example content

    Returns:
        Classified category
    """

    # Build examples section
    examples_text = "Classification Examples:\n\n"
    for category, example_list in examples.items():
        examples_text += f"Category: {category}\n"
        for i, example in enumerate(example_list[:2], 1):  # Max 2 examples per category
            examples_text += f"Example {i}: {example[:200]}...\n"
        examples_text += "\n"

    system_prompt = f"""You are an expert document classifier. Learn from these examples:

{examples_text}

Now classify new documents following these patterns."""

    prompt = f"""Based on the examples above, classify this document:

Document Title: {metadata.get('file_name', 'N/A')}
Content: {content[:2000]}

Category:"""

    return self.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.1
    )
```

### Usage Example

```python
# Define examples for each category
examples = {
    "invoices": [
        "Invoice #12345\nDate: 2025-01-15\nAmount Due: $1,500.00\nPayment Terms: Net 30",
        "BILL TO: Acme Corp\nInvoice Date: 2025-02-01\nTotal: $3,200.00"
    ],
    "contracts": [
        "SERVICE AGREEMENT\nThis Agreement made on January 1, 2025\nBetween Party A and Party B",
        "EMPLOYMENT CONTRACT\nEffective Date: 2025-01-01\nEmployee: John Doe"
    ],
    "reports": [
        "QUARTERLY REPORT\nExecutive Summary: Sales increased by 15%\nFindings: Market growth...",
        "RESEARCH FINDINGS\nMethodology: Survey of 500 participants\nResults: 80% satisfaction"
    ]
}

# Use in classification
ollama = OllamaService()
result = ollama.classify_with_examples(
    content=document_text,
    metadata=document_metadata,
    categories=["invoices", "contracts", "reports"],
    examples=examples
)
```

---

## Fine-tuning Ollama Models

**Create a domain-specific model** trained on your documents.

### Step 1: Prepare Training Data

Create a training dataset in JSONL format:

```bash
# Create training_data.jsonl
cat > training_data.jsonl << 'EOF'
{"prompt": "Classify this document", "completion": "invoices", "context": "Invoice #12345 Amount Due: $1500"}
{"prompt": "Classify this document", "completion": "contracts", "context": "Agreement between Party A and Party B"}
{"prompt": "Classify this document", "completion": "reports", "context": "Quarterly Analysis Findings: Revenue up 20%"}
EOF
```

### Step 2: Create a Modelfile

```bash
# Create Modelfile
cat > Modelfile << 'EOF'
FROM llama3.2:3b

# Set parameters
PARAMETER temperature 0.1
PARAMETER top_p 0.9

# System message
SYSTEM """You are an expert document classifier trained on legal and financial documents.

Your task is to classify documents into these categories:
- invoices: Financial billing documents
- contracts: Legal agreements
- reports: Analytical documents
- correspondence: Communication documents

Analyze the content, structure, and metadata carefully."""

# Add training examples as context
MESSAGE user Classify: Invoice #12345 Date: 2025-01-01 Amount: $1,500
MESSAGE assistant invoices

MESSAGE user Classify: SERVICE AGREEMENT between Acme Corp and XYZ Inc
MESSAGE assistant contracts

MESSAGE user Classify: Q4 Financial Report - Executive Summary
MESSAGE assistant reports

MESSAGE user Classify: Dear John, Regarding our meeting...
MESSAGE assistant correspondence
EOF
```

### Step 3: Create Custom Model

```bash
# Create the model
ollama create doc-classifier -f Modelfile

# Test it
ollama run doc-classifier "Classify this: Invoice #999 Total: $500"
```

### Step 4: Use Custom Model

Update your `.env` file:

```bash
OLLAMA_MODEL=doc-classifier
```

Or use in code:

```python
ollama = OllamaService(model="doc-classifier")
classifier = DocumentClassifier(ollama_service=ollama)
```

---

## Creating Custom Models

For **production use**, create a fully fine-tuned model.

### Option 1: Using Ollama's Create Command (Simple)

```bash
# 1. Create base Modelfile with examples
cat > Modelfile << 'EOF'
FROM llama3.2:3b

PARAMETER temperature 0.1

SYSTEM "You are a document classifier specializing in [YOUR DOMAIN]"

# Add 50-100 examples
MESSAGE user [example document 1]
MESSAGE assistant [category 1]

MESSAGE user [example document 2]
MESSAGE assistant [category 2]

# ... more examples
EOF

# 2. Create model
ollama create my-doc-classifier -f Modelfile
```

### Option 2: Full Fine-tuning (Advanced)

Requires more resources but better results.

```bash
# 1. Install required tools
pip install torch transformers peft accelerate

# 2. Prepare dataset (CSV format)
cat > training_data.csv << 'EOF'
text,category
"Invoice #12345 Amount: $1500","invoices"
"SERVICE AGREEMENT dated 2025-01-01","contracts"
"Quarterly Report Q4 2024","reports"
EOF
```

Create fine-tuning script:

```python
# fine_tune.py
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
import pandas as pd

# Load base model
model_name = "meta-llama/Llama-3.2-3B"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Load your training data
df = pd.read_csv("training_data.csv")

# Configure LoRA for efficient fine-tuning
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# Training code here...
# (This is a simplified example - full implementation is complex)

# After training, save the model
model.save_pretrained("./doc-classifier-finetuned")

# Convert to Ollama format
# ollama create doc-classifier-ft -f Modelfile
```

### Option 3: Using Commercial Services

For best results without complexity:

1. **OpenAI Fine-tuning**: Use GPT-3.5/4 fine-tuning
2. **Anthropic Claude**: Use prompt caching and examples
3. **HuggingFace AutoTrain**: Automated fine-tuning

Then export and convert to Ollama format.

---

## Training Data Collection

### Automated Collection

Create a script to collect training data from user feedback:

```python
# src/training_collector.py
import json
from pathlib import Path
from datetime import datetime

class TrainingDataCollector:
    """Collect training data from classifications."""

    def __init__(self, output_file: Path = Path("training_data.jsonl")):
        self.output_file = output_file

    def record_classification(
        self,
        content: str,
        predicted_category: str,
        correct_category: str,
        metadata: dict
    ):
        """Record a classification for training."""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "content_preview": content[:500],
            "predicted": predicted_category,
            "correct": correct_category,
            "metadata": metadata,
            "was_correct": predicted_category == correct_category
        }

        with open(self.output_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def generate_training_examples(self):
        """Generate few-shot examples from collected data."""

        examples = {}
        with open(self.output_file, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry["was_correct"]:
                    category = entry["correct"]
                    if category not in examples:
                        examples[category] = []
                    examples[category].append(entry["content_preview"])

        return examples
```

### Interactive Correction

Add to [src/cli.py](src/cli.py):

```python
@cli.command()
@click.argument("results_file", type=click.Path(exists=True))
def review(results_file: str):
    """Review and correct classifications."""

    collector = TrainingDataCollector()

    # Load results
    with open(results_file) as f:
        results = json.load(f)

    for result in results["results"]:
        console.print(f"\nFile: {result['file_name']}")
        console.print(f"Predicted: {result['category']}")

        correct = click.prompt(
            "Correct category (press Enter if correct)",
            default=result['category']
        )

        collector.record_classification(
            content=result.get('content', ''),
            predicted_category=result['category'],
            correct_category=correct,
            metadata=result['metadata']
        )

    console.print("\n[green]Training data saved![/green]")
```

---

## Evaluation & Improvement

### 1. Test Classification Accuracy

```python
# src/evaluate.py
from pathlib import Path
from typing import Dict, List
import json

class ClassificationEvaluator:
    """Evaluate classification accuracy."""

    def __init__(self, classifier: DocumentClassifier):
        self.classifier = classifier

    def evaluate(
        self,
        test_data: Dict[str, List[Path]]
    ) -> Dict[str, float]:
        """Evaluate on labeled test data.

        Args:
            test_data: Dict mapping categories to file paths

        Returns:
            Accuracy metrics
        """

        correct = 0
        total = 0
        per_category = {}

        for true_category, files in test_data.items():
            category_correct = 0

            for file_path in files:
                result = self.classifier.classify_document(file_path)
                total += 1

                if result and result.category == true_category:
                    correct += 1
                    category_correct += 1

            per_category[true_category] = category_correct / len(files)

        return {
            "overall_accuracy": correct / total,
            "per_category_accuracy": per_category,
            "total_documents": total
        }

# Usage
test_data = {
    "invoices": list(Path("test_data/invoices").glob("*.pdf")),
    "contracts": list(Path("test_data/contracts").glob("*.pdf")),
}

evaluator = ClassificationEvaluator(classifier)
results = evaluator.evaluate(test_data)
print(f"Accuracy: {results['overall_accuracy']:.2%}")
```

### 2. Monitor and Improve

```python
# Track performance over time
def track_accuracy(results_file: Path):
    """Track accuracy trends."""

    with open(results_file) as f:
        data = [json.loads(line) for line in f]

    # Calculate accuracy over time
    accuracy_by_date = {}
    for entry in data:
        date = entry["timestamp"][:10]
        if date not in accuracy_by_date:
            accuracy_by_date[date] = {"correct": 0, "total": 0}

        accuracy_by_date[date]["total"] += 1
        if entry["was_correct"]:
            accuracy_by_date[date]["correct"] += 1

    # Print trends
    for date, stats in sorted(accuracy_by_date.items()):
        acc = stats["correct"] / stats["total"]
        print(f"{date}: {acc:.2%} ({stats['correct']}/{stats['total']})")
```

---

## Best Practices

### Quick Wins (No Training)

1. **Better prompts** - Most impactful, immediate improvement
2. **More specific categories** - "sales_invoices" vs "invoices"
3. **Larger models** - Use llama3.1:8b instead of llama3.2:3b
4. **Keyword hints** - Pre-filter obvious cases

### Medium Effort (Few-Shot)

1. **Collect 5-10 examples per category**
2. **Create Modelfile with examples**
3. **Test and iterate**

### High Effort (Fine-tuning)

1. **Collect 100+ labeled examples**
2. **Fine-tune base model**
3. **Evaluate and iterate**
4. **Version and track models**

---

## Recommended Approach

```
Start → Prompt Engineering (Day 1)
      ↓
      Few-Shot Learning (Week 1)
      ↓
      Collect Training Data (Ongoing)
      ↓
      Fine-tune Model (Month 1)
      ↓
      Continuous Improvement
```

---

## Next Steps

1. **Immediate**: Enhance prompts in [src/ollama_service.py](src/ollama_service.py)
2. **Short-term**: Implement few-shot learning
3. **Long-term**: Collect data and fine-tune

For questions, see [README.md](README.md) or open an issue.

---

**Remember**: Start simple (prompt engineering) and only add complexity if needed!
