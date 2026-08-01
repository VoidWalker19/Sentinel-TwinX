# Logging Service

Provides standard rotating file loggers combined with clean console outputs.

## Configuration
- `log_dir`: Folder where logs are written (default: `"logs"`).
- `log_file`: Name of log file (default: `"sentinel.log"`).
- `max_bytes`: Maximum file size in bytes before rollover (default: `5242880` or 5MB).
- `backup_count`: Count of rotated log backups to keep (default: `5`).
- `level`: Minimum logging level (default: `logging.INFO`).

## Errors Handled
- Permissions exceptions when creating directories or log files: Automatically catches disk write failures and falls back gracefully to standard console logging to prevent server boot failure.
