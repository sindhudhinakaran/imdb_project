import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import re

# Utils to expand genres
def expand_genres(df):
    # Explode genres: split by comma and explode to get one genre per row
    df = df.copy()
    df['GenreList'] = df['Genre'].fillna('').apply(lambda x: [g.strip() for g in x.split(',')])
    df_exp = df.explode('GenreList')
    return df_exp

# Load Data (adjust path as needed)
@st.cache_data
def load_data():
    df = pd.read_csv('imdb_2024_all_movies.csv')
    # Ensure proper types
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce').fillna(0).astype(int)
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)
    df['Votes'] = pd.to_numeric(df['Votes'], errors='coerce').fillna(0).astype(int)
    return df

df = load_data()
df_exp = expand_genres(df)

st.title("IMDb 2024 Movie Insights")

# --- Sidebar for Filters ---
st.sidebar.header("Filter Movies")

# Duration filter options
dur_options = {"< 2 hours": 0, "2 - 3 hours": 1, "> 3 hours": 2}
dur_choice = st.sidebar.multiselect(
    "Select Duration (hours)",
    options=dur_options.keys(),
    default=list(dur_options.keys()),
    key='duration_multiselect'
)

def duration_filter(duration_minutes):
    try:
        hours = duration_minutes / 60
    except Exception:
        return False  # Exclude if invalid

    conditions = []
    if "< 2 hours" in dur_choice:
        conditions.append(hours < 2)
    if "2 - 3 hours" in dur_choice:
        conditions.append((hours >= 2) & (hours <= 3))
    if "> 3 hours" in dur_choice:
        conditions.append(hours > 3)
    return any(conditions) if conditions else True  # If no filter selected, keep all

# Rating Filter
min_rating = st.sidebar.slider(
    "Minimum IMDb Rating",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.1,
    key='min_rating_slider'
)

# Votes Filter
min_votes = st.sidebar.number_input(
    "Minimum Number of Votes",
    min_value=0,
    value=0,
    step=1000,
    key='min_votes_input'
)

# Genre Filter
all_genres = sorted(df_exp['GenreList'].dropna().unique())
selected_genres = st.sidebar.multiselect(
    "Select Genre(s)",
    options=all_genres,
    default=all_genres,
    key='genre_multiselect'
)

# Apply Filters
filtered_df = df[
    (df['Duration'].apply(duration_filter)) &
    (df['Rating'] >= min_rating) &
    (df['Votes'] >= min_votes)
].copy()

if selected_genres:
    filtered_exp = df_exp[df_exp['GenreList'].isin(selected_genres)]
    filtered_df = filtered_df[filtered_df['Title'].isin(filtered_exp['Title'].unique())]

st.sidebar.markdown(f"### Showing {len(filtered_df)} movies after filtering")

# --- Main Panels ---

# 1. Top 10 Movies by Rating and Voting Counts
st.subheader("Top 10 Movies by Rating and Votes")
top10 = filtered_df.sort_values(['Rating', 'Votes'], ascending=[False, False]).head(10)
st.dataframe(top10[['Title', 'Rating', 'Votes', 'Genre', 'Duration']])

# 2. Genre Distribution: count of movies per genre (using filtered)
st.subheader("Genre Distribution")
genre_counts = filtered_df['Genre'].str.split(',').explode().str.strip().value_counts()
fig_bar = px.bar(
    x=genre_counts.index,
    y=genre_counts.values,
    labels={"x": "Genre", "y": "Number of Movies"},
    title="Number of Movies per Genre"
)
st.plotly_chart(fig_bar, use_container_width=True)

# 3. Average Duration by Genre
st.subheader("Average Duration by Genre (minutes)")
avg_duration = df_exp.groupby('GenreList')['Duration'].mean().sort_values()
fig_hbar = px.bar(
    avg_duration,
    x=avg_duration.values,
    y=avg_duration.index,
    orientation='h',
    labels={"x": "Average Duration (min)", "y": "Genre"},
    title="Average Movie Duration by Genre"
)
st.plotly_chart(fig_hbar, use_container_width=True)

# 4. Voting Trends by Genre: avg votes per genre
st.subheader("Average Voting Counts by Genre")
avg_votes = df_exp.groupby('GenreList')['Votes'].mean().sort_values(ascending=False)
fig_votes = px.bar(
    avg_votes,
    x=avg_votes.index,
    y=avg_votes.values,
    labels={"x": "Genre", "y": "Average Votes"},
    title="Average Voting Counts per Genre"
)
st.plotly_chart(fig_votes, use_container_width=True)

