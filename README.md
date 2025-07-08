# Cuddly Potato

Cuddly Potato is a command-line interface (CLI) tool for storing, managing, and tracking question-answer pairs from large language models (LLMs). It uses an SQLite database to keep your data organized and allows for easy exporting to JSON for use in traditional data science workflows.

This tool is designed to help you track the progress of open-weight models over time by creating a structured dataset of their responses.

## Features

  * **Add Entries**: Easily add new question-answer pairs, including metadata like the model name, date, domain, and comments.
  * **Update Entries**: Modify existing entries in the database by their unique ID.
  * **Export to JSON**: Export the entire database of question-answer pairs to a JSON file, ready for analysis or use as a dataset.
  * **SQLite Backend**: All data is stored in a simple, file-based SQLite database.
  * **Unique Constraints**: Prevents duplicate entries for the same question and model combination.
  * **Well-Tested**: Comes with a full test suite to ensure reliability.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/cuddly-potato.git
    cd cuddly-potato
    ```

2.  **Install the project in editable mode:**
    This command uses the `setup.py` file to install the necessary dependencies (like Click) and creates a command-line entry point called `cuddly-potato`. Using the `-e` flag means that any changes you make to the source code will be immediately effective without needing to reinstall.

    ```bash
    pip install -e .
    ```

## Usage

Cuddly Potato is operated entirely from the command line. A database file named `cuddly_potato.db` will be automatically created in your project directory upon first use.

### Adding a New Entry

You can add a new entry in two ways:

1.  **Interactive Prompts**:
    The tool will prompt you for each piece of information.

    ```bash
    cuddly-potato add
    ```

2.  **Using Command-Line Options**:
    Provide all the information as flags.

    ```bash
    cuddly-potato add --question "What is the capital of France?" --model "Gemma3 27B" --answer "Paris" --domain "Geography" --subdomain "European Capitals" --comments "Initial test."
    ```

### Updating an Existing Entry

To update an entry, you need to know its `id`. You can update one or more fields at a time.

```bash
cuddly-potato update 1 --answer "The capital city of France is Paris." --comments "Updated for better clarity."
```

  * This command updates the `answer` and `comments` for the entry with `id` of 1.

### Exporting Data to JSON

To export all entries to a JSON file:

```bash
cuddly-potato export my_llm_data.json
```

  * This will create a file named `my_llm_data.json` in your current directory containing all the records from the database.

## Development and Testing 

This project uses Python's built-in `unittest` framework for testing. The tests are located in the `tests/` directory and run against a temporary test database that is created and destroyed for each test run.

To run the test suite, navigate to the project's root directory and run:

```bash
python -m unittest discover -s tests
```

You should see output indicating that all tests have passed successfully.

## License

This project is licensed under the **GNU General Public License v3.0**. See the `LICENSE` file for more details.
