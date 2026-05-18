# simu Dashboard

A Streamlit dashboard for the simu by Sakaza Afrika platform.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run app.py
```

The dashboard opens at **http://localhost:8501**

## Pages

| Page | Description |
|---|---|
| 📊 Overview | Live stats, response trend, channel donut, themes, map, and latest voices |
| 💬 Responses | Searchable & filterable full response table with CSV export |
| 🎙️ Voices | Community voice feed, filterable by theme and channel |
| 🗺️ Map | Scatter map of all response locations, coloured by channel or theme |
| 📈 Analytics | Activity heatmap, format breakdown, theme×channel stacked bar, channel trends |

## Next steps (connecting real data)

Replace `load_data()` in `app.py` with a real database query:

```python
import psycopg2  # or supabase, sqlalchemy, etc.

@st.cache_data(ttl=60)
def load_data():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    return pd.read_sql("SELECT * FROM responses ORDER BY created_at DESC", conn)
```

Store credentials in `.streamlit/secrets.toml`:

```toml
DATABASE_URL = "postgresql://user:password@host:5432/simu"
```

## Deployment

Deploy free to Streamlit Community Cloud:
1. Push this folder to a GitHub repo
2. Go to share.streamlit.io → New app → point to `app.py`
