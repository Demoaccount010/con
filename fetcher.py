import httpx

def search_jikan(query):
    try:
        clean = query.replace(".mkv", "").replace(".mp4", "").replace("_", " ").replace("-", " ")
        # Popularity sort se famous anime pehle aayega
        url = f"https://api.jikan.moe/v4/anime?q={clean}&limit=5&order_by=popularity"
        res = httpx.get(url, timeout=10)
        data = res.json()
        
        results = []
        if data.get('data'):
            for item in data['data']:
                # Priority: English Title > Default Title
                title_en = item.get('title_english') or item['title']
                
                results.append({
                    "title": title_en, # <--- FIXED: ENGLISH TITLE
                    "poster": item['images']['jpg']['large_image_url'],
                    "synopsis": item.get('synopsis', 'No details available.'),
                    "rating": str(item.get('score', 'N/A')),
                    "genres": ", ".join([g['name'] for g in item.get('genres', [])]),
                    "id": item['mal_id']
                })
        return results
    except Exception as e:
        print(f"Fetcher Error: {e}")
        return []
