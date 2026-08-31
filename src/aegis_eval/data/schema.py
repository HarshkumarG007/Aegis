from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    target_name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    queries = relationship("AdversarialQuery", back_populates="run")

class AdversarialQuery(Base):
    __tablename__ = "adversarial_queries"

    query_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.run_id"))
    attack_type: Mapped[str] = mapped_column(String) # contradiction, out_of_domain, multi_hop, ambiguous
    query_text: Mapped[str] = mapped_column(Text)
    source_chunk_ids: Mapped[str] = mapped_column(Text) # Stored as comma-separated or JSON string for simplicity here
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("EvaluationRun", back_populates="queries")
    response = relationship("TargetResponse", back_populates="query", uselist=False)

class TargetResponse(Base):
    __tablename__ = "target_responses"

    response_id: Mapped[str] = mapped_column(String, ForeignKey("adversarial_queries.query_id"), primary_key=True)
    answer_text: Mapped[str] = mapped_column(Text)
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text) # Stored as comma-separated or JSON string

    query = relationship("AdversarialQuery", back_populates="response")
    verdict = relationship("EvaluationVerdict", back_populates="response", uselist=False)

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
