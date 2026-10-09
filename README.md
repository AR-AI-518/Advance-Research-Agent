# Advance Research Agent

An advanced research-agent application built with a modular architecture. The project separates security, caching, monitoring, and configuration from the agent's memory, tools, planning, pipeline, and FastAPI application.

## Architecture

```text
Advance-Research-Agent/
├── functions/
│   ├── memory.py          # Memory operations for the agent
│   ├── tools.py           # Tools the agent can use during research
│   └── planning.py        # Breaks a research task into steps
├── layers/
│   ├── security.py        # Input/output security checks
│   ├── cashe.py           # Caching layer (filename as currently used)
│   ├── monitring.py       # Logging and monitoring
│   └── config.py          # Application and model settings
├── main/
│   ├── Agent.py           # Final Research Agent
│   ├── pipline.py         # Connects the agent workflow stages
│   └── app.py             # FastAPI application and API endpoints
└── README.md
```

### Request flow

```text
Client
  |
  v
FastAPI App (main/app.py)
  |
  v
Pipeline (main/pipline.py)
  |
  +--> Security (layers/security.py)
  +--> Planning (functions/planning.py)
  +--> Tools (functions/tools.py)
  +--> Memory (functions/memory.py)
  +--> Cache (layers/cashe.py)
  +--> Monitoring (layers/monitring.py)
  +--> Configuration (layers/config.py)
  |
  v
Final Research Agent (main/Agent.py)
  |
  v
Research Response
```

> This diagram shows the intended high-level responsibilities. The exact call order depends on how these modules are connected in the implementation.

## Main Components

| Component | Responsibility |
|---|---|
| **Security** | Applies security checks to help validate or filter requests and responses. |
| **Cache** | Reuses eligible stored results to reduce repeated work and latency. |
| **Monitoring** | Records application activity and helps diagnose errors and performance issues. |
| **Config** | Keeps model and application settings in one place. |
| **Memory** | Manages relevant information used across agent interactions, according to the configured memory strategy. |
| **Tools** | Provides the capabilities the agent can call while researching. |
| **Planning** | Converts a research request into smaller steps. |
| **Research Agent** | Coordinates research and produces the final result. |
| **Pipeline** | Connects the processing stages into one workflow. |
| **FastAPI App** | Exposes the agent through HTTP API endpoints. |

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/AR-AI-518/Advance-Research-Agent.git
   cd Advance-Research-Agent
   ```

2. Create and activate a virtual environment:

   **Windows PowerShell**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies.

   If the project has a `requirements.txt` file:

   ```bash
   pip install -r requirements.txt
   ```

   If it does not, install the dependencies used by your code and create a `requirements.txt` before sharing or deploying the project.

4. Configure environment variables.

   Create a local `.env` file if your configuration uses environment variables. Add the required settings, such as your model-provider API key, using the variable names expected by `layers/config.py`.

   **Never commit `.env` or API keys to GitHub.** Add `.env` to `.gitignore`.

## Run the API

Start the FastAPI app from the repository root, using the import path that matches your project:

```bash
uvicorn main.app:app --reload
```

Then open:

- API documentation: `http://127.0.0.1:8000/docs`
- Alternative API documentation: `http://127.0.0.1:8000/redoc`

If your FastAPI instance has a different variable name or your app is launched from another module, adjust the Uvicorn command accordingly.

## Example Workflow

1. A client sends a research request to the FastAPI endpoint.
2. The pipeline coordinates request processing.
3. Security checks are applied where configured.
4. Planning breaks the research task into steps.
5. The agent uses available tools and memory as needed.
6. The cache may serve a reusable result when applicable.
7. Monitoring records relevant activity and errors.
8. The Research Agent returns the final response through the API.

## Project Status

This README describes the project's high-level structure. Update the component descriptions, environment variables, API examples, and workflow to match the actual implementation as the code evolves.
