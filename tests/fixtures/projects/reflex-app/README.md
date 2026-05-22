# My Reflex App

A chat application built with **Reflex** — a Python framework that compiles to React under the hood. Developers write pure Python; the build step transpiles to JavaScript/Next.js in the `.web/` directory.

## Prerequisites

- Python 3.10+
- Node.js 16+ (used internally by Reflex build, not by app code)

## Stack

- Reflex (the framework)
- LangChain + OpenAI (chat backend)
- Groq (low-latency inference)

## Notes for developers

You do not write React, Next.js, or TypeScript in this project. The `.web/`
folder is generated output and must be excluded from analysis. Add it to
`.gitignore` if Reflex hasn't already.
