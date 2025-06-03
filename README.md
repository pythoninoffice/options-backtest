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

### Download Data
Option chain data is required for backtesting. Below is the link to download SPY EOD option chain from 2019 to 2024.
https://drive.google.com/file/d/1o_SGPxqcNz6PkPX34ZdJL3BYZfcjLY57/view?usp=drive_link


## Usage
To run the application, first download the data, then update the `DB_PATH` variable in `config.py` with the path to the downloaded data file.
```bash
DB_PATH = r'path_to_data\spy_2019_2024.db'

```

execute the following command:
```bash
streamlit run app.py
```
The application will start.