"""
RAG (Retrieval-Augmented Generation) related data models for Data Agent V4 Backend
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class DocumentStatus(str, Enum):
    """Document processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INDEXING = "indexing"
    INDEXED = "indexed"


class ChunkingStrategy(str, Enum):
    """Document chunking strategy enumeration"""
    SEMANTIC = "semantic"
    FIXED_SIZE = "fixed_size"
    OVERLAP = "overlap"
    STRUCTURED = "structured"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"


class RetrievalMode(str, Enum):
    """Retrieval mode enumeration"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    EXACT = "exact"


class ProcessingStep(str, Enum):
    """RAG processing step enumeration"""
    QUERY_EMBEDDING = "query_embedding"
    SIMILARITY_SEARCH = "similarity_search"
    RESULT_FILTERING = "result_filtering"
    CONTEXT_BUILDING = "context_building"
    ANSWER_GENERATION = "answer_generation"


class DocumentChunk(BaseModel):
    """Document chunk model for RAG processing"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Chunk unique identifier")
    document_id: int = Field(..., description="Parent document ID")
    tenant_id: str = Field(..., description="Tenant ID for isolation")
    chunk_index: int = Field(..., description="Sequential chunk index within document")
    content: str = Field(..., description="Chunk text content")
    content_length: int = Field(..., description="Content character length")
    token_count: Optional[int] = Field(None, description="Estimated token count")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_id: Optional[str] = Field(None, description="Embedding vector ID in ChromaDB")

    # Metadata
    file_name: str = Field(..., description="Source file name")
    file_type: str = Field(..., description="File type (pdf, docx, etc.)")
    page_number: Optional[int] = Field(None, description="Page number (for PDF)")
    chapter_title: Optional[str] = Field(None, description="Chapter or section title")
    paragraph_index: Optional[int] = Field(None, description="Paragraph index")
    sentence_index: Optional[int] = Field(None, description="Sentence index")

    # Chunking metadata
    chunking_strategy: ChunkingStrategy = Field(..., description="Strategy used for chunking")
    chunk_size: int = Field(..., description="Target chunk size")
    overlap_size: int = Field(default=0, description="Overlap size with previous/next chunk")
    semantic_score: Optional[float] = Field(None, description="Semantic coherence score")

    # Processing timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")

    # Quality metrics
    quality_score: Optional[float] = Field(None, description="Content quality score (0-1)")
    relevance_score: Optional[float] = Field(None, description="Domain relevance score")

    class Config:
        from_attributes = True


class VectorCollection(BaseModel):
    """Vector collection management model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Collection unique identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    name: str = Field(..., description="Collection name")
    display_name: str = Field(..., description="Human-readable collection name")
    description: Optional[str] = Field(None, description="Collection description")

    # ChromaDB integration
    chroma_collection_id: str = Field(..., description="ChromaDB collection ID")
    embedding_model: str = Field(default="zhipu-embedding", description="Embedding model used")
    embedding_dimension: int = Field(default=1024, description="Embedding vector dimension")

    # Collection statistics
    document_count: int = Field(default=0, description="Number of documents in collection")
    chunk_count: int = Field(default=0, description="Number of chunks in collection")
    total_tokens: int = Field(default=0, description="Total tokens in collection")

    # Configuration
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.SEMANTIC, description="Default chunking strategy")
    chunk_size: int = Field(default=512, description="Default chunk size")
    overlap_ratio: float = Field(default=0.2, description="Default overlap ratio")

    # Status and management
    is_active: bool = Field(default=True, description="Whether collection is active")
    is_public: bool = Field(default=False, description="Whether collection is public within tenant")
    auto_index: bool = Field(default=True, description="Whether to automatically index new documents")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_indexed: Optional[datetime] = Field(None, description="Last indexing timestamp")

    class Config:
        from_attributes = True


class RetrievalSession(BaseModel):
    """Multi-turn conversation session model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session unique identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: Optional[str] = Field(None, description="User ID (if available)")
    session_name: Optional[str] = Field(None, description="Session name or title")

    # Session configuration
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.SEMANTIC, description="Default retrieval mode")
    max_context_chunks: int = Field(default=5, description="Maximum context chunks per query")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity threshold")
    collections: List[str] = Field(default_factory=list, description="Target collection IDs")

    # Session statistics
    query_count: int = Field(default=0, description="Number of queries in session")
    total_retrieved_chunks: int = Field(default=0, description="Total chunks retrieved")
    average_response_time_ms: float = Field(default=0.0, description="Average response time")

    # Session management
    is_active: bool = Field(default=True, description="Whether session is active")
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    last_query_at: Optional[datetime] = Field(None, description="Last query timestamp")

    class Config:
        from_attributes = True


