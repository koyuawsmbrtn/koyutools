#!/usr/bin/env python3
"""
Anime/Series downloader for aniworld.to and s.to
Downloads episodes with German audio (data-lang-key="1") and sends URLs to jDownloader
Supports fallback to German subtitles or English subtitles if German audio not available
"""

import argparse
import random
import requests
import subprocess
import sys
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def parse_language_preferences(lang_string):
    """Parse language preference string into list of (key, name) tuples."""
    lang_mapping = {
        "1": "German audio",
        "2": "English subtitles", 
        "3": "German subtitles"
    }
    
    lang_keys = [key.strip() for key in lang_string.split(',')]
    preferences = []
    
    for key in lang_keys:
        if key in lang_mapping:
            preferences.append((key, lang_mapping[key]))
        else:
            print(f"Warning: Unknown language key '{key}', skipping")
    
    return preferences


def get_episode_url(content_name, season, episode, site="aniworld"):
    """Generate episode URL for the given anime/series, season, and episode."""
    if site == "aniworld":
        return f"https://aniworld.to/anime/stream/{content_name}/staffel-{season}/episode-{episode}"
    elif site == "sto":
        return f"https://s.to/serie/stream/{content_name}/staffel-{season}/episode-{episode}"
    else:
        raise ValueError(f"Unsupported site: {site}")


def main():
    parser = argparse.ArgumentParser(description='Download anime/series episodes from aniworld.to or s.to')
    parser.add_argument('content_name', help='Anime/series name (as it appears in the URL)')
    parser.add_argument('max_seasons', type=int, help='Maximum number of seasons to download')
    parser.add_argument('max_episodes', type=int, help='Maximum episodes per season to download')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--site', choices=['aniworld', 'sto'], default='aniworld', 
                       help='Site to scrape from: aniworld (aniworld.to) or sto (s.to) (default: aniworld)')
    parser.add_argument('--lang', type=str, default='1,3,2', 
                       help='Language preference order as comma-separated data-lang-keys (default: 1,3,2 = German audio, German subs, English subs)')
    
    args = parser.parse_args()
    
    # Parse language preferences
    preferred_langs = parse_language_preferences(args.lang)
    if not preferred_langs:
        print("Error: No valid language preferences specified")
        sys.exit(1)
    
    print(f"Language preference order: {', '.join([name for _, name in preferred_langs])}")
    
    # Create a session for connection reuse
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    download_links = []
    
    for season in range(1, args.max_seasons + 1):
        for episode in range(1, args.max_episodes + 1):
            url = get_episode_url(args.content_name, season, episode, args.site)
            print(f"Processing: S{season:02d}E{episode:02d} - {url}")
            
            try:
                # Get the episode page
                response = session.get(url)
                if response.status_code == 404:
                    print(f"  Episode not found (404), skipping remaining episodes for season {season}")
                    break
                elif response.status_code != 200:
                    print(f"  Error {response.status_code}, skipping")
                    continue
                
                # Parse the page to find preferred language link
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to find links in order of user-specified preference
                chosen_li = None
                chosen_lang_name = None
                
                for lang_key, lang_name in preferred_langs:
                    li_element = soup.find('li', {'data-lang-key': lang_key})
                    if li_element:
                        chosen_li = li_element
                        chosen_lang_name = lang_name
                        print(f"  Found {lang_name} option")
                        break
                
                if not chosen_li:
                    print(f"  No supported language options found")
                    continue
                
                # Find the link within this <li> element
                link = chosen_li.find('a', class_='watchEpisode')
                
                if not link:
                    print(f"  No watchEpisode link found in {chosen_lang_name} option")
                    continue
                
                # Get the href attribute
                relative_url = link.get('href')
                if not relative_url:
                    print(f"  No href found in {chosen_lang_name} link")
                    continue
                
                # Build full URL
                full_url = urljoin(url, relative_url)
                print(f"  Found {chosen_lang_name} link: {full_url}")
                
                # Follow the redirect to get actual download URL
                redirect_response = session.get(full_url, allow_redirects=False)
                if redirect_response.status_code in [301, 302, 303, 307, 308]:
                    final_url = redirect_response.headers.get('Location')
                    if final_url:
                        # Make absolute URL if needed
                        final_url = urljoin(full_url, final_url)
                        print(f"  Final download URL: {final_url}")
                        download_links.append(final_url)
                    else:
                        print(f"  No redirect location found")
                else:
                    # If no redirect, use the original URL
                    print(f"  No redirect, using original URL")
                    download_links.append(full_url)
                
                # Add delay between requests to be respectful
                time.sleep(args.delay)
                
            except requests.RequestException as e:
                print(f"  Request error: {e}")
                continue
            except Exception as e:
                print(f"  Unexpected error: {e}")
                continue
    
    # Send URLs to jDownloader via clipboard one by one
    if download_links:
        print(f"\nFound {len(download_links)} download links")
        print("Sending to jDownloader via clipboard (one by one with random delays)...")
        
        for i, url in enumerate(download_links, 1):
            try:
                # Use wl-copy to send to clipboard
                subprocess.run(['wl-copy'], input=url.encode('utf-8'), check=True)
                print(f"  [{i}/{len(download_links)}] Copied: {url}")
                
                # Wait random time between 1-3 seconds before next copy (except for last one)
                if i < len(download_links):
                    delay = random.uniform(1.0, 3.0)
                    print(f"    Waiting {delay:.1f}s before next copy...")
                    time.sleep(delay)
                    
            except subprocess.CalledProcessError as e:
                print(f"  Error copying to clipboard: {e}")
                print(f"  Failed URL: {url}")
            except FileNotFoundError:
                print("  wl-copy not found. Make sure wl-clipboard is installed.")
                print(f"  Failed URL: {url}")
                break
        
        print("Finished copying all URLs to clipboard for jDownloader")
    else:
        print("No download links found")


if __name__ == "__main__":
    main()
