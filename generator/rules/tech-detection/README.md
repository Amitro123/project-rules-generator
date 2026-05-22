# Tech-Detection Rules

This directory holds **declarative rules** that drive PRG's project_type
reconciliation and tech_stack cleanup. The Python functions in
`generator/project_profile.py` (`reconcile_project_type`,
`apply_tech_cleanup_rules`) are generic — they iterate rule records and
apply whichever match. The per-tech policy lives here as data, not in
branching code.

## Directory layout

```
generator/rules/tech-detection/
├── README.md
├── _schema.md                                 # rule shape, validated at load
├── project-type-precedence/
│   ├── 01-python-api-always.yaml
│   ├── 02-agent-skills-high-confidence.yaml
│   ├── 03-agent-when-structure-unsure.yaml
│   ├── 04-generator-or-webapp-on-fallback.yaml
│   └── 05-any-newer-on-fallback.yaml
└── tech-cleanup/
    ├── 01-strip-gpt.yaml
    ├── 02-strip-jest-when-not-test-framework.yaml
    └── 03-strip-reflex-js-artifacts.yaml
```

Files are loaded in lexicographic order — that's why the leading `NN-`
numeric prefix matters. The first matching precedence rule wins; cleanup
rules apply sequentially.

## Adding a new rule

1. Pick the right subdirectory.
2. Copy an existing file as a starting template (the schema is in
   `_schema.md`).
3. Name your file `NN-short-slug.yaml` where `NN` controls evaluation order.
4. Reload PRG (the loader runs at module import). Tests under
   `tests/test_rule_loader.py` verify your file parses and your predicate
   is reachable.

No Python edits required — that's the whole point.