# 5. Rating Distribution - Histogram
st.subheader("IMDb Rating Distribution")
fig_hist = px.histogram(
    filtered_df,
    x='Rating',
    nbins=20,
    labels={"Rating": "IMDb Rating"},
    title="Distribution of IMDb Ratings"
)
st.plotly_chart(fig_hist, use_container_width=True)

# Alternative boxplot for all movies' rating
st.subheader("IMDb Rating Boxplot")
fig_box = px.box(filtered_df, y='Rating', points="all")
st.plotly_chart(fig_box, use_container_width=True)

# 6. Genre-Based Rating Leaders (top rated movie per major genre)
st.subheader("Top Rated Movie by Major Genre")

# Define major genres (consistent with your earlier major_genres)
major_genres = {
    'Action', 'Adventure', 'Comedy', 'Drama', 'Horror',
    'Sci-Fi', 'Romance', 'Thriller', 'Animation',
    'Fantasy', 'Crime', 'Mystery', 'Biography',
    'Documentary', 'Family', 'Musical'
}

leaders = []
for genre in major_genres:
    movies_in_genre = [m for m in filtered_df.itertuples() if genre.lower() in (g.strip().lower() for g in getattr(m, "Genre", "").split(","))]
    if movies_in_genre:
        best = max(movies_in_genre, key=lambda x: x.Rating if x.Rating else 0)
        leaders.append({
            "Genre": genre,
            "Title": best.Title,
            "Rating": best.Rating,
            "Votes": best.Votes,
            "Duration": best.Duration
        })
df_leaders = pd.DataFrame(leaders).sort_values('Genre')
st.table(df_leaders)

# 7. Most Popular Genres by Voting (pie chart)
st.subheader("Most Popular Genres by Total Votes")
total_votes_by_genre = df_exp.groupby('GenreList')['Votes'].sum().sort_values(ascending=False)
fig_pie = px.pie(
    names=total_votes_by_genre.index,
    values=total_votes_by_genre.values,
    title="Total Votes by Genre"
)
st.plotly_chart(fig_pie, use_container_width=True)

# 8. Duration Extremes
st.subheader("Duration Extremes")
min_dur_movie = filtered_df[filtered_df['Duration'] == filtered_df['Duration'].min()]
max_dur_movie = filtered_df[filtered_df['Duration'] == filtered_df['Duration'].max()]
st.markdown("**Shortest movie(s):**")
st.table(min_dur_movie[['Title', 'Duration', 'Genre', 'Rating', 'Votes']])

st.markdown("**Longest movie(s):**")
st.table(max_dur_movie[['Title', 'Duration', 'Genre', 'Rating', 'Votes']])

# 9. Ratings by Genre (heatmap)
st.subheader("Genre-Ratings Heatmap")

genre_rating_matrix = []
for genre in major_genres:
    movies_in_genre = [m for m in df_exp.itertuples() if genre.lower() == m.GenreList.strip().lower()]
    if movies_in_genre:
        avg_rating = np.mean([m.Rating for m in movies_in_genre])
    else:
        avg_rating = np.nan
    genre_rating_matrix.append((genre, avg_rating))

heatmap_df = pd.DataFrame(genre_rating_matrix, columns=['Genre', 'AvgRating']).set_index('Genre')
fig_heatmap, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(heatmap_df.T, annot=True, cmap='YlGnBu', cbar_kws={'label': 'Avg IMDb Rating'}, vmin=0, vmax=10, linewidths=0.5)
ax.set_xlabel('Genre')
ax.set_ylabel('')
st.pyplot(fig_heatmap)

# 10. Correlation Analysis
st.subheader("Ratings vs Voting Counts Scatter Plot")
fig_scatter = px.scatter(
    filtered_df,
    x='Votes',
    y='Rating',
    hover_name='Title',
    labels={'Votes': 'Number of Votes', 'Rating': 'IMDb Rating'},
    title='Correlation Between Number of Votes and Rating',
    trendline="ols"
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Display filtered DataFrame
st.subheader("Filtered Movie Data")
st.dataframe(filtered_df[['Title', 'Duration', 'Rating', 'Votes', 'Genre']].reset_index(drop=True))
