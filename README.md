# uvpy.run

**uvpy.run** is a remote Python script execution platform that hosts a curated collection of standalone Python tools designed to be executed directly from URLs using [UV](https://github.com/astral-sh/uv) (Ultra-fast Python package installer and resolver).

## ✨ Features

- **🚀 URL-based execution**: Run Python scripts directly from URLs (downloaded and executed locally)
- **📦 Automatic dependencies**: [PEP 723](https://peps.python.org/pep-0723/) metadata handles package installation automatically
- **⚡ Ultra-fast**: UV's Rust-based implementation for lightning-fast execution
- **🔒 Isolated environments**: Each script runs in its own isolated environment
- **🛠️ Zero setup**: No virtual environment management needed
- **🌐 Remote accessibility**: Access tools from anywhere with just a URL

## 🎯 How It Works

Thanks to **PEP 723** (Inline script metadata), each Python script contains its own dependency specifications, making them completely self-contained and executable without manual environment setup.

## 🚀 Quick Start

### Prerequisites

Install UV if you haven't already:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Running Scripts

You can run any Python script from uvpy.run directly:

```bash
# Basic syntax
uv run https://uvpy.run/script_name.py

# Example: Run a password generator
uv run https://uvpy.run/passwordgen.py

# Example: Generate a QR code
uv run https://uvpy.run/qr.py --help
```

Each tool includes built-in help - try adding `--help` to see available options.

## 📚 Available Tools

The platform hosts various Python tools in categories like:
- **Utilities**: Password generators, QR code creators
- **Development**: Flask secret generators, terminal tools
- **Games**: Snake game, Brick breaker
- **Image Processing**: Image translation and processing tools
- **Network**: Proxy IP tools
- **And more...**

Visit [uvpy.run](https://uvpy.run) to browse the complete collection with descriptions, usage examples, and one-click copy commands.

## 🔧 Development

This platform is built with:
- **Flask**: Web framework for serving the tools
- **UV**: Python package manager for script execution
- **PEP 723**: Inline script metadata standard

### Project Structure
```
uvpy_run/
├── main.py              # Flask application
├── static_pyfiles/      # Python tools collection
├── templates/           # HTML templates
├── static/              # Static assets (favicon, etc.)
└── README.md           # This file
```

## ⚠️ Security Notice

**Running remote scripts can pose security risks.** Please review the source code of any script before execution. By using these tools, you acknowledge that you run them at your own risk and responsibility. The platform maintainer is not liable for any damage or security issues that may arise from script execution.

## 🤝 Contributing

We welcome contributions! If you have a useful Python tool that follows PEP 723 standards, feel free to submit it to our collection.

## 📄 License

This project is open source. Individual tools may have their own licenses - please check each script for specific licensing information.

---

**uvpy.run** - Execute Python scripts remotely with confidence
Powered by [UV](https://github.com/astral-sh/uv) + [PEP 723](https://peps.python.org/pep-0723/)
