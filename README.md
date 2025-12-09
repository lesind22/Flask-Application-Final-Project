# Flask App with Leaflet.js Visualization

This is a Flask application that visualizes Black Publications in the United States from 1859-2025 using Leaflet.js.

# What This App Does: 
  - Reads data from the Black_Publications.csv
  - Displays Three Interactive Visualizations:
    1. Geographic distribution (U.S. Map of Publications from state-to-state)
    2. Detailed data (List of Publications)
    3. Direct access to sources (Digitized Link to Publications)
      

# How to Run:
Install Flask:

	pip install -r requirements.txt


Activate your virtual environment:

	python3 -m venv venv
____________________________________
	source venv/bin/activate


Run the Application:

	python app.py


Open your browser and go to this link:

	http://127.0.0.1:5000/
____________________________________

#Files:
- app.py: Main Flask application
- templates folder: HTML files
- Black_Publications.csv: Data file with Black Publications information
- requirements.txt: Python dependencies 
