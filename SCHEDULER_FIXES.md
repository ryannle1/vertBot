# VertBot Scheduler Fixes and Improvements

## Overview
This document outlines the fixes implemented to resolve issues with VertBot's scheduled tasks (price monitoring and daily reports) stopping unexpectedly.

## Issues Identified and Fixed

### 1. **Missing Error Handling**
- **Problem**: Scheduled tasks could crash silently without restarting
- **Fix**: Added comprehensive error handling in all scheduled functions
- **Result**: Tasks now continue running even if individual operations fail

### 2. **Scheduler Management**
- **Problem**: Scheduler could stop running without detection
- **Fix**: Added scheduler watchdog that checks every 5 minutes
- **Result**: Automatic restart of scheduler if it stops

### 3. **Task Lifecycle Management**
- **Problem**: Background tasks could be lost during bot reconnections
- **Fix**: Better task management with proper cleanup and recreation
- **Result**: Tasks are properly managed and restarted when needed

### 4. **Daily Tracking Reset**
- **Problem**: Daily tracking variables weren't properly reset
- **Fix**: Added scheduled daily reset at midnight
- **Result**: Consistent daily operation without manual intervention

## New Features Added

### 1. **Health Check Command** (`!health`)
- Monitors scheduler status
- Shows last activity times
- Displays overall bot health
- Helps diagnose issues quickly

### 2. **Manual Restart Command** (`!restart`)
- Allows administrators to manually restart the scheduler
- Useful for immediate recovery from issues
- Requires admin permissions

### 3. **Scheduler Watchdog**
- Automatically detects when scheduler stops
- Restarts scheduler automatically
- Runs every 5 minutes in background

### 4. **Enhanced Logging**
- Better tracking of task execution times
- More detailed error reporting
- Activity monitoring for debugging

## How to Use

### Check Bot Health
```bash
!health
```
This command shows:
- Scheduler status (running/stopped)
- Scheduled jobs and next run times
- Price monitoring activity
- Daily report status
- Last activity timestamps
- Overall health indicator

### Restart Scheduler (Admin Only)
```bash
!restart
```
This command:
- Restarts the scheduler if it's not running
- Re-adds all scheduled jobs
- Provides status feedback

### Monitor Logs
The bot now provides detailed logging for:
- Scheduler startup/shutdown
- Task execution and errors
- Automatic restarts
- Health check results

## Configuration

### Scheduler Settings
- **Price Check Interval**: 5 minutes (300 seconds)
- **Daily Report Time**: 4:00 PM Eastern Time
- **Daily Reset Time**: 12:00 AM Eastern Time
- **Watchdog Check Interval**: 5 minutes

### Timezone Configuration
All scheduled tasks use US/Eastern timezone for consistency with market hours.

## Troubleshooting

### If Tasks Stop Running

1. **Check Health Status**
   ```bash
   !health
   ```

2. **Look for Error Messages**
   - Check bot logs for error details
   - Look for "scheduler watchdog" messages

3. **Manual Restart**
   ```bash
   !restart
   ```

4. **Check Bot Permissions**
   - Ensure bot has proper Discord permissions
   - Verify bot is still in the server

### Common Issues

1. **Scheduler Not Running**
   - Use `!restart` command
   - Check logs for initialization errors

2. **Price Monitoring Inactive**
   - Verify market data API access
   - Check ticker configuration

3. **Daily Report Not Sending**
   - Verify channel configuration
   - Check timezone settings

## Testing

### Run Startup Tests
```bash
python test_bot_startup.py
```
This script tests:
- Scheduler initialization
- Market monitor functionality
- Task creation
- Basic error handling

## Monitoring and Maintenance

### Regular Health Checks
- Use `!health` command daily
- Monitor logs for warnings/errors
- Check scheduled job status

### Log Rotation
- Logs are automatically rotated
- Maximum file size: 10MB
- Keep 5 backup files

## Technical Details

### Scheduler Implementation
- Uses APScheduler with AsyncIOScheduler
- Cron-based scheduling for daily tasks
- Interval-based scheduling for monitoring
- Grace period handling for missed executions

### Task Management
- Proper asyncio task lifecycle management
- Automatic cleanup of completed tasks
- Error recovery and restart mechanisms

### Error Handling
- Comprehensive exception catching
- Graceful degradation on failures
- Automatic retry mechanisms
- Detailed error logging

## Future Improvements

1. **Metrics Collection**
   - Task execution statistics
   - Performance monitoring
   - Alert thresholds

2. **Advanced Scheduling**
   - Dynamic schedule adjustment
   - Market hours detection
   - Holiday handling

3. **Health Dashboard**
   - Web-based monitoring
   - Real-time status updates
   - Historical data

## Support

If you continue to experience issues:
1. Check the logs for detailed error messages
2. Use the `!health` command to diagnose problems
3. Try the `!restart` command for immediate recovery
4. Review this documentation for troubleshooting steps
