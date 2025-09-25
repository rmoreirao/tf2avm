Below is a **high-level technical specification** (in Markdown) for implementing your multi-agent Terraform → AVM migration system using **LangGraph**. It is a first, minimal version. It uses Python, follows GenAI best practices (e.g. Pydantic for schemas), and leans on LangGraph’s workflow/agent abstractions (incl. orchestrator-worker model) per their documentation (e.g. orchestrator patterns) ([LangChain][1]).

---

# Technical Spec: LangGraph-based Multi-Agent AVM Migration System

## 1. Architecture & Design Goals

* Use **LangGraph** to build a workflow graph with an **Orchestrator** plus specialized **worker agents** (scanning, mapping, conversion, validation, review).
* Keep versioning and structured outputs via **Pydantic models**.
* Support **human-in-the-loop** approval steps via LangGraph’s persistence / gating (pause + resume) features. ([LangChain][1])
* Provide **observability**, logs, and simple retry semantics.
* Use Python idioms, dependency injection, modular design, testability.

---

## 2. Key Components & Modules

* `agents/` — module containing each agent’s logic (RepoScanner, AVMKnowledge, Mapping, Converter, Validator, Reviewer)
* `schemas/` — Pydantic schemas for inputs/outputs between agents
* `orchestrator/` — LangGraph workflow definition wiring agents
* `tools/` — utility functions (HCL parsing, Git operations, Terraform CLI wrappers)
* `config/` — config, constants, AVM index endpoints, logging setup
* `main.py` (or `run_workflow.py`) — entrypoint to trigger migration workflow

---

## 3. Data Schemas (Pydantic)

Example schemas to define:

```python
from pydantic import BaseModel
from typing import List, Optional

class RepoInput(BaseModel):
    repo_url: str

class FileManifest(BaseModel):
    path: str
    resources: List[dict]  # e.g. {"type": str, "name": str}

class RepoManifest(BaseModel):
    files: List[FileManifest]
    variables: List[dict]
    outputs: List[dict]
    providers: List[str]
    terraform_version: Optional[str]

class AVMIndexEntry(BaseModel):
    resource_type: str
    avm_module: str
    version: str

class AVMIndex(BaseModel):
    entries: List[AVMIndexEntry]

class MappingEntry(BaseModel):
    original: str
    mapped_to: Optional[str]
    confidence: float

class MappingResult(BaseModel):
    mappings: List[MappingEntry]
    unmapped: List[str]

class ConversionResult(BaseModel):
    converted_repo_path: str
    files_converted: List[str]

class ValidationErrorItem(BaseModel):
    tool: str
    message: str

class ValidationResult(BaseModel):
    status: str  # "success" or "failed"
    errors: List[ValidationErrorItem]
    warnings: List[str]

class ReviewReport(BaseModel):
    markdown: str
```

These schemas will be the interface between agents and ensure type safety / clarity.

---

## 4. LangGraph Workflow / Orchestration

### 4.1 Orchestrator-Worker Model (LangGraph)

* The Orchestrator node produces a plan and then **sends tasks** to workers; workers write results to a shared key.
* After workers finish, the orchestrator synthesizes final outputs.


### 4.2 Human-in-the-Loop Gates

* In the Review phase, if certain confidence thresholds fail or high-risk flags exist, pause workflow and present the report for human review before finalizing.
* Use LangGraph persistence / gating to suspend and resume workflow. ([LangChain][1])

---

## 5. Agents’ Responsibilities (High Level)

| Agent        | Responsibility                                 
| ------------ | ---------------------------------------------- 
| RepoScanner  | Clone repo, parse HCL, build manifest          
| AVMKnowledge | Fetch AVM index, docs                          
| Mapping      | For each resource/file, propose mapping to AVM 
| Converter    | Rewrite `.tf` files using mappings             
| Validator    | Run validation + lint on converted repo        
| Reviewer     | Generate final report / human review gate      

* Agents must accept and return data in the Pydantic schema forms.

---

## 6. Workflow Sketch (Mermaid-style in MD)

```mermaid
flowchart TD
  start((Start))
  start --> orchestrator[Orchestrator Node]

  orchestrator --> scanner[RepoScanner]
  scanner --> orchestrator

  orchestrator --> avm_knowledge[AVMKnowledge]
  avm_knowledge --> orchestrator

  orchestrator --> mapping_phase{Mapping Phase}
  mapping_phase --> |Send per-file| mapping_worker1[MappingWorker]
  mapping_phase --> |Send per-file| mapping_worker2[MappingWorker]
  mapping_worker1 --> orchestrator
  mapping_worker2 --> orchestrator

  orchestrator --> conversion_phase{Conversion Phase}
  conversion_phase --> |Send per-file| converter_worker1[ConverterWorker]
  conversion_phase --> |Send per-file| converter_worker2[ConverterWorker]
  converter_worker1 --> orchestrator
  converter_worker2 --> orchestrator

  orchestrator --> validator[Validator]
  validator --> orchestrator

  orchestrator --> reviewer[Reviewer]
  reviewer --> orchestrator

  orchestrator --> stop((End))
```

* The **Orchestrator** node dynamically uses `Send` for mapping & conversion workers, then collects results and sequences the rest.

---

## 7. Execution Flow (Step by Step)

1. **Entry**: node `orchestrator` invoked with `RepoInput`.
2. **RepoScanner**: called by orchestrator, outputs `RepoManifest`.
3. **AVMKnowledge**: invoked with query on resource types, yields `AVMIndex`.
4. **Mapping Phase**: orchestrator sends **per-file mapping jobs** to `MappingWorker` tasks, aggregate into `MappingResult`.
5. **Conversion Phase**: orchestrator sends **per-file conversion jobs** to `ConverterWorker` tasks, producing `ConversionResult`.
6. **Validation**: run global validation (Terraform validate, lint) on converted repo.
7. **Review & Gate**: produce `ReviewReport`. If critical issues, pause for human approval.
8. **Return final outcome**: either path to converted repo or report.

---

## 8. Development Best Practices & Notes

* Use **dependency injection** (e.g. pass tools, config into agents) so logic is testable.
* Agents should be small, single-purpose functions (or `@task` nodes).
* Log structured entries (JSON) at each agent step for observability.
* Validate Pydantic models at the boundaries between agents.
* Provide fallback behavior / graceful error handling (timeouts, retries).

## 9. Python Dependencies & `requirements.txt`

The project uses a Python environment (>=3.10 recommended) with the following core dependencies. A generated `requirements.txt` should live at the repository root and be kept in sync when new libraries are introduced. Where possible, versions are pinned with compatible-release operators (`~=`) to balance stability and updates.

### External (Non-Python) Tooling Prerequisites

The following executables must be available on the PATH for the Validator agent:

* Terraform CLI (>=1.6)
* `tflint`
* `checkov`

These are intentionally not inside `requirements.txt` because they are installed via native package managers (e.g., `choco`, `brew`, `apt`) or their own installers.

### Dependency Management Notes

* For local iterative development, you may optionally adopt `uv` or `pip-tools` for lockfile generation; this is out-of-scope for the initial minimal spec.
* If GPU or alternative inference backends are introduced later (e.g., local models), add conditional extras (e.g., `transformers`, `accelerate`).
* Keep import usage minimal inside agents to make unit testing easier (allowing selective dependency injection / mocking).
