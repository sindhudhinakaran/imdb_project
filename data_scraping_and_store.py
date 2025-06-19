import os
import time
import re
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException, TimeoutException
)
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine

CHROMEDRIVER_PATH = r'C:\Program Files (x86)\chromedriver.exe'
IMDB_SEARCH_URL = 'https://www.imdb.com/search/title/?title_type=feature&release_date=2024-01-01,2024-12-31'

OUTPUT_DIR = "IMDB_2024_by_genre"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_vote_count(vote_str):
    try:
        cleaned = (
            vote_str.replace('\xa0', '')
            .replace('(', '')
            .replace(')', '')
            .replace(',', '')
            .strip()
            .upper()
        )
        if 'K' in cleaned:
            return int(float(cleaned.replace('K', '')) * 1000)
        elif 'M' in cleaned:
            return int(float(cleaned.replace('M', '')) * 1_000_000)
        else:
            return int(cleaned)
    except Exception as e:
        print(f"Failed to parse vote count from '{vote_str}': {e}")
        return 0

def scrape_search_results(limit=300):
    service = Service(CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment for headless
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(IMDB_SEARCH_URL)
    driver.maximize_window()
    wait = WebDriverWait(driver, 30)

    time.sleep(5)

    while True:
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.ipc-metadata-list-summary-item')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            movies = soup.find_all('li', class_='ipc-metadata-list-summary-item')
            current_count = len(movies)
            print(f"Movies loaded so far: {current_count}")

            if limit and current_count >= limit:
                print(f"Reached limit of {limit} movies after loading.")
                break

            try:
                load_more_btn = driver.find_element(By.CSS_SELECTOR, 'button.ipc-see-more__button')
                if not load_more_btn.is_enabled():
                    print("Load more button disabled — all loaded.")
                    break
                driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", load_more_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", load_more_btn)
                print("Clicked '50 more' button.")

                max_wait = 30
                start_time = time.time()
                new_count = current_count
                while new_count <= current_count:
                    time.sleep(1)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    new_count = len(soup.find_all('li', class_='ipc-metadata-list-summary-item'))
                    if time.time() - start_time > max_wait:
                        print("Timeout waiting for more movies to load after click.")
                        break

                if new_count <= current_count:
                    print("No new movies loaded, stopping load loop.")
                    break

                if limit and new_count >= limit:
                    print(f"Reached limit of {limit} movies after loading more.")
                    break

            except (NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
                print(f"Load more button missing or not clickable: {e}")
                break

        except TimeoutException:
            print("Timeout waiting for movies to load, stopping.")
            break

    # Final parse
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    movies = soup.find_all('li', class_='ipc-metadata-list-summary-item')
    print(f"Total movies loaded: {len(movies)}")

    all_movies = []
    for i, movie in enumerate(movies):
        if limit and i >= limit:
            break

        title_elem = movie.find('a', class_='ipc-title-link-wrapper')
        movie_title = title_elem.text.strip() if title_elem else ''
        relative_link = title_elem['href'] if title_elem and title_elem.has_attr('href') else ''
        movie_url = 'https://www.imdb.com' + relative_link if relative_link else ''

        rating = ''
        rating_span = movie.find('span', attrs={'aria-label': lambda x: x and 'IMDb rating:' in x})
        if rating_span:
            rating_val = rating_span.find('span', class_='ipc-rating-star--rating')
            rating = rating_val.text.strip() if rating_val else ''

        votes = None
        vote_span = movie.find('span', class_='ipc-rating-star--voteCount')
        if vote_span:
            votes = parse_vote_count(vote_span.text)

        all_movies.append({
            'Title': movie_title,
            'Rating': rating,
            'Votes': votes,
            'MovieURL': movie_url,
        })

    driver.quit()
    return all_movies

def fetch_genres_and_duration_from_url(movie):
    url = movie['MovieURL']
    genres = ''
    duration = ''
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')

        interests_div = soup.find('div', attrs={'data-testid': 'interests'})
        if interests_div:
            genre_anchors = interests_div.find_all('a', class_='ipc-chip ipc-chip--on-baseAlt')
            genres_list = [
                a.find('span', class_='ipc-chip__text').text.strip()
                for a in genre_anchors if a.find('span', class_='ipc-chip__text')
            ]
            genres = ", ".join(genres_list)

        parent_div = soup.find('div', class_='sc-f9ad6c98-0 bqDcCk')
        if parent_div:
            ul_inline = parent_div.find('ul', class_='ipc-inline-list')
            if ul_inline:
                li_list = ul_inline.find_all('li', recursive=False)
                if len(li_list) >= 3:
                    dur_text = li_list[2].text.strip()
                    if 'h' in dur_text or 'm' in dur_text:
                        duration = dur_text

    except Exception as e:
        print(f"Error fetching genres/duration from {url}: {e}")
    return genres, duration

def parallel_genre_duration_fetch(movies, max_workers=10):
    print(f"Fetching genres and durations for {len(movies)} movies in parallel with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_movie = {executor.submit(fetch_genres_and_duration_from_url, movie): movie for movie in movies}
        for future in as_completed(future_to_movie):
            movie = future_to_movie[future]
            try:
                genres, duration = future.result()
            except Exception as e:
                print(f"Error in future: {e}")
                genres, duration = '', ''
            movie['Genre'] = genres
            movie['Duration'] = duration

    print("Completed fetching genres and durations.")
    return movies

def clean_title(title):
    return re.sub(r'^\s*\d+\.\s*', '', title).strip()

def duration_to_minutes(duration_str):
    if not duration_str or not isinstance(duration_str, str):
        return 0
    match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?', duration_str)
    hours = int(match.group(1)) if match and match.group(1) else 0
    minutes = int(match.group(2)) if match and match.group(2) else 0
    return hours * 60 + minutes

def save_by_major_genre(movies):
    if not movies:
        print("No movies to save by genre.")
        return

    major_genres = {
        'Action', 'Adventure', 'Comedy', 'Drama', 'Horror',
        'Sci-Fi', 'Romance', 'Thriller', 'Animation',
        'Fantasy', 'Crime', 'Mystery', 'Biography',
        'Documentary', 'Family', 'Musical'
    }

    genre_dict = {}

    for movie in movies:
        full_genres = movie.get('Genre', '')
        genres_list = [g.strip() for g in full_genres.split(',') if g.strip()]

        major = None
        for g in genres_list:
            if g.lower() in (mg.lower() for mg in major_genres):
                major = next(mg for mg in major_genres if mg.lower() == g.lower())
                break
        if not major:
            major = 'Unknown'

        genre_dict.setdefault(major, []).append(movie)

    for major_genre, items in genre_dict.items():
        safe_genre = major_genre.replace(' ', '_').replace('-', '_')
        filepath = os.path.join(OUTPUT_DIR, f"{safe_genre}_movies_2024.csv")
        df = pd.DataFrame(items)
        df.to_csv(filepath, index=False)
        print(f"Saved {len(items)} movies for major genre '{major_genre}' to '{filepath}'")

# def save_to_sql(movies, db_path='imdb_2024.db'):
#     if not movies:
#         print("No movies to save to SQL.")
#         return
#     import sqlite3
#     df = pd.DataFrame(movies)
#     conn = sqlite3.connect(db_path)
#     df.to_sql('movies_2024', conn, if_exists='replace', index=False)
#     print(f"Saved {len(movies)} records into SQLite DB at '{db_path}'")
#     conn.close()

def save_to_postgres(df, db_user, db_pass, db_host, db_port, db_name, table_name='movies_2024'):
    engine_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(engine_url)
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    print(f"Saved {len(df)} records into PostgreSQL table '{table_name}'")

def main():
    limit = 300  # or None
    max_workers = 20

    movies = scrape_search_results(limit=limit)
    if not movies:
        print("No movies scraped, exiting.")
        return

    movies = parallel_genre_duration_fetch(movies, max_workers=max_workers)

    # Clean and fill missing values
    for movie in movies:
        movie['Title'] = clean_title(movie.get('Title', ''))
        movie['Duration'] = duration_to_minutes(movie.get('Duration', ''))
        try:
            movie['Rating'] = float(movie.get('Rating', 0)) if movie.get('Rating') else 0.0
        except:
            movie['Rating'] = 0.0
        movie['Votes'] = movie.get('Votes') if movie.get('Votes') is not None else 0
        movie['Genre'] = movie.get('Genre', '')
        movie.pop('MovieURL', None)  # clean up if needed

    df_all = pd.DataFrame(movies)
    df_all.to_csv('imdb_2024_all_movies.csv', index=False)
    print(f"Saved all movies CSV with {len(movies)} records")

    save_by_major_genre(movies)
    # save_to_sql(movies)

    # Update PostgreSQL creds here:
    db_user = 'postgres'
    db_pass = '1312'
    db_host = 'localhost'
    db_port = 5433
    db_name = 'imdb'

    save_to_postgres(df_all, db_user, db_pass, db_host, db_port, db_name)

if __name__ == "__main__":
    main()
