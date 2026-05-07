# Tokyo-Airbnb-Analysis
An interactive geospatial dashboard analyzing Tokyo's Airbnb market to identify "hidden gem" neighborhoods by balancing cost, guest satisfaction, and transit proximity. Built with Python, Streamlit, and Plotly for CS 4379G.  

Data Sourcing & Setup
Due to GitHub's file size limitations, the raw datasets are not included in this repository. To run the dashboard locally, please follow these steps:

Download the Data: Visit Inside Airbnb - Get the Data. http://insideairbnb.com/get-the-data/  

Locate Tokyo: Scroll down and find Tokyo.

Required Files: Download the following files from the September 2025 snapshot (or the most recent version):

listings.csv: Summary information and metrics for listings in Tokyo.

reviews.csv: Basic review data.

reviews.csv.gz: Detailed review data (used for the Listing Inspector).

Placement: Move the downloaded files into the data/ folder. Your directory structure should look like this:

Tokyo-Airbnb-Analysis/
├── app.py
├── data/
│   ├── listings.csv
│   ├── reviews.csv
│   └── reviews.csv.gz
└── README.md