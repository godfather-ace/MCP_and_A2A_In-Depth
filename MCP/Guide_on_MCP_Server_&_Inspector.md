# 🐍 Python Tutorial: Implementing an MCP Server & Inspector

## 📦 Overview

In this tutorial, we’ll walk through building a simple **MCP (Model Context Protocol) server** using Python.  
We’ll also explore how to **inspect** and **install** your server using the **MCP CLI tools**.

---

## ⚙️ Step 1: Install `uv`

`uv` is a fast Python package manager and environment tool by Astral.  
Use the following command to install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 🧱 Step 2: Set Up Your Python Project

Initialize a new project and navigate into it:

```bash
uv init simple-mcp-server
cd simple-mcp-server
```

---

## 🧩 Step 3: Create a Virtual Environment

```bash
uv venv .venv
source .venv/bin/activate
```

---

## 📦 Step 4: Install Dependencies

Using `uv`:

```bash
uv add "mcp[cli]" yfinance
```

Alternatively, using `pip`:

```bash
pip install mcp yfinance
```

---

## 🧠 Step 5: Create the MCP Server (`main.py`)

Below is the complete implementation for your **MCP Stock Price Server** 👇

```python
from mcp.server.fastmcp import FastMCP
import yfinance as yf

# Create an MCP server with a custom name
mcp = FastMCP("Stock Price Server")

@mcp.tool()
def get_stock_price(symbol: str) -> float:
    """
    Retrieve the current stock price for the given ticker symbol.
    Returns the latest closing price as a float.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if not data.empty:
            price = data['Close'].iloc[-1]
            return float(price)
        else:
            info = ticker.info
            price = info.get("regularMarketPrice", None)
            if price is not None:
                return float(price)
            else:
                return -1.0
    except Exception:
        return -1.0

@mcp.resource("stock://{symbol}")
def stock_resource(symbol: str) -> str:
    """
    Expose stock price data as a resource.
    Returns a formatted string with the current stock price for the given symbol.
    """
    price = get_stock_price(symbol)
    if price < 0:
        return f"Error: Could not retrieve price for symbol '{symbol}'."
    return f"The current price of '{symbol}' is ${price:.2f}."

@mcp.tool()
def get_stock_history(symbol: str, period: str = "1mo") -> str:
    """
    Retrieve historical data for a stock given a ticker symbol and a period.
    Returns the historical data as a CSV formatted string.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return f"No historical data found for symbol '{symbol}' with period '{period}'."
        return data.to_csv()
    except Exception as e:
        return f"Error fetching historical data: {str(e)}"

@mcp.tool()
def compare_stocks(symbol1: str, symbol2: str) -> str:
    """
    Compare the current stock prices of two ticker symbols.
    Returns a formatted message comparing the two stock prices.
    """
    price1 = get_stock_price(symbol1)
    price2 = get_stock_price(symbol2)
    if price1 < 0 or price2 < 0:
        return f"Error: Could not retrieve data for comparison of '{symbol1}' and '{symbol2}'."
    if price1 > price2:
        return f"{symbol1} (${price1:.2f}) is higher than {symbol2} (${price2:.2f})."
    elif price1 < price2:
        return f"{symbol1} (${price1:.2f}) is lower than {symbol2} (${price2:.2f})."
    else:
        return f"Both {symbol1} and {symbol2} have the same price (${price1:.2f})."

if __name__ == "__main__":
    mcp.run()
```

---

## 🧪 Step 6: Run MCP Inspector

Inspect your MCP server locally using the MCP CLI:

```bash
mcp dev main.py
```

This opens an inspection interface where you can test your registered tools and resources.

---

## 💻 Step 7: Add to Claude Desktop

Once you’ve verified your server, install it to **Claude Desktop**:

```bash
mcp install main.py --name "My MCP Server"
```

Check Claude Desktop JSON or Cursor MCP Add MCP:

```bash
{
  "mcpServers": {
    "My MCP Server": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "yfinance",
        "mcp",
        "run",
        "/Users/sachintripathi/Documents/Py_files/Daimler_MCP_A2A/mcp-server/main.py"
      ]
    }
  } 
}
```

---

## 🧭 Summary

✅ Set up Python MCP server  
✅ Created tools for fetching and comparing stock prices  
✅ Integrated `yfinance` for real-time market data  
✅ Inspected and registered your MCP in Claude  

---

## 🧰 Resources

- 🔗 [MCP Python SDK on PyPI](https://pypi.org/project/mcp/)
- 📘 [YFinance Documentation](https://pypi.org/project/yfinance/)
- 🧑‍💻 [Claude Desktop + MCP Docs](https://modelcontextprotocol.io/)
- 🧰 [Astral’s `uv` Project](https://github.com/astral-sh/uv)

---

> 💡 *Tip:* Extend this server to include financial analytics, historical chart generation, or multi-agent collaboration using frameworks like **LangChain**, **CrewAI**, or **Autogen**.

---

