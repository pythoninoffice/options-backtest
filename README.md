# Option Backtest

## Description
Option Backtest is a Python-based application designed for backtesting simple trading strategies on options. 

## Features
- Backtesting of simple options trading strategies, including sinlge leg options, strangles and wheels
- Interactive web interface by streamlit

## Installation

### Prerequisites
- Python 3.11 or higher

### Clone the Repository
```bash
git clone https://github.com/pythoninoffice/option_backtest.git
cd option_backtest
```

### Set Up a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage
To run the application, execute the following command:
```bash
streamlit run app.py
```
The application will start.

## Directory Structure
option_backtest/
│
├── app.py # Main application file
├── bt_engine.py # Backtesting engine logic
├── config.py # Configuration settings
├── options.py # Options-related functionalities
├── strategies.py # Trading strategies implementation
└── README.md # Project documentation
 