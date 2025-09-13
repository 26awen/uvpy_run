# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "requests",
# ]
# ///

# MIT License
#
# Copyright (c) 2025 Config-Txt Project
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Third-party Dependencies:
# - Click: BSD-3-Clause License (https://github.com/pallets/click)
# - Requests: Apache-2.0 License (https://github.com/psf/requests)

"""
IP address and location information lookup tool

A command-line utility for retrieving current IP address and location information
using the ipinfo.io service. Supports both current IP lookup and specific IP address
queries with flexible output formats.



Version: 0.6.0
Category: Network Utility
Author: Config-Txt Project

Usage Examples:
    uv run terminal_proxy_ip.py current
    uv run terminal_proxy_ip.py current --format json --verbose
    uv run terminal_proxy_ip.py lookup 8.8.8.8
    uv run terminal_proxy_ip.py lookup 1.1.1.1 --format json --verbose
"""

# WARN: if you have problem, see https://ipinfo.io/missingauth

import click
import requests
from typing import Dict, Any, Optional
import json


def get_ip_info() -> Optional[Dict[str, Any]]:
    """Get current IP address and location information from ipinfo.io"""
    try:
        response = requests.get("https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        click.echo(f"Error getting IP information: {e}")
        return None


def parse_location(loc_str: str) -> tuple[str, str]:
    """Parse location string from ipinfo.io format 'lat,lng'"""
    if not loc_str:
        return "Unknown", "Unknown"
    
    try:
        lat, lng = loc_str.split(",")
        return lat.strip(), lng.strip()
    except ValueError:
        return "Unknown", "Unknown"


@click.command()
@click.option("--format", "-f", type=click.Choice(["json", "table"]), default="table", 
              help="Output format (json or table)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def main(format: str, verbose: bool) -> None:
    """Get current proxy IP address and location information using ipinfo.io"""
    click.echo("Fetching current IP information from ipinfo.io...")
    
    # Get IP information from ipinfo.io
    ip_info = get_ip_info()
    if not ip_info:
        click.echo("Failed to retrieve IP information")
        return
    
    # Output results based on format
    if format == "json":
        click.echo(json.dumps(ip_info, indent=2))
    else:
        # Display in table format
        click.echo(f"IP Address: {ip_info.get('ip', 'Unknown')}")
        click.echo(f"City: {ip_info.get('city', 'Unknown')}")
        click.echo(f"Region: {ip_info.get('region', 'Unknown')}")
        click.echo(f"Country: {ip_info.get('country', 'Unknown')}")
        
        if verbose:
            click.echo(f"Organization: {ip_info.get('org', 'Unknown')}")
            click.echo(f"Timezone: {ip_info.get('timezone', 'Unknown')}")
            click.echo(f"Postal Code: {ip_info.get('postal', 'Unknown')}")
            
            # Parse and display coordinates
            loc = ip_info.get('loc', '')
            if loc:
                lat, lng = parse_location(loc)
                click.echo(f"Latitude: {lat}")
                click.echo(f"Longitude: {lng}")
            else:
                click.echo("Latitude: Unknown")
                click.echo("Longitude: Unknown")
            
            # Display hostname if available
            hostname = ip_info.get('hostname')
            if hostname:
                click.echo(f"Hostname: {hostname}")


@click.command()
@click.argument("ip_address", required=False)
@click.option("--format", "-f", type=click.Choice(["json", "table"]), default="table", 
              help="Output format (json or table)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def lookup(ip_address: Optional[str], format: str, verbose: bool) -> None:
    """Look up information for a specific IP address"""
    if not ip_address:
        click.echo("Please provide an IP address to look up")
        return
    
    click.echo(f"Looking up information for IP: {ip_address}")
    
    try:
        response = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=10)
        response.raise_for_status()
        ip_info = response.json()
    except requests.RequestException as e:
        click.echo(f"Error looking up IP information: {e}")
        return
    
    # Output results based on format
    if format == "json":
        click.echo(json.dumps(ip_info, indent=2))
    else:
        # Display in table format
        click.echo(f"IP Address: {ip_info.get('ip', 'Unknown')}")
        click.echo(f"City: {ip_info.get('city', 'Unknown')}")
        click.echo(f"Region: {ip_info.get('region', 'Unknown')}")
        click.echo(f"Country: {ip_info.get('country', 'Unknown')}")
        
        if verbose:
            click.echo(f"Organization: {ip_info.get('org', 'Unknown')}")
            click.echo(f"Timezone: {ip_info.get('timezone', 'Unknown')}")
            click.echo(f"Postal Code: {ip_info.get('postal', 'Unknown')}")
            
            # Parse and display coordinates
            loc = ip_info.get('loc', '')
            if loc:
                lat, lng = parse_location(loc)
                click.echo(f"Latitude: {lat}")
                click.echo(f"Longitude: {lng}")
            else:
                click.echo("Latitude: Unknown")
                click.echo("Longitude: Unknown")
            
            # Display hostname if available
            hostname = ip_info.get('hostname')
            if hostname:
                click.echo(f"Hostname: {hostname}")


@click.group()
def cli() -> None:
    """IP information tool using ipinfo.io service"""
    pass


cli.add_command(main, name="current")
cli.add_command(lookup, name="lookup")


if __name__ == "__main__":
    cli()
