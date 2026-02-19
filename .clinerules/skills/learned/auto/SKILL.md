---
name: auto
description: Automates backend setup and deployment for Slab3D Editor MVP
auto_triggers:
  - keywords: [backend, deploy, setup, slab3d-editor]
    project_signals: [has_fastapi, has_supabase]
tools: [docker, docker-compose, make, render-cli]
---

# Skill: Auto

## Purpose
Automate backend setup and deployment for Slab3D Editor MVP, ensuring a consistent development environment and streamlined deployment process.

## Process

### 1. Install Dependencies
```bash
cd backend
make init
```
This step installs the required dependencies, including FastAPI, ezdxf, and ReportLab.

### 2. Configure Supabase
```bash
# Create a new file .env.supabase with the following content
SUPABASE_URL=your_url
SUPABASE_ANON_KEY=your_anon_key
```
Replace `your_url` and `your_anon_key` with your actual Supabase URL and anonymous key.

### 3. Deploy to Render
```bash
# Create a new file render.json with the following content
{
  "service": {
    "name": "slab3d-editor-backend",
    "buildCommand": "make build",
    "startCommand": "make start"
  }
}
```
This step sets up the Render service configuration for the Slab3D Editor backend.

### 4. Build and Deploy Image
```bash
# Run the following command to build and deploy the image
make deploy
```
This step builds the Docker image and deploys it to Render.

## Output
- A deployed Slab3D Editor backend on Render
- A Docker image for the backend
- A `render.json` file for easy service configuration

## Anti-Patterns

❌ **Manual deployment**: Avoid manually deploying the backend each time, which can lead to errors and inconsistencies. Use automation to streamline the process.

❌ **Outdated dependencies**: Regularly update dependencies to ensure the backend remains secure and functional.

## Tech Stack Notes
This skill uses Docker, Docker Compose, and Render CLI for automation. Make is used for task automation. FastAPI and ezdxf are used for building the backend. Supabase is used for database and authentication.