class RetrievalEntry(BaseModel):
    """Individual retrieval entry within a session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Entry unique identifier")
    session_id: str = Field(..., description="Parent session ID")
    tenant_id: str = Field(..., description="Tenant ID")
    query_index: int = Field(..., description="Query index within session")

    # Query information
    original_query: str = Field(..., description="Original user query")
    processed_query: Optional[str] = Field(None, description="Processed/cleaned query")
    query_embedding: Optional[List[float]] = Field(None, description="Query vector embedding")
    retrieval_mode: RetrievalMode = Field(..., description="Retrieval mode used")

    # Retrieval results
    retrieved_chunks: List[str] = Field(default_factory=list, description="Retrieved chunk IDs")
    retrieval_scores: List[float] = Field(default_factory=list, description="Retrieval scores")
    context_used: List[str] = Field(default_factory=list, description="Actually used chunk IDs in context")

    # Generated response
    generated_answer: Optional[str] = Field(None, description="Generated answer")
    answer_confidence: Optional[float] = Field(None, description="Answer confidence score")
    sources_cited: List[str] = Field(default_factory=list, description="Source document references")

    # Performance metrics
    retrieval_time_ms: int = Field(default=0, description="Retrieval processing time")
    generation_time_ms: int = Field(default=0, description="Answer generation time")
    total_time_ms: int = Field(default=0, description="Total processing time")

    # Quality metrics
    relevance_score: Optional[float] = Field(None, description="Query-relevance score")
    user_feedback: Optional[int] = Field(None, description="User feedback rating (1-5)")
    user_correction: Optional[str] = Field(None, description="User correction or feedback")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True


class RetrievalLog(BaseModel):
    """RAG retrieval processing log for auditing and debugging"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Log unique identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    session_id: Optional[str] = Field(None, description="Session ID (if applicable)")
    entry_id: Optional[str] = Field(None, description="Retrieval entry ID")

    # Processing information
    processing_step: ProcessingStep = Field(..., description="Processing step")
    operation_type: str = Field(..., description="Operation type")
    status: str = Field(..., description="Operation status (success, error, warning)")

    # Input/Output data
    input_data: Optional[Dict[str, Any]] = Field(None, description="Input parameters and data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output results")
    error_message: Optional[str] = Field(None, description="Error message if any")

    # Performance metrics
    execution_time_ms: int = Field(default=0, description="Execution time in milliseconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    tokens_processed: Optional[int] = Field(None, description="Number of tokens processed")

    # Configuration snapshot
    config_snapshot: Optional[Dict[str, Any]] = Field(None, description="Relevant configuration at time of processing")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")

    class Config:
        from_attributes = True


class EmbeddingCache(BaseModel):
    """Embedding cache model for performance optimization"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Cache entry unique identifier")
    tenant_id: str = Field(..., description="Tenant ID")

    # Cache key
    content_hash: str = Field(..., description="SHA-256 hash of original content")
    content_preview: str = Field(..., description="First 100 characters of content")

    # Embedding data
    embedding: List[float] = Field(..., description="Cached embedding vector")
    embedding_model: str = Field(..., description="Embedding model used")
    embedding_dimension: int = Field(..., description="Embedding vector dimension")

    # Cache metadata
    content_length: int = Field(..., description="Original content length")
    token_count: int = Field(..., description="Estimated token count")
    compute_time_ms: int = Field(default=0, description="Original computation time")

    # Cache management
    hit_count: int = Field(default=0, description="Number of cache hits")
    last_hit_at: Optional[datetime] = Field(None, description="Last cache hit timestamp")
    expires_at: Optional[datetime] = Field(None, description="Cache expiration time")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True


class RetrievalResult(BaseModel):
    """Individual retrieval result model"""
    chunk_id: str = Field(..., description="Retrieved chunk ID")
    content: str = Field(..., description="Chunk content")
    content_preview: str = Field(..., description="Content preview (first 200 chars)")

    # Source information
    document_id: int = Field(..., description="Source document ID")
    document_title: str = Field(..., description="Source document title")
    file_name: str = Field(..., description="Source file name")
    file_type: str = Field(..., description="Source file type")
    page_number: Optional[int] = Field(None, description="Page number (if applicable)")
    chapter_title: Optional[str] = Field(None, description="Chapter or section title")

    # Retrieval metrics
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")
    rank: int = Field(..., description="Rank in retrieval results")

    # Content metadata
    content_length: int = Field(..., description="Content character length")
    token_count: Optional[int] = Field(None, description="Estimated token count")
    chunk_index: int = Field(..., description="Chunk index within document")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Content tags")

    class Config:
        from_attributes = True


class RAGQueryRequest(BaseModel):
    """RAG query request model"""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    tenant_id: str = Field(..., description="Tenant ID")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")

    # Retrieval configuration
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.SEMANTIC, description="Retrieval mode")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum retrieval results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    collections: List[str] = Field(default_factory=list, description="Target collection IDs (empty = all)")

    # Context configuration
    max_context_tokens: int = Field(default=2000, ge=100, le=8000, description="Maximum context tokens")
    include_metadata: bool = Field(default=True, description="Include source metadata in response")

    # Response configuration
    generate_answer: bool = Field(default=True, description="Whether to generate LLM answer")
    answer_style: str = Field(default="concise", description="Answer style (concise, detailed, creative)")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature for generation")

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class RAGQueryResponse(BaseModel):
    """RAG query response model"""
    success: bool = Field(..., description="Query processing success status")
    query: str = Field(..., description="Original query")
    tenant_id: str = Field(..., description="Tenant ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    entry_id: Optional[str] = Field(None, description="Retrieval entry ID")

    # Retrieval results
    retrieval_results: List[RetrievalResult] = Field(default_factory=list, description="Retrieved chunks")
    total_retrieved: int = Field(default=0, description="Total chunks retrieved")
    retrieval_time_ms: int = Field(default=0, description="Retrieval processing time")

    # Generated answer
    answer: Optional[str] = Field(None, description="Generated answer")
    answer_confidence: Optional[float] = Field(None, description="Answer confidence score")
    generation_time_ms: int = Field(default=0, description="Answer generation time")

    # Context information
    context_used: List[str] = Field(default_factory=list, description="Chunk IDs used in context")
    context_length: int = Field(default=0, description="Context character length")
    context_tokens: int = Field(default=0, description="Estimated context tokens")

    # Processing information
    processing_steps: List[str] = Field(default_factory=list, description="Processing steps taken")
    total_time_ms: int = Field(default=0, description="Total processing time")
    collections_searched: List[str] = Field(default_factory=list, description="Collections searched")

    # Quality metrics
    average_relevance: Optional[float] = Field(None, description="Average relevance score")
    query_understanding: Optional[str] = Field(None, description="Query understanding explanation")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        from_attributes = True


class RAGStats(BaseModel):
    """RAG processing statistics model"""
    tenant_id: str = Field(..., description="Tenant ID")

    # Document statistics
    total_documents: int = Field(default=0, description="Total documents processed")
    indexed_documents: int = Field(default=0, description="Successfully indexed documents")
    failed_documents: int = Field(default=0, description="Failed document processing")
    total_chunks: int = Field(default=0, description="Total chunks generated")

    # Query statistics
    total_queries: int = Field(default=0, description="Total queries processed")
    successful_queries: int = Field(default=0, description="Successful queries")
    failed_queries: int = Field(default=0, description="Failed queries")
    average_retrieval_time_ms: float = Field(default=0.0, description="Average retrieval time")
    average_generation_time_ms: float = Field(default=0.0, description="Average generation time")

    # Quality metrics
    average_relevance_score: float = Field(default=0.0, description="Average retrieval relevance score")
    average_answer_confidence: float = Field(default=0.0, description="Average answer confidence score")
    user_satisfaction_score: float = Field(default=0.0, description="Average user satisfaction score")

    # Usage statistics
    total_tokens_processed: int = Field(default=0, description="Total tokens processed")
    total_embeddings_generated: int = Field(default=0, description="Total embeddings generated")
    cache_hit_rate: float = Field(default=0.0, description="Embedding cache hit rate")

    # Collection statistics
    active_collections: int = Field(default=0, description="Active collections")
    total_retrieval_sessions: int = Field(default=0, description="Total retrieval sessions")
    active_sessions: int = Field(default=0, description="Currently active sessions")

    # Performance metrics
    peak_queries_per_minute: int = Field(default=0, description="Peak queries per minute")
    average_queries_per_hour: float = Field(default=0.0, description="Average queries per hour")
    system_load_average: float = Field(default=0.0, description="System load average")

    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    statistics_period_days: int = Field(default=30, description="Statistics period in days")

    class Config:
        from_attributes = True