# Workshop Setup 🚀

Completing this setup before the workshop ensures we can dive straight into coding without install delays.

> ⚠️ **Please complete this setup on your own computer** — not in a cloud environment like GitHub Codespaces or Google Colab. In past workshops, students using cloud environments ran into problems that prevented them from completing the exercises.

## Prerequisites

Start by making sure you have the following software installed:

- **Git:** https://git-scm.com/downloads  
- **`uv` (package manager):** https://docs.astral.sh/uv/getting-started/installation/  
  Used to manage project dependencies and ensure consistent Python versions. After installing `uv`, restart the terminal.
- **Code editor:** Any editor is fine. I personally use VS Code: https://code.visualstudio.com/download  

## Step 1: Clone the course repo

Run: 
```sh 
git clone https://github.com/arilamstein/streamlit-workshop.git
cd streamlit-workshop
```

## Step 2: Create the course virtual environment

Run:
```sh
uv sync
```

This creates `.venv` and installs all dependencies pinned for the workshop.

## Step 3: Activate the virtual environment

Use the command for your OS/shell:

- Mac/Linux:  `source .venv/bin/activate`
- Windows (Command Prompt):  `.venv\Scripts\activate`
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (Git Bash / MINGW64): `source .venv/Scripts/activate`

Verify:
- Run `python --version` → should report a version starting with **Python 3.13**
- Run `which python` (Mac/Linux) or `where python` (Windows) → should show a path inside `.venv`

## Step 4: Open the workbook

In your terminal, run:
```sh
jupyter notebook workbook.ipynb
```

This should open a browser tab with the course workbook. Follow the instructions there to complete Exercise 1.1.

After you complete Exercise 1.1, the setup is complete 🎉

If you hit any issues, reach out in the course chat.