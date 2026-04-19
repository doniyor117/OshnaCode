# 🛠️ OshnaCode

**OshnaCode** is an elite, tool-augmented AI agent designed for senior-level technical assistance. It doesn't just chat—it operates. With direct filesystem access, terminal execution, and deep code analysis capabilities, Oshna is built to handle complex refactoring, system administration, and project exploration.

## 🚀 Core Capabilities

### 📂 Filesystem Mastery
Oshna can navigate and manipulate your project structure with precision:
- **Atomic Edits**: Uses line-based editing to modify files without overwriting entire documents.
- **Safe Operations**: Implements path validation to prevent directory traversal attacks.
- **Search & Discovery**: Integrated `grep`-like search and directory listing.

### 💻 Terminal & Git Integration
- **Bash Execution**: Can run any non-interactive bash command.
- **Human-in-the-Loop**: For security, all bash commands require explicit user approval before execution.
- **Git Awareness**: Native tools to check `git status` and `git diff`, ensuring changes are reviewed before being finalized.

### 🧠 Advanced Code Analysis
- **Code Skeletonization**: Powered by `tree-sitter`, Oshna can extract the architectural structure (classes, functions, methods) of Python and JavaScript files without reading the entire source, optimizing context window usage.
- **Intelligent Context**: A custom context manager prunes old conversation turns while preserving the integrity of tool-call chains.

### 💾 Session Persistence
- **State Recovery**: All conversations are serialized to JSON in the `conversations/` directory.
- **Seamless Resumption**: Load previous sessions to continue complex tasks without re-explaining the context.

## 🛠️ Tech Stack
- **LLM**: `gemma-4-31b-it` (via Google GenAI)
- **Schema Validation**: `Pydantic` for strict tool input/output typing.
- **Parsing**: `tree-sitter` for multi-language AST analysis.
- **Environment**: Python 3.10+

## ⚙️ Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/doniyor117/OshnaCode
cd OshnaCode
```

### 2. Create Python Environment and Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Note: tree-sitter grammars may need additional installation depending on your OS
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_api_key_here
```

### 4. Run the Agent
```bash
python main.py
```

## 🛡️ Security Note
Oshna has the power to delete files and execute system commands. While the `execute_bash` tool requires manual approval, always review the agent's proposed actions before granting permission.

---
*Built for those who prefer their code clean and their assistants witty.*
