# Design: Refactoring God Modules for Improved Modularity and Maintainability

## Problem Statement
The existing `rules_creator.py`, `agent.py`, and sections of `analyze_cmd.py` have grown into monolithic "god modules," leading to high coupling, low cohesion, poor testability, and increased cognitive load for developers. This refactoring aims to decompose these modules into smaller, single-responsibility units, thereby enhancing maintainability, testability, and extensibility of the CLI application.

## Architecture Decisions

- **Modularity and Decomposition Strategy**: Service-Oriented Decomposition with Layered Architecture (vs. purely functional decomposition, monolithic classes with many methods)
- **LLM Interaction Abstraction**: Strategy Pattern with a Unified `LLMClient` Interface (vs. direct SDK calls, single wrapper function with if/else)
- **Configuration Management**: Pydantic `BaseSettings` (vs. global dictionaries, `os.environ.get()` everywhere)
- **Prompt Management**: Externalized Prompt Templates (vs. hardcoded strings, database storage)

## API Contracts

- `messages`: A list of dictionaries, each with "role" (e.g., "system", "user", "assistant") and "content" fields.
- `config`: An `LLMConfig` instance specifying the provider, model, API key, and generation parameters.
- `LLMAPIError`: If there's an issue communicating with the LLM API (e.g., network error, invalid API key, rate limit).
- `LLMProviderNotImplementedError`: If the specified `LLMConfig.provider` does not have a concrete `LLMClient` implementation.
- `context`: A string describing the overall context or domain for which rules are needed (e.g., "Python web application security").
- `requirements`: A list of specific requirements or areas to focus on for rule generation (e.g., ["SQL injection", "XSS", "dependency vulnerabilities"]).
- `llm_config`: An `LLMConfig` instance to use for the underlying LLM calls.
- `RuleGenerationError`: If the LLM fails to generate valid rules or the output cannot be parsed into `GeneratedRule` models.
- `LLMAPIError`: Propagated from `LLMClient` if LLM interaction fails.
- `project_path`: A `pathlib.Path` object pointing to the root directory of the project to be analyzed.
- `llm_config`: An `LLMConfig` instance to use for any LLM interactions during the analysis.
- `ProjectAnalysisError`: If the project path is invalid, or an internal analysis step fails.
- `RuleGenerationError`, `LLMAPIError`: Propagated from underlying services.

## Success Criteria

- **Code Modularity**:
- **Testability**:
- **Maintainability**:
- **Reliability**:
