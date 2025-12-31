#!/usr/bin/env python3
"""
Roast.World to Artisan Converter
Download and convert roast profiles from roast.world to Artisan CSV format

Usage:
    python roastworld_to_artisan.py <roast_id_or_url>
    python roastworld_to_artisan.py 0QQFP4AFGdZC34Il64oPQ
    python roastworld_to_artisan.py https://roast.world/sweetmarias/roasts/0QQFP4AFGdZC34Il64oPQ
"""

import sys
import re
import json
import requests
from datetime import datetime
from pathlib import Path


def extract_roast_id(input_str):
    """Extract roast ID from URL or return the ID directly"""
    # Check if it's a URL
    url_pattern = r'roast\.world/[^/]+/roasts/([A-Za-z0-9_-]+)'
    match = re.search(url_pattern, input_str)
    if match:
        return match.group(1)
    
    # Otherwise assume it's already an ID
    return input_str.strip()


def fetch_roast_data(roast_id):
    """Fetch roast data from roast.world Firebase storage"""
    url = f"https://firebasestorage.googleapis.com/v0/b/testaillio.appspot.com/o/roasts%2F{roast_id}.json?alt=media"
    
    print(f"Fetching roast data for ID: {roast_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching roast data: {e}")
        return None


def detect_duplicate_samples(drum_temps):
    """
    Detect if temperature data has duplicate samples.
    R2 data often stores 1-second samples as pairs (val1, val1, val2, val2, ...)
    """
    if len(drum_temps) < 40:
        return False
    
    # Check if consecutive even/odd pairs are identical
    duplicate_count = sum(
        1 for i in range(10, 30, 2)
        if abs(drum_temps[i] - drum_temps[i + 1]) < 0.01
    )
    
    return duplicate_count > 8  # Most pairs are duplicates


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit"""
    return celsius * 9/5 + 32


def format_time(seconds):
    """Convert seconds to MM:SS format"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def convert_to_artisan_csv(roast_data, output_file=None):
    """
    Convert roast.world JSON data to Artisan CSV format
    
    Args:
        roast_data: Dictionary containing roast data from roast.world
        output_file: Optional output filename
    
    Returns:
        Path to the created CSV file
    """
    # Extract key data
    bt_temps = roast_data['beanTemperature']
    drum_temps = roast_data['drumTemperature']
    sample_rate = roast_data['sampleRate']
    roast_start_idx = roast_data['roastStartIndex']
    first_crack_idx = roast_data.get('indexFirstCrackStart', 0)
    weight_in = roast_data['weightGreen']
    weight_out = roast_data['weightRoasted']
    roast_name = roast_data.get('roastName', 'Roast')
    roast_id = roast_data.get('uid', 'unknown')
    
    # Detect if data has duplicate samples
    has_duplicates = detect_duplicate_samples(drum_temps)
    
    if has_duplicates:
        print("Detected duplicate samples - using 1-second resolution")
        # Take every other sample
        bt_array = bt_temps[roast_start_idx::2]
        drum_array = drum_temps[roast_start_idx::2]
        effective_sample_rate = 1.0  # Actual rate is 1 second
    else:
        bt_array = bt_temps[roast_start_idx:]
        drum_array = drum_temps[roast_start_idx:]
        effective_sample_rate = sample_rate
    
    # Ensure arrays are same length
    min_len = min(len(bt_array), len(drum_array))
    bt_array = bt_array[:min_len]
    drum_array = drum_array[:min_len]
    
    # Calculate timing
    num_points = min_len
    total_time = (num_points - 1) * effective_sample_rate
    
    if has_duplicates:
        first_crack_time = ((first_crack_idx - roast_start_idx) // 2) * effective_sample_rate
    else:
        first_crack_time = (first_crack_idx - roast_start_idx) * effective_sample_rate
    
    # Print summary
    print(f"\nRoast: {roast_name}")
    print(f"Sample rate: {effective_sample_rate}s")
    print(f"Total points: {num_points}")
    print(f"Total time: {int(total_time)}s ({int(total_time)//60}:{int(total_time)%60:02d})")
    print(f"First Crack: {int(first_crack_time)}s ({int(first_crack_time)//60}:{int(first_crack_time)%60:02d})")
    print(f"Weight: {weight_in}g → {weight_out}g ({100*(weight_in-weight_out)/weight_in:.1f}% loss)")
    print(f"BT range: {min(bt_array):.1f}°C - {max(bt_array):.1f}°C")
    print(f"Drum range: {min(drum_array):.1f}°C - {max(drum_array):.1f}°C")
    
    # Generate CSV
    csv_lines = []
    
    # Header line
    today = datetime.now().strftime('%d.%m.%Y')
    csv_lines.append(
        f"Date:{today}\t"
        f"Unit:F\t"
        f"CHARGE:00:00\t"
        f"TP:\t"
        f"DRYe:\t"
        f"FCs:{format_time(first_crack_time)}\t"
        f"FCe:\t"
        f"SCs:\t"
        f"SCe:\t"
        f"DROP:{format_time(total_time)}\t"
        f"COOL:\t"
        f"Time:00:00\t"
        f"Notes:{roast_name} (roast.world ID: {roast_id})"
    )
    
    # Column headers
    csv_lines.append("Time1\tTime2\tET\tBT\tEvent")
    
    # Data rows
    time_array = [i * effective_sample_rate for i in range(num_points)]
    for i, t in enumerate(time_array):
        bt_f = celsius_to_fahrenheit(bt_array[i])
        drum_f = celsius_to_fahrenheit(drum_array[i])
        time_str = format_time(t)
        
        # Mark events
        event = ""
        if i == 0:
            event = "Charge"
        elif first_crack_time > 0 and abs(t - first_crack_time) < effective_sample_rate:
            event = "FCs"
        elif i == len(time_array) - 1:
            event = "Drop"
        
        csv_lines.append(f"{time_str}\t{time_str}\t{drum_f:.1f}\t{bt_f:.1f}\t{event}")
    
    # Generate output filename if not provided
    if output_file is None:
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', roast_name)
        output_file = f"{safe_name}_{roast_id[:8]}.csv"
    
    # Write CSV file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(csv_lines))
    
    print(f"\n✓ CSV file created: {output_path.absolute()}")
    return output_path


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python roastworld_to_artisan.py <roast_id_or_url_or_file>")
        print("\nExamples:")
        print("  python roastworld_to_artisan.py 0QQFP4AFGdZC34Il64oPQ")
        print("  python roastworld_to_artisan.py https://roast.world/sweetmarias/roasts/0QQFP4AFGdZC34Il64oPQ")
        print("  python roastworld_to_artisan.py roast_data.json")
        sys.exit(1)
    
    input_str = sys.argv[1]
    
    # Check if input is a local file
    if Path(input_str).is_file():
        print(f"Reading from local file: {input_str}")
        try:
            with open(input_str, 'r') as f:
                roast_data = json.load(f)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    else:
        # Extract roast ID and fetch from roast.world
        roast_id = extract_roast_id(input_str)
        roast_data = fetch_roast_data(roast_id)
        if roast_data is None:
            print("Failed to fetch roast data")
            sys.exit(1)
    
    # Convert to Artisan CSV
    output_file = None
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    try:
        convert_to_artisan_csv(roast_data, output_file)
        print("\nConversion complete!")
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
