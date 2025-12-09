from flask import Flask, render_template, jsonify
import csv
import os
import json
import time
from urllib.request import urlopen, Request
from urllib.parse import quote

app = Flask(__name__)

# Cache file to store geocoded coordinates (so we don't re-geocode every time)
CACHE_FILE = 'geocode_cache.json'

def load_cache():
    """Load cached coordinates from file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save coordinates cache to file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def geocode_location(city, state, cache):
    """
    Geocode a city/state using Nominatim (OpenStreetMap).
    Free, no API key required, but requires 1 second delay between requests.
    """
    if not city or not state:
        return None, None
    
    # Create cache key
    cache_key = f"{city.strip()}, {state.strip()}"
    
    # Check cache first
    if cache_key in cache:
        coords = cache[cache_key]
        return coords.get('lat'), coords.get('lng')
    
    # Build the geocoding URL
    query = quote(f"{city}, {state}, USA")
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
    
    try:
        # Nominatim requires a User-Agent header
        req = Request(url, headers={'User-Agent': 'BlackPublicationsMap/1.0'})
        response = urlopen(req, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        if data:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            
            # Save to cache
            cache[cache_key] = {'lat': lat, 'lng': lng}
            save_cache(cache)
            
            # Respect Nominatim's rate limit (1 request per second)
            time.sleep(1)
            
            return lat, lng
    except Exception as e:
        print(f"Geocoding error for {city}, {state}: {e}")
    
    # Cache failed lookups too (as None) to avoid retrying
    cache[cache_key] = {'lat': None, 'lng': None}
    save_cache(cache)
    return None, None

def parse_time_period(time_period):
    """Parse time period string like '1920-1935' into start and end years."""
    try:
        if '-' in str(time_period):
            parts = time_period.split('-')
            return int(parts[0].strip()), int(parts[1].strip())
        else:
            year = int(time_period)
            return year, year
    except (ValueError, AttributeError):
        return None, None

def load_publications():
    """Load publications from CSV and return as list of dicts."""
    publications = []
    cache = load_cache()
    csv_path = os.path.join(os.path.dirname(__file__), 'Black_Publications.csv')
    
    # Track unique locations to minimize geocoding
    locations_to_geocode = set()
    
    # First pass: read all data and collect unique locations
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # DEBUG: Print original fieldnames
        print("ORIGINAL fieldnames:", reader.fieldnames[:5])
        
        # Strip whitespace from column names (fixes trailing spaces issue)
        reader.fieldnames = [name.strip() if name else name for name in reader.fieldnames]
        
        # DEBUG: Print cleaned fieldnames
        print("CLEANED fieldnames:", reader.fieldnames[:5])
        
        for row in reader:
            # DEBUG: Print first row's title value
            if len(rows) == 0:
                print("First row 'Publication_Title' value:", repr(row.get('Publication_Title')))
                print("First row keys:", list(row.keys())[:5])
            
            rows.append(row)
            city = row.get('Publishing_Company_City', '').strip()
            state = row.get('Publishing_Company_State', '').strip()
            if city and state:
                locations_to_geocode.add((city, state))
    
    # Geocode all unique locations
    print(f"Found {len(locations_to_geocode)} unique locations to process...")
    location_coords = {}
    
    for i, (city, state) in enumerate(locations_to_geocode):
        cache_key = f"{city}, {state}"
        if cache_key not in cache:
            print(f"Geocoding ({i+1}/{len(locations_to_geocode)}): {city}, {state}")
        lat, lng = geocode_location(city, state, cache)
        location_coords[(city, state)] = (lat, lng)
    
    # Second pass: build publication records with coordinates
    for row in rows:
        city = row.get('Publishing_Company_City', '').strip()
        state = row.get('Publishing_Company_State', '').strip()
        coords = location_coords.get((city, state), (None, None))
        
        start_year, end_year = parse_time_period(row.get('Time_Period', ''))
        
        pub = {
            'title': row.get('Publication_Title', ''),
            'volume': row.get('Volume', ''),
            'issue': row.get('Issue', ''),
            'audience': row.get('Audience', ''),
            'company': row.get('Publishing_Company_Name', ''),
            'publisher': row.get("Publisher's_Name", ''),
            'city': city,
            'state': state,
            'editor': row.get('Editor(s)', ''),
            'frequency': row.get('Frequency', ''),
            'start_year': start_year,
            'end_year': end_year,
            'digitized_url': row.get('Digitized_URL', ''),
            'lat': coords[0],
            'lng': coords[1]
        }
        publications.append(pub)
    
    print(f"Loaded {len(publications)} publications successfully!")
    
    return publications

@app.route('/')
def cover():
    return render_template('cover.html')

@app.route('/map')
def map_view():
    return render_template('index.html')

@app.route('/publications')
def publications():
    return render_template('publications.html')

@app.route('/digitized')
def digitized():
    return render_template('digitized.html')

@app.route('/api/publications')
def get_publications():
    """API endpoint to get all publications as JSON."""
    publications = load_publications()
    return jsonify(publications)

@app.route('/api/unmapped')
def get_unmapped():
    """Helper endpoint to see which cities couldn't be geocoded."""
    publications = load_publications()
    unmapped = set()
    for pub in publications:
        if pub['lat'] is None and pub['city']:
            unmapped.add((pub['city'], pub['state']))
    return jsonify(list(unmapped))

@app.route('/api/clear-cache')
def clear_cache():
    """Clear the geocode cache (useful if you want to retry failed lookups)."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        return jsonify({'status': 'Cache cleared'})
    return jsonify({'status': 'No cache file found'})

if __name__ == '__main__':
    print("Starting Black Publications Map...")
    print("First run will geocode all locations (this may take a few minutes)")
    print("Coordinates are cached, so subsequent runs will be fast.")
    app.run(debug=True)