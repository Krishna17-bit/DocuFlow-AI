from __future__ import annotations
from typing import Any, TypedDict
from .models import DocumentRecord, PipelineResult, now_iso
from .intelligence import classify_document, chunk_document, extract_fields, validate_documents, create_review_items, parse_rules

class DocFlowState(TypedDict, total=False):
    documents: list[DocumentRecord]
    rules_df: Any
    trace: list[dict[str, Any]]
    chunks: list[Any]
    fields: list[Any]
    findings: list[Any]
    review_items: list[Any]


def _log(state: DocFlowState, node: str, action: str, **details: Any) -> None:
    state.setdefault("trace", [])
    state["trace"].append({"time": now_iso(), "node": node, "action": action, **details})


def _ingest_documents(state: DocFlowState) -> DocFlowState:
    _log(state, "ingest_documents", "received_documents", document_count=len(state.get("documents", []) or [])); return state

def _classify_documents(state: DocFlowState) -> DocFlowState:
    docs = [classify_document(d) for d in state.get("documents", [])]
    state["documents"] = docs; _log(state, "classify_documents", "classified_documents", classified_count=len(docs)); return state

def _extract_tables_placeholder(state: DocFlowState) -> DocFlowState:
    docs = state.get("documents", [])
    _log(state, "extract_tables", "registered_uploaded_tables", table_document_count=len([d for d in docs if d.file_type == "table" or d.table_count > 0])); return state

def _build_chunks(state: DocFlowState) -> DocFlowState:
    chunks = []
    for doc in state.get("documents", []): chunks.extend(chunk_document(doc))
    state["chunks"] = chunks; _log(state, "build_chunks", "created_searchable_chunks", chunk_count=len(chunks)); return state

def _structured_extraction(state: DocFlowState) -> DocFlowState:
    fields = []
    for doc in state.get("documents", []): fields.extend(extract_fields(doc))
    state["fields"] = fields; _log(state, "structured_extraction", "extracted_fields", field_count=len(fields)); return state

def _rule_validation(state: DocFlowState) -> DocFlowState:
    rules = parse_rules(state.get("rules_df"))
    findings = validate_documents(state.get("documents", []), rules)
    state["findings"] = findings; _log(state, "rule_validation", "validated_against_rules", rule_count=len(rules), finding_count=len(findings)); return state

def _human_review(state: DocFlowState) -> DocFlowState:
    items = create_review_items(state.get("documents", []), state.get("fields", []), state.get("findings", []))
    state["review_items"] = items; _log(state, "human_review", "created_review_queue", review_item_count=len(items)); return state

def _export_packaging(state: DocFlowState) -> DocFlowState:
    _log(state, "export_packaging", "prepared_export_state"); return state


def build_docflow_graph():
    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:
        raise RuntimeError("LangGraph is not installed. Run: pip install langgraph langchain-core") from exc
    graph = StateGraph(DocFlowState)
    graph.add_node("ingest_documents", _ingest_documents)
    graph.add_node("classify_documents", _classify_documents)
    graph.add_node("extract_tables", _extract_tables_placeholder)
    graph.add_node("build_chunks", _build_chunks)
    graph.add_node("structured_extraction", _structured_extraction)
    graph.add_node("rule_validation", _rule_validation)
    graph.add_node("human_review", _human_review)
    graph.add_node("export_packaging", _export_packaging)
    graph.set_entry_point("ingest_documents")
    graph.add_edge("ingest_documents", "classify_documents")
    graph.add_edge("classify_documents", "extract_tables")
    graph.add_edge("extract_tables", "build_chunks")
    graph.add_edge("build_chunks", "structured_extraction")
    graph.add_edge("structured_extraction", "rule_validation")
    graph.add_edge("rule_validation", "human_review")
    graph.add_edge("human_review", "export_packaging")
    graph.add_edge("export_packaging", END)
    return graph.compile()


def run_docflow_graph(documents: list[DocumentRecord], rules_df: Any) -> PipelineResult:
    app = build_docflow_graph()
    final = app.invoke({"documents": documents, "rules_df": rules_df, "trace": []})
    return PipelineResult(documents=final.get("documents", []), chunks=final.get("chunks", []), fields=final.get("fields", []), findings=final.get("findings", []), review_items=final.get("review_items", []), trace=final.get("trace", []))
