# Project Rules Generator
> Turn any project's README into intelligent, context-aware agent skills.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-green.svg)](tests/)

## 🎯 What It Does

Turn any project's `README.md` into:
- **rules.md** - Coding standards, DO/DON'T, workflows
- **skills.md** - AI agent capabilities tailored to your project type

No more generic "analyze code" - get skills like:
- `video-processing-optimizer` for ML projects
- `api-endpoint-analyzer` for web apps
- `prompt-optimizer` for AI agents

## ✨ Key Features

- 🧠 **Smart Detection** - Identifies project type (web app, CLI, ML pipeline, agent, library)
- 🎨 **Domain-Specific Skills** - Generates relevant skills, not generic templates
- 🔧 **Dual Interface** - CLI for automation, IDE-agent for interactive use
- 📊 **High Confidence** - Multi-signal detection with confidence scores
- ⚙️ **Configurable** - YAML config for LLM enhancement, git settings
- 🧪 **Tested** - Unit tests + verified on real projects

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/project-rules-generator
cd project-rules-generator
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate for current directory
python main.py .

# Generate for a specific project
python main.py /path/to/your-project

# Interactive mode (confirms findings before generating)
python main.py . --interactive
```

### Example Output

Running on **MediaLens-AI** (video analysis project):
```
Detected: ml_pipeline (confidence: 100%)
```

**Generated Skills:**
- ✅ `video-processing-optimizer` - Tune ffmpeg parameters
- ✅ `broadcast-segmentation-analyzer` - Evaluate scene splitting
- ✅ `embedding-quality-tester` - Improve semantic search
- ✅ `prompt-optimizer` - Enhance AI prompts

## 📦 Project Types Supported

| Type | Detection Signals | Example Skills |
|------|-------------------|----------------|
| **Agent** | LLM APIs (Gemini, OpenAI), orchestration | `prompt-optimizer`, `llm-api-cost-analyzer` |
| **ML Pipeline** | PyTorch, video processing, training | `model-performance-analyzer`, `video-processing-optimizer` |
| **Web App** | FastAPI, React, REST APIs | `api-endpoint-analyzer`, `frontend-backend-sync` |
| **CLI Tool** | Click, argparse, command-line | `command-analyzer`, `cli-test-generator` |
| **Library** | Package structure, no main.py | `api-design-reviewer`, `documentation-sync` |
| **Generator** | Templates, scaffolding | `template-optimizer`, `self-improve` |

## 🎨 How It Works

1. **README Parser**  
   ↓ (extracts name, tech, features)
2. **Project Type Detector**  
   ↓ (AI agent? Web app? ML pipeline?)
3. **Domain Template Selector**  
   ↓ (loads relevant skill templates)
4. **Smart Generator**  
   ↓ (customizes for YOUR project)
5. **Output**: `rules.md` + `skills.md`

## ⚙️ Configuration

Edit `config.yaml` to customize behavior:

```yaml
llm:
  enabled: false  # Enable for deeper analysis via API
  provider: "gemini"  # or "anthropic"

git:
  auto_commit: true
  commit_message: "🤖 Auto-generated project docs"

generation:
  verbose: false
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Test specific detection logic
pytest tests/test_ai_video_detection.py -v

# Run generator on sample project
python main.py tests/test_samples/sample-project
```

## 🔧 IDE Agent Integration

### Antigravity / Claude / Gemini / Cursor
Load skills by prompting:
> "Load skills from {project}-skills.md and help me refactor the API layer"

### OpenClaw
```bash
/skills load medialens-ai-skills.md
```

### Manual
Reference the generated files as context for any AI agent.

## 📊 Real-World Examples

| Project | Detected Type | Skills Generated |
|---------|---------------|------------------|
| **MediaLens-AI** | `ml_pipeline` | `video-processing-optimizer`, `broadcast-segmentation-analyzer` |
| **DevLens-AI** | `cli_tool` | `command-analyzer`, `code-quality-auditor` |
| **Project-Rules-Gen** | `generator` | `readme-deep-analyzer`, `template-optimizer`, `self-improve` |

## 🛠️ Advanced Usage

**Batch Processing**
```bash
# Generate for all projects in a folder
python main.py ~/projects --scan-all
```

**LLM-Enhanced Analysis**
```bash
# Enable Gemini/Claude for deeper README analysis
python main.py . --llm-analyze
```

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feat/amazing-feature`
3. Run tests: `pytest`
4. Commit: `git commit -m "feat: add amazing feature"`
5. Push and open PR

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

Built for developers who work with AI agents and want smarter, project-specific assistance.  
Tested with: **Claude**, **Gemini**, **Cursor**, **Antigravity**, **OpenClaw**.

---
**Project Rules Generator** - Because generic "analyze code" skills aren't enough anymore.
