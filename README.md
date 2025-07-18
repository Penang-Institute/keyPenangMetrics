`# Key Penang Metrics

Compiles latest data on key Penang metrics from [data-gov-my](https://github.com/data-gov-my/) API every week and outputs [metrics.tsv](output/metrics.tsv).

**Live Website**: https://statistics.penanginstitute.org/

## Architecture

This repository serves as a data pipeline that:
1. **Fetches** key metrics from Malaysian government APIs weekly
2. **Processes** data into multiple formats (TSV, YAML, JSON)
3. **Deploys** automatically to the main [pistats](https://github.com/Penang-Institute/pistats) repository as a submodule
4. **Updates** the live statistics website with fresh data

## Data Sources

The system retrieves data from multiple [data-gov-my](https://github.com/data-gov-my/) APIs:
- Population statistics
- GDP and economic indicators
- Employment data
- Consumer Price Index (CPI)
- Household income metrics
- RSS feed from Penang Monthly publications

## Scripts

### Python (Current)
- `scripts/metrics.py` - Python implementation for retrieving and processing metrics data
- `requirements.txt` - Python dependencies

### R (Legacy)
- `scripts/metrics.R` - Original R implementation (maintained for backup)

## GitHub Actions

### Python Workflows (Current)
- `render-metrics-cron-python.yaml` - Scheduled execution every Thursday at 5am UTC
- `render-metrics-manual-python.yaml` - Manual trigger workflow

#### Manual Execution
To manually trigger the data update workflow:
1. Go to the [Actions tab](https://github.com/Penang-Institute/keyPenangMetrics/actions)
2. Select "Manual task (Python)" workflow
3. Click "Run workflow" button
4. Confirm by clicking "Run workflow"

This will immediately fetch fresh data and update the live website.

### R Workflows (Disabled)
- `render-metrics-cron.yaml.disabled` - Original R-based scheduled workflow (disabled)
- `render-metrics-manual.yaml.disabled` - Original R-based manual workflow (disabled)

## Changelog

### 2025-06-13 - R to Python Migration Finalized
- **Disabled**: R-based GitHub Actions workflows (moved to .disabled extension)
- **Primary**: Python implementation now the sole production system
- **Status**: R workflows deactivated, Python workflows operational
- **Migration**: Complete transition from R to Python accomplished

### 2025-06-12 - Python Migration Complete
- **Added**: GitHub Actions workflows for Python execution
  - `render-metrics-cron-python.yaml` - Automated weekly execution
  - `render-metrics-manual-python.yaml` - Manual trigger capability
- **Updated**: Production deployment now uses Python implementation
- **Status**: Migration fully complete and operational

### 2025-06-03 - Python Migration
- **Added**: `scripts/metrics.py` - Python version of the metrics processing script
  - Improved error handling and logging
  - Better API response validation
  - Direct HTTP handling for parquet files using PyArrow
  - Robust XML parsing for RSS feeds
  - Enhanced data type checking and validation
- **Added**: `requirements.txt` - Python package dependencies
- **Maintained**: `scripts/metrics.R` - Original R script kept as backup during migration period

### Features of Python Implementation
- **Better Error Handling**: Comprehensive try-catch blocks with informative error messages
- **API Response Validation**: Handles different API response structures robustly  
- **Direct Parquet Processing**: Uses pandas and PyArrow for efficient data handling
- **UTF-8 Encoding**: Explicit encoding for all file operations
- **Defensive Programming**: Checks for empty responses and missing data fields
- **Improved Logging**: Detailed progress and error reporting
- **Automated Deployment**: GitHub Actions workflows for scheduled and manual execution

## Dependencies

### Python
```bash
pip install -r requirements.txt
```

### R (Legacy)
Uses renv for package management. See `renv.lock` for specific versions.

## Usage

### Python
```bash
python scripts/metrics.py
```

### R (Legacy)
```r
source("scripts/metrics.R")
```

## Output Files

The Python script generates the following output files:
- `output/metrics.tsv` - Tab-separated values for key metrics
- `output/metrics_python.tsv` - Python-specific metrics output
- `output/metrics_grid.yaml` - YAML format for Quarto grid display
- `output/metrics_grid.json` - JSON format for web applications
- `output/metrics_grid_python.yaml` - Python-specific YAML grid format
- `output/penang-monthly-stats.yaml` - Penang Monthly statistics articles from RSS feed

These files are automatically integrated into the [pistats website](https://statistics.penanginstitute.org/) through the submodule system.