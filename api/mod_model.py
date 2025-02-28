import os
import hashlib
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from urllib.robotparser import RobotFileParser
from llama_index.core import Document
import chromadb
GROQ_API_KEY = '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'

from llama_index.llms.groq import Groq
# from llama_index.llms.huggingface import HuggingFaceLLM
# from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI

# from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import (Settings, VectorStoreIndex, SimpleDirectoryReader, PromptTemplate, Document)
from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = "crawled_data"  # Directory to store crawled data
MAX_CRAWL_DEPTH = 100  # Maximum depth for recursive crawling

# def can_fetch(url, user_agent="MyCrawler"):
#     """Checks if a URL can be fetched according to robots.txt."""
#     parsed_url = urlparse(url)
#     robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
#     rp = RobotFileParser()
#     rp.set_url(robots_url)
#     try:
#         rp.read()
#         return rp.can_fetch(user_agent, url)
#     except:
#         return True

def get_file_path(url):
    """Generates a unique file path for a URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    subdir_name = url.split('/')[2]
    directory_path = os.path.join(DATA_DIR, subdir_name)
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)  # Use makedirs for nested directories
            print(f"Directory '{directory_path}' created.")
        except OSError as e:
            print(f"Error creating directory '{directory_path}': {e}")
    return os.path.join(directory_path, f"{url_hash}.txt")

# count = 0
# visited = set()
def crawl_website(start_url, base_url=None, visited=None, delay=1):
    """Recursively crawls a website and saves content to files."""
    # global count
    # global visited
    # if count > 100: return
    if visited is None:
        visited = set()
    if len(visited) > MAX_CRAWL_DEPTH: return
    if base_url is None:
        base_url = urlparse(start_url).netloc

    if start_url in visited:
        return

    visited.add(start_url)
    # if not can_fetch(start_url):
    #     logging.info(f'Not allowed to crawl {start_url}')
    #     return

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(start_url, headers=headers)
        # print(response.json())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        file_path = get_file_path(start_url)
        print(file_path)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {start_url}\n\n{text}")

        links = [urljoin(start_url, link.get("href")) for link in soup.find_all("a") if link.get("href")]
        for link in links:
            parsed_link = urlparse(link)
            if parsed_link.netloc == base_url and link not in visited:
                time.sleep(delay)
                if len(visited) > MAX_CRAWL_DEPTH: return
                crawl_website(link, base_url, visited, delay)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error crawling {start_url}: {e}")

def load_local_data():
    """Loads crawled data from local files and creates Document objects."""
    documents = []
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if filename.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                url = content.split("URL: ")[1].split("\n")[0]
                text = "\n".join(content.split("\n")[2:])
                documents.append(Document(text=text, metadata={"source": url}))
    return documents

def init_index(embed_model):
    """Initializes the index from local data."""
    reader = SimpleDirectoryReader(input_dir="crawled_data", recursive=True)
    documents = reader.load_data()
    # documents = []
    # if urls:
    #     for url in urls:
    #         text = get_text_from_url(url)
    #         if text:
    #             documents.append(Document(text=text, metadata={"source": url}))

    logging.info("index creating with `%d` documents", len(documents))

    chroma_client = chromadb.EphemeralClient()
    # chroma_client.clear_system_cache()
    chroma_collection = chroma_client.create_collection("iollama")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # use this to set custom chunk size and splitting
    # https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/

    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context, embed_model=embed_model)

    return index

def init_llm():
    llm = Groq(model='llama3-8b-8192', api_key=GROQ_API_KEY)
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = llm
    Settings.embed_model = embed_model

def init_query_engine(index):
    global query_engine

    # custome prompt template
    template = (
    "Your role is to assist users by answering their questions related to the product using the provided documentation. "
    "Your goal is to help users set up and use the product effectively, troubleshoot issues, and perform specific tasks.\n\n"
    "Context Provided:\n"
    "-----------------------------------------\n"
    "{context_str}\n"
    "-----------------------------------------\n\n"
    "User Question: {query_str}\n\n"
    "Guidelines for Your Response:\n"
    "1. Use simple and clear language to ensure the answer is easy to understand.\n"
    "2. Provide accurate and relevant information based only on the context provided.\n"
    "3. If the context does not contain enough information to answer the question, politely inform the user and suggest where they might find additional help (e.g., official documentation, support forums).\n"
    "4. Avoid adding any information not present in the context.\n"
    "5. If the question involves steps or instructions, break them down into a numbered or bullet-point list for clarity.\n\n"
    "Your Answer:\n"
    "[Provide your response here, adhering to the guidelines above.]"
)
    # template = (
    #     "Your job is to answer questions related to the products for which documentation information is provided"
    #     "Help users in solving their queries relating to setting up various CDP and help them perform specific tasks\n\n"
    #     "Here is some context related to the query:\n"
    #     "-----------------------------------------\n"
    #     "{context_str}\n"
    #     "-----------------------------------------\n"
    #     "Considering the above information, please respond to the following inquiry in a detail using simple language and accurate information\n"
    #     "Question: {query_str}\n\n"
    #     "The answer should use simple language and be accurate. Do not provide any information that is not present in the context above."
    # )
    qa_template = PromptTemplate(template)

    # build query engine with custom template
    # text_qa_template specifies custom template
    # similarity_top_k configure the retriever to return the top 3 most similar documents,
    # the default value of similarity_top_k is 2
    query_engine = index.as_query_engine(text_qa_template=qa_template, similarity_top_k=3)

    return query_engine


def chat(input_question, user):
    global query_engine

    response = query_engine.query(input_question)
    logging.info("got response from llm - %s", response)

    return response.response


def chat_cmd():
    global query_engine

    while True:
        input_question = input("Enter your question (or 'exit' to quit): ")
        if input_question.lower() == 'exit':
            break

        response = query_engine.query(input_question)
        logging.info("got response from llm - %s", response)


# Example Usage
# if __name__ == '__main__':
#     init_llm()
#     start_url = [
#         'https://docs.mparticle.com/',
#         'https://docs.lytics.com/',
#         'https://docs.zeotap.com/home/en-us/',
#         'https://segment.com/docs/?ref=nav',
#     ]
#     for url in start_url:
#         crawl_website(url)
#     print('Happening...\n\n\n\n')
#     index = init_index(Settings.embed_model)
#     init_query_engine(index)
#     chat_cmd()