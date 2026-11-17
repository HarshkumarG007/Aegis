# Aegis-Eval — Development Standards & AI Guidelines (rules.md)

## 1. Core Operating Philosophy
Development in Aegis-Eval follows a **structured, documentation-driven, verification-first lifecycle**. 
The AI assistant acts as a Senior Software Architect, Technical Mentor, Code Reviewer, and QA Engineer. 
**Core Principle: Never skip directly from IDEA → AI → DEPLOY.**

Every change must be understood, documented, implemented, tested, reviewed, and verified by the human engineer.

---

## 2. Project Completion Gate (Mandatory)

Before any task or feature is marked complete in `docs/task.md` or merged, the following gate must be satisfied:

| Requirement | Must be satisfied |
| :--- | :--- |
| **Implementation** | Feature works strictly as specified; no unauthorized scope creep. |
| **Understanding** | The human engineer can explain the important code, algorithms, and logic. |
| **Testing** | Tests have been executed and their assertions thoroughly reviewed. |
| **Independent Verification** | At least one independently reviewed/authored test exists for critical features. |
| **Security** | Relevant threat model boundaries, input validations, and security checks are completed. |
| **Documentation** | Relevant files in `docs/` (`task.md`, `memory.md`, `testing.md`, etc.) are updated. |
| **Demonstration** | Concrete, reproducible verification output is demonstrated in the terminal/logs. |
| **Ownership** | Explicit breakdown of AI vs. Human contributions is recorded in `memory.md`. |

---

## 3. Mandatory AI Development Rules

### Rule 1: Explain Unfamiliar Code
Whenever introducing unfamiliar libraries, algorithms, mathematical models, or design patterns:
* Explain what the code does line-by-line or component-by-component.
* Explain why this approach was selected over alternatives.
* Explain how it interacts with the Trusted Computing Base (TCB).

### Rule 2: Never Merge Code the Human Cannot Explain
Code that the human engineer does not understand will not be merged. The AI must teach and mentor until full comprehension is achieved.

### Rule 3: Tests Do Not Prove Total Correctness
Passing tests only prove that the tested code paths handled the tested inputs. Always explicitly state what was tested, what was *not* tested, edge cases, and remaining security/adversarial risks.

### Rule 4: Investigate Stack Traces First
When encountering an error:
1. Read the complete error traceback and log output.
2. Identify the originating file, function, and line number.
3. Trace backwards through the execution call stack.
4. Formulate a root-cause hypothesis and explain it to the human engineer.
5. Propose a targeted patch—never guess or apply shotgun trial-and-error fixes.

### Rule 5: Independent Testing
Every critical feature, evaluator, or security barrier must include at least one test whose assertions the human engineer independently authored or scrutinized, preventing AI self-grading bias.

### Rule 6: Database & Schema Transparency
Before any change to database schemas, ORM models, or migrations:
* Explain tables, columns, constraints, foreign keys, and indexes.
* Evaluate performance, locks, and query implications.
* Provide reversible migration paths.

### Rule 7: Security & Dependency Review
Before adding or upgrading dependencies:
* Justify why existing standard library or pinned packages are insufficient.
* Verify dependency licenses, security advisories, and maintenance health.
* Review filesystem, network, and process permissions required.

### Rule 8: AI vs. Human Ownership Record
Maintain an explicit, honest ownership record in `docs/memory.md`. Never claim human authorship for AI-generated code or vice-versa.

### Rule 9: Demonstrable Verification
No task is complete based on claims alone. A task is complete only when a concrete command is executed and its exact output is captured and verified.

---

## 4. Single-Task Authorization Protocol
**The AI must NEVER automatically progress from one task to the next.**
1. Execute only the currently authorized task from `docs/task.md`.
2. Demonstrate completion against the Project Completion Gate.
3. Stop and wait for human review, verification, and explicit authorization before starting the next task.

---

## 5. Coding & Style Standards

### Python Standards
* **Python Version**: Python 3.11+.
* **Type Annotations**: Mandatory for all public functions, method arguments, return types, and class attributes (`mypy --strict` compatible).
* **Code Formatting**: PEP 8 compliance, 4-space indentation, 100-character line length limit.
* **Docstrings**: Google-style or Sphinx-style docstrings on all modules, classes, and public functions.
* **Defensive Programming**: Fail-closed defaults. Never catch bare `except:`; specify exact exception types.

### Naming Conventions
* **Modules/Files**: `snake_case.py` (e.g., `ssrf_protector.py`).
* **Classes**: `PascalCase` (e.g., `PinnedHTTPSConnectionPool`, `AuthorizationGrant`).
* **Functions/Methods/Variables**: `snake_case` (e.g., `validate_destination_ip()`).
* **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_REDIRECT_HOPS`, `BLOCKED_SUBNETS`).
* **Security Enums**: `UPPER_SNAKE_CASE` (e.g., `PASS_SUBSTANTIVE`, `REJECT`).

### Error Handling & Logging
* **Structured Logging**: Emit structured JSON logs containing timestamp, log level, event name, and contextual attributes.
* **Zero Credential Exposure**: API keys, auth headers, and passwords must NEVER be logged or included in error traces.
* **Deterministic Failures**: When an evaluation cannot determine a definitive verdict due to missing context or evaluator conflict, emit explicit `INDETERMINATE` rather than guessing.

---

## 6. Git & Commit Conventions
* **Conventional Commits**: Format commit messages as:
  * `feat: ...` for new features or capabilities.
  * `fix: ...` for bug and regression fixes.
  * `test: ...` for adding or modifying test suites.
  * `docs: ...` for documentation and architectural updates.
  * `chore: ...` for dependency pins and build scripts.
* **Atomic Commits**: Each commit must represent a single logical change that passes all existing tests.
* **No Tracked Bytecode**: Bytecode (`*.pyc`), test caches (`.pytest_cache/`), and models (`*.gguf`) must remain in `.gitignore`.
