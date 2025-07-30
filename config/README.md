# Configuration Files

This folder contains configuration files for the Discord bot. **Do not commit the actual config files to version control** as they contain sensitive data.

## Files

### `channels.json`
Stores Discord channel IDs for each guild where the bot should send reports.
- **Format**: `{"guild_id": channel_id}`
- **Example**: See `channels.json.example`

### `tickers.json`
Stores user-defined stock tickers for each guild.
- **Format**: `{"guild_id": ["TICKER1", "TICKER2"]}`
- **Example**: See `tickers.json.example`

### `constants.py`
Contains hardcoded constants like default stock symbols.
- **Safe to commit**: Contains no sensitive data

## Setup Instructions

1. **Copy example files**:
   ```bash
   cp config/channels.json.example config/channels.json
   cp config/tickers.json.example config/tickers.json
   ```

2. **Edit the files** with your actual data:
   - Replace `guild_id_1` with your actual Discord guild ID
   - Replace the channel IDs with your actual channel IDs
   - Add your preferred stock tickers

3. **Never commit** the actual `.json` files to version control

## Getting Guild and Channel IDs

1. **Enable Developer Mode** in Discord (User Settings > Advanced > Developer Mode)
2. **Right-click** on your server → "Copy Server ID" (for guild_id)
3. **Right-click** on a channel → "Copy Channel ID" (for channel_id)

## Security Notes

- ✅ **Safe to commit**: `constants.py`, `*.example` files, `README.md`
- ❌ **Never commit**: `channels.json`, `tickers.json`, `.env` files
- 🔒 **Keep private**: All files containing real IDs, tokens, or user data 