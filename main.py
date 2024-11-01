from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)


def scrape_pitchfork():
    reviews = []
    url = 'https://pitchfork.com/reviews/albums/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    review_items = soup.find_all('div', class_='summary-item__icon-review-floating')
    
    for item in review_items:
        try:
            review_container = item.find_parent('div', class_='summary-item')
            if not review_container or 'Best New' not in review_container.text:
                continue
            
            link = review_container.find('a')
            if not link or 'href' not in link.attrs:
                continue
                
            review_url = f"https://pitchfork.com{link['href']}"
            
            heading = review_container.find(['h2', 'h3'])
            if not heading:
                continue
                
            review_type = 'Best New Album' if 'Best New Album' in review_container.text else 'Best New Reissue'
            
            # Remove genre tag if present
            text_content = heading.get_text(strip=True)
            if '  ' in text_content:
                text_content = text_content.split('  ', 1)[1]
            
            # Get the URL path
            url_path = link['href'].split('/')[-2]
            url_parts = url_path.split('-')
            
            if url_path.startswith('various-artists-'):
                artist = 'Various Artists'
                title = text_content
            else:
                # Check if the last part is a potential acronym
                if len(url_parts[-1]) <= 4 and url_parts[-1].lower() == url_parts[-1]:
                    artist = url_parts[-1].upper()
                    title = ' '.join(url_parts[:-1]).replace('-', ' ').title()
                else:
                    # Use the first two parts as artist name
                    artist = ' '.join(url_parts[:2]).replace('-', ' ').title()
                    title = text_content
                    # Remove artist name from title if present
                    if artist.lower() in title.lower():
                        title = title.lower().replace(artist.lower(), '').strip()
            
            if title and artist:
                title = title.strip().title()
                artist = artist.strip()
                
                reviews.append({
                    'title': title,
                    'artist': artist,
                    'rating': review_type,
                    'source': 'Pitchfork',
                    'url': review_url
                })
                
        except Exception as e:
            continue
    
    return reviews

def scrape_metacritic():
    reviews = []
    url = 'https://www.metacritic.com/music/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all clamp-metascore divs (these contain the full review info)
        review_items = soup.find_all('div', class_='clamp-metascore')
        
        for item in review_items:
            # Get the score
            score_div = item.find('div', class_='metascore_w')
            if not score_div:
                continue
                
            try:
                score = int(score_div.text.strip())
                if score >= 90:  # Only include very high scores
                    # Get the link element which contains both URL and title
                    link = item.find('a')
                    if link and 'href' in link.attrs:
                        url = f"https://www.metacritic.com{link['href']}"
                        
                        # The URL contains the album and artist info
                        # Format: /music/album-name/artist-name/critic-reviews
                        parts = link['href'].split('/')
                        if len(parts) >= 4:
                            title = parts[2].replace('-', ' ').title()
                            artist = parts[3].replace('-', ' ').title()
                            
                            reviews.append({
                                'title': title,
                                'artist': artist,
                                'rating': score,
                                'source': 'Metacritic',
                                'url': url
                            })
            except (ValueError, AttributeError):
                continue
    
    except requests.RequestException as e:
        print(f"Error accessing Metacritic: {e}")
    
    return reviews

def get_all_reviews():
    pitchfork_reviews = scrape_pitchfork()
    metacritic_reviews = scrape_metacritic()
    
    # Create a dictionary to store reviews by title and artist
    combined_reviews = {}
    
    # Process Pitchfork reviews
    for review in pitchfork_reviews:
        key = (review['title'].lower(), review['artist'].lower())
        combined_reviews[key] = {
            'title': review['title'],
            'artist': review['artist'],
            'rating': review['rating'],
            'source': 'Pitchfork',
            'url': review['url'],
            'trusted': False
        }
    
    # Process Metacritic reviews and check for duplicates
    for review in metacritic_reviews:
        key = (review['title'].lower(), review['artist'].lower())
        if key in combined_reviews:
            # Review exists in both sources - mark as trusted
            combined_reviews[key]['trusted'] = True
            combined_reviews[key]['metacritic_rating'] = review['rating']
        else:
            combined_reviews[key] = {
                'title': review['title'],
                'artist': review['artist'],
                'rating': review['rating'],
                'source': 'Metacritic',
                'url': review['url'],
                'trusted': False
            }
    
    return list(combined_reviews.values())

def main():
    reviews = get_all_reviews()
    
    print(f"Found {len(reviews)} highly rated albums:")
    for review in reviews:
        title_link = f"[{review['title']}]({review['url']})" if review.get('url') else review['title']
        # Format rating based on source
        rating = f"{review['rating']}/10" if review['source'] == 'Pitchfork' else f"{review['rating']}/100"
        print(f"{title_link} by {review['artist']} - {rating} ({review['source']})")

@app.route('/')
def index():
    reviews = get_all_reviews()
    return render_template('index.html', reviews=reviews)


