# support-chatbot
A support chatbot using Groq and RAG
## Tech Stack
ReactJS + Flask + Groq Llama3 (small) + ChromaDB + LlamaIndex

## Instructions for Running Locally

1. Clone repository
2. `cd chatbot`
3. Run `npm install` in `/chatbot` directory to start frontend part
4. `cd ..` to `/support-chatbot` parent directory
5. Run `pip install -r requirement.txt`
6. If `llama-index-vector-stores-chroma` gives dependency errors, install it manually using `pip install llama-index-vector-stores-chroma`

### NOTE: Data collected through webcrawling is included and crawling is turned off by default to prevent redundancy

5. IF `crawled_data` is empty or changes are made to crawler function:
    - In `api/api.py` uncomment till line 48 to run web crawling if crawled_data is empty
    Otherwise, simply run the `api/api.py` file with `python -u [absolute or relative path to api/api.py]`

6. Open `localhost:5173` or the port on which React project is running.
7. Use the app.

## Backend - RAG integration with LLM

**1. Libraries Used:**

* **`os`:** For operating system interactions (file/directory operations).
* **`hashlib`:** For generating URL hashes (MD5).
* **`sys`:** For system-specific parameters and functions (logging).
* **`requests`:** For making HTTP requests to fetch web pages.
* **`BeautifulSoup`:** For parsing HTML content.
* **`urllib.parse`:** For URL parsing and manipulation.
* **`time`:** For adding delays during crawling.
* **`logging`:** For logging messages.
* **`llama_index.core`:** The core LlamaIndex library, used for building the index, handling documents, and creating the query engine.
* **`chromadb`:** Used for vector storage.
* **`llama_index.llms.groq`:** Integrates the Groq LLM.
* **`llama_index.embeddings.huggingface`:** Integrates HuggingFace embeddings.

**2. Code Functionality:**

* **`get_file_path(url)`:**
    * Generates a unique file path for each crawled URL using an MD5 hash and a subdirectory based on the domain.
    * Creates the necessary directories if they don't exist.
* **`crawl_website(start_url, base_url=None, visited=None, delay=1)`:**
    * Recursively crawls a website, starting from `start_url`.
    * Fetches HTML content using `requests`.
    * Parses HTML using `BeautifulSoup` and extracts text.
    * Saves the extracted text to a file using `get_file_path`.
    * Finds links on the page and recursively crawls them, ensuring the crawler stays within the same domain.
    * Respects a delay between requests.
    * limits the amount of pages crawled to 5.
* **`load_local_data()`:**
    * Loads crawled data from the `crawled_data` directory.
    * Creates `Document` objects for each file, including the URL as metadata.
* **`init_index(embed_model)`:**
    * Loads documents from the crawled data.
    * Initializes a Chroma vector store.
    * Creates a vector index using LlamaIndex, using the HuggingFace embedding model.
* **`init_llm()`:**
    * Initializes the Groq LLM and the HuggingFace embedding model.
    * Sets the LlamaIndex settings to use these models.
* **`init_query_engine(index)`:**
    * Creates a query engine from the vector index.
    * Uses a custom prompt template for question answering.
    * Configures the retriever to return the top 3 most similar documents.
* **`chat(input_question, user)`:**
    * Takes a user question as input.
    * Uses the query engine to retrieve relevant information and generate a response.
    * Returns the response.
* **`chat_cmd()`:**
    * Provides a command-line interface for interacting with the chatbot.
    * Allows users to enter questions and receive responses.

**3. Workflow:**

1.  **Crawling:** The `crawl_website` function is used to crawl specified websites and save their content to local files.
2.  **Indexing:** The `init_index` function loads the crawled data, creates a vector index, and stores it in ChromaDB.
3.  **LLM and Embedding Initialization:** The `init_llm` function initializes the Groq LLM and the HuggingFace embedding model.
4.  **Query Engine Setup:** The `init_query_engine` function sets up the query engine with a custom prompt template.
5.  **Chatting:** The `chat` or `chat_cmd` functions are used to interact with the chatbot, allowing users to ask questions and receive answers based on the crawled data.

## Backend - Flask API

**Libraries Used:**

* **`flask`:** A micro web framework for Python used to build the API.
* **`flask_cors`:** A Flask extension that handles Cross-Origin Resource Sharing (CORS), allowing requests from different origins (like a React frontend).
* **`logging`:** Python's built-in logging module for tracking application events and errors.
* **`sys`:** Provides access to system-specific parameters and functions, used here for logging.
* **`mod_model`:** The module containing web crawling, indexing, and question-answering logic.
* **`config`:** A module holding configuration variables like `HTTP_PORT`.

**High-Level Working:**

1.  **Initialization:**
    * The Flask application is created.
    * CORS is enabled.
    * Logging is configured.
    * The `init_llm()` function from `mod_model` is called to initialize the Large Language Model (LLM) and embedding model.
    * The `crawl_website()` function from `mod_model` is used to crawl specified websites and store their content.
    * The `init_index()` function from `mod_model` is used to create a vector index of the crawled data.
    * The `init_query_engine()` function from `mod_model` is used to create a query engine to be able to query the index.
    * The Flask application starts, listening on the specified port.

2.  **API Endpoints:**
    * **`/` (GET):** A simple endpoint that returns a "hi, look around" message.
    * **`/api/question` (POST):**
        * Receives a POST request containing a JSON payload with a "question" and "user_id".
        * Validates the request's `Content-Type` header (must be `application/json`).
        * Extracts the question and user ID from the JSON data.
        * Calls the `chat()` function from `mod_model` to process the question using the LLM and the indexed data.
        * Returns a JSON response containing the "answer" from the LLM.

3.  **Question Processing:**
    * The `chat()` function (from `mod_model`) uses the query engine to search the vector index for relevant information based on the user's question.
    * The LLM generates a response based on the retrieved information and a predefined prompt template.
    * The response is then returned to the API.

In essence, the Flask app acts as a web service that exposes a chatbot interface. It crawls websites, indexes their content, and uses an LLM to answer user questions based on that content.

## Frontend - ReactJS

This React component creates a chatbot interface. Here's a concise breakdown:

1.  **User Input:** The user types a message in the input field.
2.  **Send Message:** When the user clicks "Send" or presses Enter, `handleSendMessage` is called.
3.  **API Request:** `handleSendMessage` uses `axios.post` to send the user's message (`question`) and a `user_id` to the Flask API endpoint (`http://localhost:7654/api/question`).
4.  **API Response:** The Flask API processes the question and sends back a JSON response containing the chatbot's `answer`.
5.  **Display Response:** The React component receives the API response, extracts the `answer`, and displays it as a message in the chat interface, using `react-markdown` to render markdown.
6.  **Error Handling:** If the API request fails, an error message is displayed to the user.
7.  **Chat Display:** The component maintains a list of messages, which get displayed in a scrollable chat area.
