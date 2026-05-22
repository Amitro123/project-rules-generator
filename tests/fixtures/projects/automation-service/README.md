# Clone Repository

This is the bug7-replicating README. The repository folder is actually
called `automation-service`, but the first H1 says "Clone Repository"
because the original author wrote setup instructions as the lead heading.

## About

Automation service that ties together Claude (Anthropic), OpenAI, and AWS
S3 to process tickets end-to-end.

## Setup

```bash
git clone https://github.com/example/automation-service
cd automation-service
pip install -r requirements.txt
```

## Stack

- Flask (HTTP layer)
- AWS via boto3 (S3, SQS, Lambda)
- Anthropic Claude (primary LLM)
- OpenAI (fallback)
- Docker (deployment)

## Bug context

Bug7 in `ListOfBugs/`: PRG extracted "Clone Repository" as the project name
because it was the first H1, even though `automation-service` is the actual
folder name. The fix in `_extract_project_name` rejects generic-instruction
slugs and falls back to the directory name.
