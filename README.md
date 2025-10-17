# Cuddly Potato

Cuddly Potato is a comprehensive data logging tool with both CLI and GUI interfaces for storing, managing, and exporting structured data entries. It uses an SQLite database to keep your data organized and supports exporting to both JSON and Excel formats.

## Features

- **Dual Interface**: Use either the command-line interface (CLI) or the graphical user interface (GUI)
- **Rich Data Schema**: Store entries with author, tags, context, question, reason, and answer fields
- **Auto-fill in GUI**: Author and tags are automatically retained from the last entry for faster data entry
- **Multiple Export Formats**: Export your data to JSON or Excel (`.xlsx`) files
- **Database Management**: Automatically remembers your last used database
- **Batch Import**: Import multiple entries from JSON files via CLI
- **Long Text Support**: All text fields support long content with proper formatting preservation
- **Unique IDs**: Each entry gets a unique auto-incrementing ID
- **Well-Tested**: Comprehensive test suite ensures reliability

## Data Schema

Each entry contains the following fields:

- **ID**: Auto-generated unique identifier
- **Author**: The author of the entry (required)
- **Tags**: Comma-separated tags for categorization (optional)
- **Context**: Background information or context (optional)
- **Question**: The main question being asked (required)
- **Reason**: The reason for asking the question (optional)
- **Answer**: The answer to the question (required)
- **Date**: Automatically recorded timestamp

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (for dependency management)

### Install Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/cuddly-potato.git
   cd cuddly-potato
   ```

2. **Install dependencies with Poetry:**

   ```bash
   poetry install
   ```

3. **Activate the virtual environment:**

   ```bash
   poetry shell
   ```

## Usage

### Command Line Interface (CLI)

The CLI provides powerful commands for managing your data entries. A database file named `cuddly_potato.db` will be automatically created in your current directory upon first use.

All commands accept a global `--db` option to specify a different database file. If omitted, the tool remembers the last database you used.

#### Adding Entries

**Interactive Mode** (prompts for required fields):
```bash
cuddly-potato add
```

**With All Options**:
```bash
cuddly-potato add \
  --author "John Doe" \
  --tags "python,data,analysis" \
  --context "Working on a data analysis project" \
  --question "How do I export data to Excel in Python?" \
  --reason "Need to share analysis results with non-technical team" \
  --answer "Use the openpyxl library to create Excel files"
```

**Using a Different Database**:
```bash
cuddly-potato --db ~/Documents/my_data.db add
```

#### Updating Entries

Update an existing entry by its ID:

```bash
cuddly-potato update 1 --author "Jane Doe" --tags "updated,tags"
```

You can update one or more fields at a time. Only provide the fields you want to change.

#### Importing from JSON

Import multiple entries from a JSON file:

```bash
cuddly-potato import-json entries.json
```

**Expected JSON format**:
```json
[
  {
    "author": "John Doe",
    "tags": "python,testing",
    "context": "Unit testing setup",
    "question": "How to write unit tests?",
    "reason": "Improve code quality",
    "answer": "Use pytest framework"
  },
  {
    "author": "Jane Smith",
    "tags": "documentation",
    "context": "Project documentation",
    "question": "Best practices for README files?",
    "reason": "Make project more accessible",
    "answer": "Include installation, usage, and examples"
  }
]
```

You can also pipe data from stdin:
```bash
cat entries.json | cuddly-potato import-json -
```

#### Exporting Data

**Export to JSON**:
```bash
cuddly-potato export-json output.json
```

**Export to Excel**:
```bash
cuddly-potato export-excel output.xlsx
```

The Excel export creates a nicely formatted spreadsheet with:
- Headers for all columns
- Auto-adjusted column widths
- All entries in a clean tabular format

### Graphical User Interface (GUI)

Launch the GUI application:

```bash
cuddly-potato gui
```

The GUI provides:
- Modern, aesthetic interface built with CustomTkinter
- Database selection with file picker
- Input fields for all data schema fields
- **Smart auto-fill**: After submitting an entry, the author and tags fields remain filled with the last entry's values, making it faster to enter multiple related entries
- Large text boxes for context, question, reason, and answer fields to accommodate long text
- Visual feedback with status messages
- Remembers your last used database

#### GUI Workflow

1. Select or create a database file (or use the default)
2. Fill in the entry fields:
   - **Author** and **Tags** will auto-fill from your last entry
   - Enter **Context**, **Question**, **Reason**, and **Answer**
3. Click "Add Entry to Database"
4. The form clears context/question/reason/answer but keeps author/tags for quick successive entries

## Development

### Running Tests

The project uses pytest for testing. Run the test suite:

```bash
pytest
```

Or with coverage:

```bash
pytest --cov=cuddly_potato
```

### Code Quality

Format code with Black:
```bash
black cuddly_potato tests
```

Lint with Ruff:
```bash
ruff check cuddly_potato tests
```

Type checking with mypy:
```bash
mypy cuddly_potato
```

## Project Structure

```
cuddly-potato/
├── cuddly_potato/
│   ├── __init__.py
│   ├── cli.py          # CLI interface and commands
│   ├── database.py     # Database operations and exports
│   └── gui.py          # GUI application
├── tests/
│   ├── __init__.py
│   ├── test_cli.py     # CLI tests
│   └── test_database.py # Database tests
├── pyproject.toml      # Project dependencies and config
└── README.md
```

## Examples

### Example 1: Research Notes

```bash
cuddly-potato add \
  --author "Alice Researcher" \
  --tags "machine-learning,research,2024" \
  --context "Exploring neural network architectures for NLP" \
  --question "What are the advantages of transformer models?" \
  --reason "Writing literature review section" \
  --answer "Transformers excel at capturing long-range dependencies through self-attention mechanisms..."
```

### Example 2: Interview Questions Database

```bash
cuddly-potato add \
  --author "HR Team" \
  --tags "interview,technical,python" \
  --context "Software Engineer position - Mid-level" \
  --question "Explain the difference between list and tuple in Python" \
  --reason "Assess basic Python knowledge" \
  --answer "Lists are mutable, tuples are immutable. Lists use [], tuples use ()..."
```

### Example 3: Customer Support FAQ

```bash
cuddly-potato add \
  --author "Support Team" \
  --tags "faq,billing,common" \
  --context "Recurring customer question about billing" \
  --question "How do I update my payment method?" \
  --reason "Most frequently asked billing question" \
  --answer "Navigate to Settings > Billing > Payment Methods, then click Update..."
```

## Tips

1. **Use Tags Effectively**: Tags are comma-separated and help categorize entries for later analysis
2. **Leverage Auto-fill**: In the GUI, author and tags persist between entries, making batch entry faster
3. **Export Regularly**: Use `export-json` or `export-excel` to back up your data
4. **Database Per Project**: Use the `--db` flag to maintain separate databases for different projects
5. **Long Text is Welcome**: All text fields (context, question, reason, answer) support long, formatted text

## License

This project is licensed under the GNU General Public License v3.0.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
