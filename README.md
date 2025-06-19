# IMDb 2024 Feature Movies — Data Pipeline and Visualization

## Overview

This project automates the process of collecting feature movie data released in 2024 from IMDb, enriching it with detailed genres and duration information, and providing an interactive web dashboard for exploration and analysis.

---

## Project Workflow

1. **Data Scraping:**  
   Using **Selenium**, the IMDb search page filtered by 2024 feature films is accessed. The script dynamically clicks the **"50 more"** button until a user-defined limit of movies is reached or all are loaded.

2. **Basic Info Parsing:**  
   From the loaded search results, essential details like **title**, **rating**, **votes**, and **movie detail URLs** are extracted.

3. **Detail Page Enrichment:**  
   Each movie’s detail page is fetched in parallel (via HTTP requests) to scrape detailed **genres** and **exact duration** values.

4. **Data Cleaning:**  
   Titles are cleaned to remove serial numbers, durations converted to total minutes, and missing values replaced with defaults.

5. **Interactive Visualization:**  
   Built with **Streamlit**, users can filter movies dynamically by duration, rating, vote counts, and genre, and explore rich visualizations — top movies, genre distributions, rating trends, heatmaps, and correlation plots.

6. **Data Storage:**  
   Processed data is saved as CSV, SQLite, and uploaded to a **PostgreSQL** database for persistence and further analysis.

---

## Technologies

- **Python 3.9+**  
- **Web Scraping:** Selenium, Requests, BeautifulSoup  
- **Data Processing:** Pandas, NumPy  
- **Visualization:** Streamlit, Plotly, Matplotlib, Seaborn  
- **Database:** SQLite, PostgreSQL, SQLAlchemy

---

## Setup Instructions

### 1. Clone/Download the Project  
Place the scripts in your working directory.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```
### 3. ChromeDriver Setup
Download matching ChromeDriver for your Chrome version from:
https://chromedriver.chromium.org/downloads

#### Update the CHROMEDRIVER_PATH in the script accordingly.

### 4. PostgreSQL Setup
#### Make sure the PostgreSQL server is running and create a database, e.g.:
```bash
sql
CREATE DATABASE imdb;
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE imdb TO your_user;
```
#### Update the PostgreSQL credentials (db_user, db_pass, db_host, db_port, db_name) in the script accordingly.

#### Running the Project
Data Scraping and Processing
```bash
python data_scraping_and_store.py
This scrapes movie data, enriches with genres/duration, and saves to CSV and databases.
```
#### Running the Visualization Dashboard
```bash
streamlit run imdb_streamlit_app.py
```
#### Use the sidebar filters and explore the various visualizations.

### Features
- Incremental loading and scraping for large datasets via Selenium
- Parallel detail page fetching for performance
- Cleaned and consistent data for analysis
- Comprehensive, interactive visualizations
- Multi-format persistent data storage
- Project Structure

### Files 
- data_scraping_and_store.py **# Scrapes and processes data**
- imdb_streamlit_app.py   **# Streamlit interactive dashboard**
- imdb_2024_all_movies.csv   **# Processed full dataset CSV**
- IMDB_2024_by_genre/        **# CSVs grouped by major genre**
- requirements.txt           **# Python dependencies file**


### Future Improvements
- Add resume and checkpointing for scraper robustness
- Support asynchronous detail fetching for better speed
- Implement data validation and logging
- Deploy Streamlit app for cloud or browser access

### Contact
Questions or contributions? Please contact: sindhudhinakaran78@gmail.com

---

