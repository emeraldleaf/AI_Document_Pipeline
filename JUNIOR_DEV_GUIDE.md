# Junior Developer's Guide to the Codebase

Welcome! This guide will help you understand the AI Document Pipeline codebase.

## 🎯 Start Here

### 1. Read These Files First (in order):
1. **[README.md](README.md)** - What the system does
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - How it's structured
3. **This guide** - How to navigate the code

### 2. Then Explore the Code (in this order):
1. **Domain Layer** (`src/domain/`) - Core concepts and contracts
2. **Infrastructure Layer** (`src/infrastructure/`) - File extraction
3. **Services Layer** (`src/services/`) - Business logic
4. **High-Level** (`src/`) - CLI, orchestration

---

## 📁 Code Structure (Layered Architecture)

```
src/
├── domain/           # Core business concepts (START HERE)
│   ├── protocols.py  # Interfaces/contracts (what things do)
│   └── models.py     # Data structures (what things are)
│
├── infrastructure/   # External system integrations
│   └── extractors.py # READ PDF, Word, Excel files (WELL COMMENTED!)
│
├── services/         # Business logic
│   ├── ocr_service.py           # Extract text from images
│   ├── classification_service.py # Classify documents with AI
│   └── document_service.py      # Orchestrate everything
│
├── High-performance (NEW!)
│   ├── parallel_processor.py      # Multi-core processing
│   ├── async_batch_processor.py   # Async I/O processing
│   └── celery_tasks.py            # Distributed processing
│
└── classifier.py     # Legacy classification (still works)
```

---

## 🎓 Learning Path for Junior Developers

### Week 1: Understand the Domain

**Goal**: Learn what the system does and how data flows

