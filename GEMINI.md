# TradingAgents-CN Gemini Agent Guide

This document provides a guide for the Gemini agent to understand and interact with the TradingAgents-CN project.

## Project Overview

TradingAgents-CN is a Chinese-enhanced version of the original TradingAgents project. It is a multi-agent-based financial trading decision framework that leverages large language models (LLMs). The project is optimized for Chinese users, providing full support for A-shares, Hong Kong stocks, and US stocks.

### Key Features

- **Multi-Agent Architecture:** The framework uses a team of specialized agents, including market analysts, fundamental analysts, news analysts, and social media analysts, to perform comprehensive stock analysis.
- **Multi-LLM Support:** It supports various LLMs, including DeepSeek, Qwen (Alibaba), Google AI (Gemini), and OpenAI models.
- **Comprehensive Data Support:** The project integrates multiple data sources like Tushare, AkShare, and Finnhub to provide real-time and historical data for different stock markets.
- **Web Interface:** A user-friendly web interface built with Streamlit allows users to configure analysis parameters, run analyses, and view reports.
- **Report Generation:** The framework can generate professional analysis reports in various formats, including Markdown, Word, and PDF.
- **Docker and Local Deployment:** The project can be deployed using Docker for a quick and easy setup or locally for development and customization.

## Getting Started

There are two ways to set up the project: Docker deployment (recommended) and local deployment.

### Docker Deployment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hsliuping/TradingAgents-CN.git
    cd TradingAgents-CN
    ```
2.  **Configure environment variables:**
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and fill in your API keys for the desired LLMs.
3.  **Build and start the services:**
    ```bash
    docker-compose up -d --build
    ```
4.  **Access the application:**
    -   Web interface: `http://localhost:8501`
    -   Database management: `http://localhost:8081`
    -   Cache management: `http://localhost:8082`

### Local Deployment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hsliuping/TradingAgents-CN.git
    cd TradingAgents-CN
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv env
    env\Scripts\activate  # Windows
    # source env/bin/activate  # Linux/macOS
    ```
3.  **Install dependencies:**
    ```bash
    pip install -e .
    ```
4.  **Configure environment variables:**
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and fill in your API keys.
5.  **Start the application:**
    ```bash
    python start_web.py
    ```
6.  **Access the application:**
    -   Web interface: `http://localhost:8501`

## Usage

### Web Interface

The web interface provides an intuitive way to interact with the TradingAgents-CN framework.

1.  **Access the web interface:** Open your browser and go to `http://localhost:8501`.
2.  **Configure analysis parameters:**
    -   Select the LLM model you want to use.
    -   Choose the analysis depth (from quick to in-depth).
    -   Select the team of analysts.
3.  **Enter the stock code:** Enter the stock code you want to analyze (e.g., `000001` for A-shares, `AAPL` for US stocks).
4.  **Start the analysis:** Click the "Start Analysis" button.
5.  **View the report:** Once the analysis is complete, you can view the detailed report and export it in your desired format.

### Command-Line Interface (CLI)

The project also provides a CLI for developers and advanced users. You can use the CLI to manage user accounts, configure data directories, and run analyses programmatically.

For more information on the CLI, please refer to the `scripts/` directory and the project's documentation.

## Development

### Contributing

Contributions to the TradingAgents-CN project are welcome. You can contribute by:

-   Reporting bugs and suggesting new features.
-   Fixing bugs and implementing new features.
-   Improving the documentation.
-   Submitting pull requests.

### Project Structure

The project is organized into the following directories:

-   `assets/`: Images and other static assets.
-   `cli/`: Command-line interface.
-   `config/`: Configuration files.
-   `data/`: Data storage.
-   `docs/`: Documentation.
-   `examples/`: Example scripts.
-   `logs/`: Log files.
-   `reports/`: Generated reports.
-   `scripts/`: Utility scripts.
-   `tests/`: Tests.
-   `tradingagents/`: Core application logic.
-   `web/`: Web interface.

For more detailed information about the project, please refer to the `README.md` file and the `docs/` directory.
