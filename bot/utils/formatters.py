def format_closing_price_report(symbol: str, price: float, date: str) -> str:
    """
    Returns a formatted string for the closing price report.
    """
    return (
        f"\n==============================\n"
        f"  📈  {symbol.upper()} Market Close\n"
        f"------------------------------\n"
        f"  Price:      ${price:,.2f}\n"
        f"  Date:       {date}\n"
        f"=============================="
    )