1. **Read**: `src/domain/protocols.py`
   - Learn what a "Protocol" is (Python's interface)
   - Understand the contracts: `DocumentExtractor`, `OCRProcessor`, `ClassificationService`

2. **Read**: `src/domain/models.py`
   - Learn the data structures: `ExtractedContent`, `DocumentMetadata`
   - Understand the `Result` type (success/failure pattern)

3. **Trace a document flow**:
   ```
   File → Extractor → ExtractedContent → Classifier → Category → Organized
   ```

**Exercise**:
- Draw a diagram of how a PDF flows through the system
- Identify which class handles each step

---

### Week 2: Understand Document Extraction

**Goal**: Learn how we extract text from different file types

1. **Read**: `src/infrastructure/extractors.py` (HEAVILY COMMENTED!)
   - Start with `TextExtractor` (simplest)
   - Then `DOCXExtractor` (medium complexity)
   - Then `PDFExtractor` (most complex)

2. **Key Concepts to Learn**:
   - **Strategy Pattern**: Each extractor handles one file type
   - **Factory Pattern**: `create_extraction_service()` creates configured objects
   - **Async/Await**: Why and when we use it
   - **Error Handling**: `Result` type vs exceptions

3. **Trace the flow**:
   ```python
   # How extraction works:
   service = ExtractionService([TextExtractor(), PDFExtractor()])
   result = await service.extract_content(Path("doc.pdf"))

   # What happens:
   # 1. Service asks each extractor: "Can you handle this?"
   # 2. PDFExtractor says "yes"
   # 3. PDFExtractor.extract() runs
   # 4. Returns Result with ExtractedContent
   ```

**Exercise**:
- Add a new extractor for `.rtf` files
- Test it with a sample file

---

### Week 3: Understand Classification

**Goal**: Learn how AI classifies documents

1. **Read**: `src/services/classification_service.py`
   - Understand how we talk to Ollama (the LLM)
   - Learn about prompts and responses

2. **Read**: `src/ollama_service.py` (legacy but still used)
   - See how prompts are constructed
   - Understand confidence scoring

3. **Key Concepts**:
   - **LLM (Large Language Model)**: AI that reads text and makes decisions
   - **Prompts**: Instructions we give the AI
   - **Zero-shot learning**: AI classifies without prior training
   - **Few-shot learning**: We give examples to improve accuracy

**Exercise**:
- Modify the classification prompt
- Test with sample documents
- Observe how results change

---

### Week 4: Understand High-Performance Processing

**Goal**: Learn how we process 500K documents fast

1. **Read**: `src/parallel_processor.py`
   - Understand Python multiprocessing
   - Learn about worker pools
   - See how results are aggregated

2. **Read**: `src/async_batch_processor.py`
   - Understand asyncio and concurrency
   - Learn about semaphores (limiting concurrent operations)
   - See batch database inserts

3. **Read**: `src/celery_tasks.py`
   - Understand distributed task queues
   - Learn about Redis as a message broker
   - See horizontal scaling

**Key Concepts**:
- **Multiprocessing**: Use multiple CPU cores (parallel)
- **Async/Await**: Handle I/O efficiently (concurrent)
- **Task Queue**: Distribute work across machines (distributed)

**Exercise**:
- Run the parallel processor with 100 test docs
- Measure the speedup vs single-threaded
- Understand why it's faster

---

## 🔑 Key Patterns Used in This Codebase

### 1. Strategy Pattern (Extractors)
```python
# Each extractor implements the same interface
# The service picks the right one at runtime

for extractor in self.extractors:
    if extractor.can_extract(file_path):  # Ask: can you handle this?
        return await extractor.extract(file_path)  # Use the first match
```

**Why?** Easy to add new file types without changing existing code.

### 2. Result Type (Error Handling)
```python
# Instead of exceptions, we return Result objects
result = await extractor.extract(file_path)

if result.is_success:
    content = result.value  # Get the data
else:
    print(result.error)  # Get the error message
```

**Why?** Makes errors explicit and forces you to handle them.

### 3. Factory Pattern (Creation)
```python
# Factory functions create configured objects
service = create_extraction_service(ocr_service)

# Inside the factory:
# - Creates all extractors
# - Wires them together
# - Returns ready-to-use service
```

**Why?** Centralizes complex object creation.

### 4. Dependency Injection (Services)
```python
# Services receive their dependencies
class PDFExtractor:
    def __init__(self, ocr_service: OCRProcessor):
        self.ocr_service = ocr_service  # Injected!

# Not this:
# def __init__(self):
#     self.ocr_service = TesseractOCRService()  # Hard-coded!
```

**Why?** Makes testing easier (can inject mocks) and reduces coupling.

### 5. Protocol-Based Design (Interfaces)
```python
# Define what something does, not how
class DocumentExtractor(Protocol):
    def can_extract(self, file_path: Path) -> bool: ...
    async def extract(self, file_path: Path) -> Result[ExtractedContent]: ...

# Any class that implements these methods is a DocumentExtractor
```

**Why?** Flexibility - multiple implementations, easy to swap.

---

## 🐛 Common Debugging Scenarios

### Scenario 1: "Document extraction fails"

**Debug steps**:
1. Check the file exists: `file_path.exists()`
2. Check the file type: `file_path.suffix`
3. Check which extractor is used: Look for log message "Using XExtractor"
4. Check the error: `result.error` if `result.is_success == False`

**Common causes**:
- Unsupported file type
- Corrupted file
- Missing OCR for scanned PDFs
- File permissions

### Scenario 2: "Classification is slow"

**Debug steps**:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Check which model: `echo $OLLAMA_MODEL`
3. Check document size: Large PDFs take longer
4. Profile with: `python tests/test_performance_benchmark.py`

**Solutions**:
- Use smaller/faster model: `llama3.2:1b`
- Use parallel processing: `doc-classify classify-parallel`
- Enable GPU for Ollama

### Scenario 3: "Out of memory"

**Debug steps**:
1. Check memory usage: `htop` or Activity Monitor
2. Check batch size in parallel processing
3. Check number of workers

**Solutions**:
- Reduce number of workers: `-w 4` instead of `-w 8`
- Reduce batch size
- Process smaller batches

---

## 📚 Key Files to Study (With Comments)

### Heavily Commented (Start Here):
- ✅ **`src/infrastructure/extractors.py`** - Document extraction (EXCELLENT comments!)
- 🚧 **`src/parallel_processor.py`** - Parallel processing (to be commented)
- 🚧 **`src/async_batch_processor.py`** - Async processing (to be commented)

### To Be Commented:
- `src/services/classification_service.py`
- `src/services/ocr_service.py`
- `src/domain/protocols.py`
- `src/classifier.py`
- `config.py`

---

## 🔍 How to Trace Code Flow

### Example: "How does a PDF get classified?"

**Step 1: Entry Point** (CLI)
```bash
doc-classify classify document.pdf
```
↓
**Step 2: CLI Handler** (`src/cli.py`)
```python
def classify(input_path, ...):
    classifier.classify_document(input_path)
```
↓
**Step 3: Classifier** (`src/classifier.py`)
```python
def classify_document(file_path):
    # Extract content
    content = extractor.extract(file_path)
    # Classify content
    category = ollama.classify(content)
```
↓
**Step 4: Extractor** (`src/infrastructure/extractors.py`)
```python
class PDFExtractor:
    async def extract(file_path):
        # Extract text from PDF
        return Result.success(ExtractedContent(...))
```
↓
**Step 5: LLM Service** (`src/ollama_service.py`)
```python
def classify_document(content, categories):
    # Send to Ollama LLM
    response = ollama.generate(prompt)
    return category
```
↓
**Step 6: Result**
```
Category: "invoices"
```

---

## 🎯 Tips for Understanding the Code

### 1. Use the IDE's "Go to Definition" (Cmd+Click)
- Click on a class/function name
- Jump to its definition
- See how it's implemented

### 2. Use the IDE's "Find Usages" (Cmd+Click → Find Usages)
- See where a class/function is used
- Understand the flow

### 3. Run Tests to See How Things Work
```bash
# Run a specific test
pytest tests/test_extractors.py::test_pdf_extraction -v

# Run all tests
pytest tests/ -v
```

### 4. Add Print Statements (Debugging)
```python
print(f"DEBUG: file_path = {file_path}")
print(f"DEBUG: result = {result}")
```

### 5. Use the Python Debugger (pdb)
```python
import pdb; pdb.set_trace()  # Code will pause here

# Commands:
# n - next line
# s - step into function
# c - continue
# p variable_name - print variable
# q - quit
```

---

## 📖 Recommended Reading

### Python Concepts:
1. **Async/Await**: https://realpython.com/async-io-python/
2. **Type Hints & Protocols**: https://realpython.com/python-type-checking/
3. **Dataclasses**: https://realpython.com/python-data-classes/
4. **Context Managers** (`with`): https://realpython.com/python-with-statement/

### Design Patterns:
1. **Strategy Pattern**: https://refactoring.guru/design-patterns/strategy/python
2. **Factory Pattern**: https://refactoring.guru/design-patterns/factory-method/python
3. **Dependency Injection**: https://python-dependency-injector.ets-labs.org/

### Architecture:
1. **Layered Architecture**: Our `domain/`, `services/`, `infrastructure/` structure
2. **SOLID Principles**: See [SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md)

---

## 🚀 Your First Tasks

### Task 1: Fix a Bug (Easy)
1. Find an issue in the GitHub Issues
2. Reproduce it locally
3. Add a test that fails
4. Fix the code
5. Verify the test passes
6. Submit a PR

### Task 2: Add a Feature (Medium)
1. Add support for a new file format (e.g., `.rtf`)
2. Create a new extractor class
3. Add tests
4. Update documentation
5. Submit a PR

### Task 3: Improve Performance (Hard)
1. Profile the code with `test_performance_benchmark.py`
2. Identify a bottleneck
3. Optimize it
4. Measure improvement
5. Submit a PR with before/after metrics

---

## ❓ Getting Help

### When You're Stuck:

1. **Check the logs**: Most functions log their actions
   ```bash
   doc-classify classify document.pdf -v  # Verbose logging
   ```

2. **Read the tests**: Tests show how to use the code
   ```python
   # tests/test_extractors.py shows how to use extractors
   ```

3. **Check the documentation**:
   - [README.md](README.md) - Overview
   - [ARCHITECTURE.md](ARCHITECTURE.md) - Design
   - [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - All docs

4. **Ask questions**:
   - Open a GitHub Discussion
   - Ask in the team chat
   - Pair with a senior dev

---

## 🎓 Learning Milestones

### Junior → Mid-Level

**You're ready for mid-level work when you can**:
- [ ] Trace a document from input to output without help
- [ ] Add a new file format extractor
- [ ] Fix bugs in extraction or classification
- [ ] Write tests for new features
- [ ] Explain the Strategy pattern to someone else

### Mid-Level → Senior

**You're ready for senior work when you can**:
- [ ] Design a new feature end-to-end
- [ ] Optimize performance bottlenecks
- [ ] Review PRs and provide meaningful feedback
- [ ] Mentor junior developers
- [ ] Make architectural decisions

---

## 📝 Code Review Checklist

Before submitting a PR, check:

- [ ] **Code works**: Tests pass locally
- [ ] **Code is clean**: No commented-out code, clear variable names
- [ ] **Code is tested**: Added tests for new functionality
- [ ] **Code is documented**: Added comments for complex logic
- [ ] **Code follows patterns**: Uses existing patterns (Strategy, Factory, etc.)
- [ ] **No secrets**: No API keys or passwords in code
- [ ] **Logging**: Added appropriate log messages
- [ ] **Error handling**: Uses `Result` type or proper exception handling

---

## 🎉 Welcome to the Team!

This codebase is designed to be learnable. Take your time, ask questions, and don't be afraid to explore!

**Remember**:
- Everyone was a junior developer once
- Making mistakes is how you learn
- Reading code is harder than writing it
- Tests are your friend

**Happy coding!** 🚀

---

**Last Updated**: October 2025
**For Questions**: See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
