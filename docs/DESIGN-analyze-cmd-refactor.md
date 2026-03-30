# Design: Decomposing `cli/analyze_cmd.py` into Focused Helper Modules

## Problem Statement
The `cli/analyze_cmd.py` module, currently at 970 Lines of Code (LOC), functions as a monolithic "god-module" handling CLI option parsing, LLM provider instantiation, core generation logic, and result export. This architectural debt severely impacts maintainability, testability, and readability, making future feature development and bug fixes unnecessarily complex and risky.

## Architecture Decisions

- **Module Decomposition Strategy**: Functional Segregation (vs Layered Architecture, Entity-Based Decomposition)
  - Pro: Clear separation of concerns, making each module highly cohesive and loosely coupled.
  - Pro: Significantly improves testability, as individual functions and modules can be unit-tested in isolation.
  - Pro: Enhances readability and maintainability, reducing cognitive load for developers working on specific features.
  - Pro: Facilitates easier onboarding for new team members by providing well-defined boundaries.
  - Con: Requires careful definition of API contracts between the new modules to ensure smooth data flow.
  - Con: Initial refactoring effort will be substantial, requiring thorough regression testing.
- **Configuration Management**: Pydantic Models for Normalized Options (vs Raw Dictionaries, Simple Function Arguments)
  - Pro: Provides strong type hints, enabling static analysis and improving developer experience.
  - Pro: Built-in data validation ensures that all configuration is correct before processing begins, catching errors early.
  - Pro: Centralizes configuration definition, making it easy to understand what options are available and required.
  - Pro: Promotes immutability for configuration objects, reducing side effects and making reasoning about state simpler.
  - Con: Requires defining and maintaining Pydantic models, adding a small amount of boilerplate.
  - Con: Potential for slightly increased memory footprint compared to raw dictionaries, though negligible for configuration objects.
- **LLM Provider Abstraction**: Strategy Pattern with Abstract Base Class (ABC) (vs If/Else Chains, Direct Imports)
  - Pro: Enables easy extension to support new LLM providers without modifying existing core logic (Open/Closed Principle).
  - Pro: Decouples the core analysis pipeline from specific LLM SDK implementations.
  - Pro: Facilitates unit testing of the pipeline logic by allowing mocking of the `LLMProviderInterface`.
  - Pro: Provides a consistent API for interacting with diverse LLM services.
  - Con: Requires an initial design and implementation overhead for the interface and factory.
  - Con: The common interface might need to be broad enough to accommodate varying capabilities across LLMs, potentially leading to some `NotImplementedError` or conditional logic within concrete providers for less common features.

## API Contracts

- `raw_options`: `Dict[str, Any]` - A dictionary containing raw, unvalidated CLI options as parsed by `click`.
- `ValidationError` (from Pydantic): If any `raw_options` fail validation against the `AnalysisOptions` schema.
- `FileNotFoundError`: If `input_path` specified in `raw_options` does not exist.
- `options`: `AnalysisOptions` - The validated analysis options, containing `provider_type`, `model_name`, and `extra_configs`.
- `UnsupportedProviderError`: If `options.provider_type` is not recognized or supported.
- `ProviderInitializationError`: If there's an issue initializing the provider (e.g., missing API key, invalid model).
- `provider`: `LLMProviderInterface` - An initialized LLM provider client.
- `options`: `AnalysisOptions` - The validated analysis options.
- `content`: `str` - The actual code content (or other text) to be analyzed.
- `LLMGenerationError`: If the LLM call fails or returns an unexpected response.
- `ContentProcessingError`: If there's an issue preparing the prompt or post-processing the LLM's response.
- `result`: `AnalysisResult` - The structured output from the analysis pipeline.
- `options`: `AnalysisOptions` - The validated analysis options, specifically `output_path` and `output_format`.
- `ExportError`: If there's an issue writing the output (e.g., permission denied, invalid path).
- `UnsupportedOutputFormatError`: If `options.output_format` is not handled.

## Success Criteria

- **Maintainability**: The `cli/analyze_cmd.py` module's Lines of Code (LOC) must be reduced to less than 100, acting purely as an orchestrator. Each new helper module (`cli/options.py`, `cli/providers.py`, `cli/pipeline.py`, `cli/export.py`) should ideally be less than 300 LOC.
- **Quality**: Unit test coverage for all new helper modules (`cli/options.py`, `cli/providers.py`, `cli/pipeline.py`, `cli/export.py`, `cli/models.py`) must be greater than 90%.
- **Performance**: There should be no measurable regression in the end-to-end execution time of the `analyze` command (within 5% variance) compared to the current implementation for typical workloads.
- **Readability**: All public classes, methods, and functions in the new helper modules must have clear docstrings conforming to a standard (e.g., Google or Sphinx style).
- **Extensibility**: Adding support for a new LLM provider should primarily involve creating one new file (the concrete provider implementation) and making minor modifications to `cli/providers.py` (e.g., adding to a provider registry/factory).
