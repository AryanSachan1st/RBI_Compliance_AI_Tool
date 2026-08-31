from langchain_openai import ChatOpenAI
from models.clause_model import ExtractedClause, ExtractedClauses
from system_prompts.clause_extraction_prompt import CLAUSE_EXTRACTION_SYSTEM_PROMPT
from system_prompts.contract_analysis_prompt import CONTRACT_ANALYSIS_SYSTEM_PROMPT
from models.clause_model import ContractAnalysis
from models.entity_model import StructuredDocumentEntities
from system_prompts.entity_extraction_prompt import ENTITY_EXTRACTION_SYSTEM_PROMPT
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config.settings import OPENAI_API_KEY
import asyncio

clause_llm = ChatOpenAI(
    model="gpt-5.6-luna",
    temperature=0,
    api_key=OPENAI_API_KEY
)

analysis_llm = ChatOpenAI(
    model="gpt-5.6-luna",
    temperature=0,
    api_key=OPENAI_API_KEY
)

# BRD FR-04: typed entity extraction for downstream deterministic verification.
entity_extractor = clause_llm.with_structured_output(StructuredDocumentEntities)

async def extract_structured_entities(user_doc: str) -> StructuredDocumentEntities:
    messages = [
        ("system", ENTITY_EXTRACTION_SYSTEM_PROMPT),
        ("human", user_doc),
    ]
    return await entity_extractor.ainvoke(messages)
# Step 1: Extract clauses from user's document
clause_extractor = clause_llm.with_structured_output(ExtractedClauses)

async def extract_clauses(user_doc: str):
    messages = [
        ("system", CLAUSE_EXTRACTION_SYSTEM_PROMPT),
        ("human", user_doc)
    ]

    result = await clause_extractor.ainvoke(messages)
    final_clauses = []

    for extracted_clause in result.clauses:
        final_clauses.append({
            "clause_id": extracted_clause.clause_id,
            "clause_type": extracted_clause.clause_type,
            "clause_text": extracted_clause.clause_text
        })

    return final_clauses # list of json obj (clause_id, clause_type, clause_text)

# Step 2: Connect langchain to the existing chromadb

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_db = Chroma(
    collection_name="rbi_source_documents",
    persist_directory="../../storage/vector_db",
    embedding_function=embeddings
)

# Retrieve top N chunks for ONE clause
retriever = vector_db.as_retriever(
    search_kwargs={
        "k": 3
    }
)

# An async function call to retrieve_source_chunks for each clause in all_clauses (parallel)
async def retrieve_source_chunks(clause_text: str):
    loop = asyncio.get_event_loop()

    # run_in_executor allows you to run CPU-bound operations in a separate thread pool, preventing them from blocking the event loop
    result = await loop.run_in_executor(None, retriever.invoke, clause_text)

    docs = []
    for doc in result:
        data = {
            "text_content": doc.page_content,
            "page_number": doc.metadata.get("page")
        }
        docs.append(data)

    return docs

# Parallel chunk retrieval for all clauses - reduces latency - time taken = slowest LLM call for one chunk instead of sum of all calls
async def retrieve_all_chunks(all_clauses: list[ExtractedClause]):
    tasks = [
        retrieve_source_chunks(clause.get("clause_text")) for clause in all_clauses
    ]

    all_results = await asyncio.gather(*tasks)

    all_chunks = []
    for clause, chunks in zip(all_clauses, all_results):
        clause_chunk = {
            "clause_id": clause.get("clause_id"),
            "clause_type": clause.get("clause_type"),
            "clause_text": clause.get("clause_text"),
            "relevant_source_chunks": chunks
        }
        all_chunks.append(clause_chunk)

    return all_chunks


# Clean up the data and build a proper analysis context for LLM analysis
def build_analysis_context(all_clauses_chunks):
    context_parts = []

    for clause_chunks in all_clauses_chunks:
        clause_section = f"""
        User Clause-
        Clause ID: {clause_chunks["clause_id"]}
        Clause Type: {clause_chunks["clause_type"]}
        Clause Text: {clause_chunks["clause_text"]}
        
        Relevant RBI Source Rules-
        """

        source_rules = ""
        for i, doc in enumerate(clause_chunks["relevant_source_chunks"]):
            source_rules += f"""
            Source Rule {i+1}: {doc.get("text_content")}
            Metadata: {doc.get("page_number")}
            """

            context_parts.append(clause_section + source_rules)

    return "\n\n".join(context_parts)

# Step 3: Call LLM
analysis_llm_structured = analysis_llm.with_structured_output(
    ContractAnalysis
)

async def analyze_retrieved_clauses(context: str):
    messages = [
        ("system", CONTRACT_ANALYSIS_SYSTEM_PROMPT),
        ("human", context)
    ]

    response = await analysis_llm_structured.ainvoke(messages)
    return response.final_results
