#!/usr/bin/env python3
"""
Retrieve metrics from OpenDOSM API and generate output files.
Python migration of scripts/metrics.R
"""

import os
import json
import yaml
import requests
import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

def create_base_request():
    """Create base API request URL"""
    return "https://api.data.gov.my/data-catalogue"

def make_api_request(params):
    """Make API request with given parameters"""
    url = f"{create_base_request()}?{urlencode(params)}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_gdp_growth():
    """Get GDP growth data"""
    params = {
        'id': 'gdp_state_real_supply',
        'sort': '-date',
        'ifilter': 'pulau pinang@state',
        'filter': 'p0@sector',
        'contains': 'growth_yoy@series',
        'limit': 1,
        'include': 'date,value'
    }
    return make_api_request(params)

def get_income():
    """Get median household income data"""
    params = {
        'id': 'hh_income_state',
        'sort': '-date',
        'ifilter': 'pulau pinang@state',
        'include': 'date,income_median',
        'limit': 1
    }
    return make_api_request(params)

def get_cpi():
    """Get CPI inflation data"""
    params = {
        'id': 'cpi_state_inflation',
        'sort': '-date',
        'ifilter': 'pulau pinang@state',
        'filter': 'overall@division',
        'include': 'date,inflation_yoy',
        'limit': 1
    }
    return make_api_request(params)

def get_unemployment():
    """Get unemployment rate data"""
    params = {
        'id': 'lfs_qtr_state',
        'sort': '-date',
        'ifilter': 'pulau pinang@state',
        'include': 'date,u_rate',
        'limit': 1
    }
    return make_api_request(params)

def get_population():
    """Get population data from parquet file"""
    url = "https://storage.dosm.gov.my/population/population_state.parquet"
    
    # Read parquet file
    table = pq.read_table(url)
    df = table.to_pandas()
    
    # Filter data
    filtered = df[
        (df['sex'] == 'both') &
        (df['age'] == 'overall') &
        (df['ethnicity'] == 'overall') &
        (df['state'] == 'Pulau Pinang')
    ]
    
    # Get latest date
    latest = filtered[filtered['date'] == filtered['date'].max()]
    
    return {
        'date': latest['date'].iloc[0].strftime('%Y-%m-%d'),
        'population': latest['population'].iloc[0]
    }

def format_date(date_str, metric_type):
    """Format date based on metric type"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    if metric_type in ['population', 'value', 'income_median']:
        return date_obj.strftime('%Y')
    elif metric_type == 'inflation_yoy':
        return date_obj.strftime('%b %Y')
    elif metric_type == 'u_rate':
        quarter = (date_obj.month + 2) // 3
        return f"Q{quarter} {date_obj.year}"
    else:
        return date_obj.strftime('%Y')

def format_value(value, metric_type):
    """Format value based on metric type"""
    if metric_type == 'population':
        return f"{value/1000:.2f}mil"
    elif metric_type == 'income_median':
        return f"RM{value:,.0f}"
    else:
        return f"{value:.2f}%"

def process_api_data():
    """Process all API data and combine into standardized format"""
    # Get all data
    gdp_data = get_gdp_growth()
    income_data = get_income()
    cpi_data = get_cpi()
    unemployment_data = get_unemployment()
    population_data = get_population()
    
    # Process API responses
    datasets = {
        'GDP growth': gdp_data,
        'Median gross household income': income_data,
        'CPI inflation, year-on-year': cpi_data,
        'Unemployment rate': unemployment_data
    }
    
    results = []
    
    # Process API datasets
    for dataset_name, data in datasets.items():
        if data and len(data) > 0:
            record = data[0]
            date = record['date']
            
            # Determine value key
            if 'value' in record:
                value = record['value']
                metric_type = 'value'
            elif 'income_median' in record:
                value = record['income_median']
                metric_type = 'income_median'
            elif 'inflation_yoy' in record:
                value = record['inflation_yoy']
                metric_type = 'inflation_yoy'
            elif 'u_rate' in record:
                value = record['u_rate']
                metric_type = 'u_rate'
            else:
                continue
            
            results.append({
                'dataset': dataset_name,
                'value': format_value(value, metric_type),
                'date_format': format_date(date, metric_type)
            })
    
    # Add population data
    results.insert(0, {
        'dataset': 'Population',
        'value': format_value(population_data['population'], 'population'),
        'date_format': format_date(population_data['date'], 'population')
    })
    
    return results

def save_metrics_tsv(data, filename='output/metrics.tsv'):
    """Save metrics data as TSV file"""
    os.makedirs('output', exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write("dataset\tvalue\tdate_format\n")
        for record in data:
            f.write(f"{record['dataset']}\t{record['value']}\t{record['date_format']}\n")

def save_metrics_yaml(data, filename='output/metrics_grid.yaml'):
    """Save metrics data as YAML for Quarto grid"""
    path_mapping = {
        'Population': 'dashboards/pop.html',
        'GDP growth': 'dashboards/gdp.html',
        'Median gross household income': 'dashboards/hhinc.html',
        'CPI inflation, year-on-year': 'dashboards/cpi.html',
        'Unemployment rate': 'dashboards/labour.html'
    }
    
    yaml_data = []
    for record in data:
        yaml_data.append({
            'description': record['dataset'],
            'subtitle': record['value'],
            'title': record['date_format'],
            'path': path_mapping.get(record['dataset'], '')
        })
    
    with open(filename, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False)

def save_metrics_json(data, filename='output/metrics_grid.json'):
    """Save metrics data as JSON"""
    json_data = []
    for record in data:
        json_data.append({
            'description': record['dataset'],
            'value': record['value'],
            'date_format': record['date_format']
        })
    
    with open(filename, 'w') as f:
        json.dump(json_data, f)

def process_penang_monthly_rss():
    """Process Penang Monthly RSS feed for statistics articles"""
    rss_url = "https://www.penangmonthly.com/tag/statistics/rss"
    
    response = requests.get(rss_url)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    
    articles = []
    for item in root.findall('.//item'):
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else ''
        
        # Extract date from category (similar to R regex logic)
        categories = item.findall('category')
        date_str = None
        for cat in categories:
            if cat.text and any(month in cat.text for month in 
                              ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December']):
                try:
                    date_obj = datetime.strptime(f"1 {cat.text}", "%d %B %Y")
                    date_str = date_obj.strftime("%Y-%m-01")
                    break
                except ValueError:
                    continue
        
        # Get content URL for image
        content = item.find('content')
        image_url = content.get('url') if content is not None else ''
        
        # Get author
        creator = item.find('.//{http://purl.org/dc/elements/1.1/}creator')
        author = creator.text if creator is not None else ''
        
        if date_str:  # Only add if we found a valid date
            articles.append({
                'title': title,
                'date': date_str,
                'path': link,
                'image': image_url,
                'author': author
            })
    
    # Save as YAML
    with open('output/penang-monthly-stats.yaml', 'w') as f:
        yaml.dump(articles, f, default_flow_style=False)

def main():
    """Main function to run all processing"""
    print("Processing metrics data...")
    
    # Process metrics
    metrics_data = process_api_data()
    
    # Save in multiple formats
    save_metrics_tsv(metrics_data)
    save_metrics_yaml(metrics_data)
    save_metrics_json(metrics_data)
    
    print("Processing Penang Monthly RSS...")
    process_penang_monthly_rss()
    
    print("Done!")

if __name__ == "__main__":
    main()