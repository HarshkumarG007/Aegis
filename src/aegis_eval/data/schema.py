from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Float, Text, JSON, Integer
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

Base = declarative_base()

class BenchmarkManifest(Base):
    __tablename__ = "benchmark_manifests"
    
    manifest_sha256: Mapped[str] = mapped_column(String, primary_key=True)
    benchmark_version: Mapped[str] = mapped_column(String)
    query_set: Mapped[str] = mapped_column(String)
    query_set_sha256: Mapped[str] = mapped_column(String)
    corpus_sha256: Mapped[str] = mapped_column(String)
    models: Mapped[str] = mapped_column(String)
    embedding_model: Mapped[str] = mapped_column(String)
    evaluator_version: Mapped[str] = mapped_column(String)
    code_revision: Mapped[str] = mapped_column(String)
    random_seed: Mapped[int] = mapped_column(Integer)
    retrieval_config: Mapped[dict] = mapped_column(JSON)
    thresholds: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    manifest_sha256: Mapped[str] = mapped_column(String, ForeignKey("benchmark_manifests.manifest_sha256"))
    target_name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    queries = relationship("AdversarialQuery", back_populates="run")

class AdversarialQuery(Base):
    __tablename__ = "adversarial_queries"

    query_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.run_id"))
    attack_type: Mapped[str] = mapped_column(String)
    query_text: Mapped[str] = mapped_column(Text)
    source_chunk_ids: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("EvaluationRun", back_populates="queries")
    response = relationship("TargetResponse", back_populates="query", uselist=False)

class TargetResponse(Base):
    __tablename__ = "target_responses"

    response_id: Mapped[str] = mapped_column(String, ForeignKey("adversarial_queries.query_id"), primary_key=True)
    status: Mapped[str] = mapped_column(String) # SUCCESS, TIMEOUT, HTTP_ERROR, DAEMON_CRASH, MALFORMED
    answer_text: Mapped[str] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    query = relationship("AdversarialQuery", back_populates="response")
    retrieved_chunks = relationship("RetrievedChunk", back_populates="response")
    verdict = relationship("EvaluationVerdict", back_populates="response", uselist=False)

class RetrievedChunk(Base):
    __tablename__ = "retrieved_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    response_id: Mapped[str] = mapped_column(String, ForeignKey("target_responses.response_id"))
    chunk_id: Mapped[str] = mapped_column(String)
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    text_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Store embedding if Vector is available (for V2.1 retrieval metrics)
    if Vector:
        embedding = mapped_column(Vector(384), nullable=True)

    response = relationship("TargetResponse", back_populates="retrieved_chunks")

class EvaluationVerdict(Base):
    __tablename__ = "evaluation_verdicts"

    verdict_id: Mapped[str] = mapped_column(String, primary_key=True)
    response_id: Mapped[str] = mapped_column(String, ForeignKey("target_responses.response_id"))
    mechanism_used: Mapped[str] = mapped_column(String)
    pass_fail: Mapped[bool] = mapped_column(Boolean)
    primary_evidence: Mapped[str] = mapped_column(Text)
    bertscore: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rouge_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    response = relationship("TargetResponse", back_populates="verdict")
    claims = relationship("EvaluationVerdictClaim", back_populates="verdict")

class EvaluationVerdictClaim(Base):
    __tablename__ = "evaluation_verdict_claims"

    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    verdict_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_verdicts.verdict_id"))
    claim_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String) # SUPPORTED, CONTRADICTED, PARTIAL, UNSUPPORTED, ENTAILED, NOT_ENTAILED
    evidence_chunk_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    verdict = relationship("EvaluationVerdict", back_populates="claims")
