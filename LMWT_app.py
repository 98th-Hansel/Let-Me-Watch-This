import sys
import os
import vlc
import sqlite3
import subprocess
import requests
import hashlib
import ctypes
import re
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSlider, QStyle, QMenu
from PyQt6.QtWidgets import QScrollArea, QHBoxLayout, QPushButton, QSizePolicy, QGridLayout, QFrame, QStackedWidget, QStackedLayout
from PyQt6.QtWidgets import QComboBox, QListWidget, QListWidgetItem, QFileDialog
from PyQt6.QtGui import QPixmap, QCursor, QIcon
from PyQt6.QtCore import Qt, QTimer, QRect, QUrl
from datetime import datetime
from bs4 import BeautifulSoup

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

#---------------------------------------------------------------------------------------------------
def find_poster(folder_path, filename=None):
    # Case 1: specific file poster
    if filename:
        name = os.path.splitext(filename)[0]
        for ext in IMAGE_EXTENSIONS:
            poster_path = os.path.join(folder_path, name + ext)
            if os.path.exists(poster_path):
                return poster_path
    # Case 2: folder poster named after the folder itself
    folder_name = os.path.basename(folder_path)
    for ext in IMAGE_EXTENSIONS:
        poster_path = os.path.join(folder_path, folder_name + ext)
        if os.path.exists(poster_path):
            return poster_path
    # Case 3: folder poster
    for file in os.listdir(folder_path):
        if file.lower().startswith("poster") or file.lower().endswith(IMAGE_EXTENSIONS):
            return os.path.join(folder_path, file)
    # Case 4: Search Online
    print(f"🔍 No local poster found for: {os.path.basename(folder_path)}")
    
    # Determine if this is a movie or TV show
    media_type = "movie"
    if "tv" in folder_path.lower() or "show" in folder_path.lower():
        media_type = "tv"
    
    folder_name = os.path.basename(folder_path)
    return find_poster_online(folder_name, folder_path, media_type)
#---------------------------------------------------------------------------------------------------

    """Find poster online and cache it locally."""
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").rstrip()
    cache_path = os.path.join(folder_path, f"{safe_name}_poster.jpg")
    
    # Check if already cached
    if os.path.exists(cache_path):
        return cache_path
    
    # Search online
    poster_url = search_wikipedia_image(title, media_type)
    
    if poster_url:
        if download_poster(poster_url, cache_path):
            return cache_path
    
    return None
#---------------------------------------------------------------------------------------------------
def search_image_poster(query, media_type="movie"):
    """
    Search for a poster using TMDB's public page.
    """
    try:
        import urllib.parse
        
        print(f"🔍 Searching for: '{query}'")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Direct TMDB search URL
        encoded_query = urllib.parse.quote(query)
        tmdb_url = f"https://www.themoviedb.org/search/{media_type}?query={encoded_query}"
        
        response = requests.get(tmdb_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ TMDB returned status {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for poster images - they have specific patterns in the URL
        for img in soup.find_all('img'):
            src = img.get('src', '')
            
            # TMDB poster images contain these patterns
            if src and 'media.themoviedb.org' in src:
                # Convert thumbnail to full poster size
                # Change w94_and_h141_face to w500
                full_url = re.sub(r'/w\d+_and_h\d+_face/', '/w500/', src)
                # Also try other size patterns
                full_url = re.sub(r'/w\d+/', '/w500/', full_url)
                
                if full_url != src:  # Only if we changed something
                    print(f"  ✅ Found poster: {full_url}")
                    return full_url
        
        print("  ❌ No poster images found")
        
    except Exception as e:
        print(f"  ❌ Search error: {e}")
    
    return None
def find_poster_online(title, folder_path, media_type="movie"):
    """Find poster online and cache it locally."""
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").rstrip()
    cache_path = os.path.join(folder_path, f"{safe_name}_poster.jpg")
    
    print(f"  📁 Cache path: {cache_path}")
    
    if os.path.exists(cache_path):
        print(f"  ✅ Found cached poster")
        return cache_path
    
    poster_url = search_image_poster(title, media_type)
    
    if poster_url:
        print(f"  ⬇️ Downloading poster...")
        if download_poster(poster_url, cache_path):
            print(f"  ✅ Poster saved")
            return cache_path
    
    return None
def download_poster(url, save_path):
    """
    Download a poster from a URL and save it as a file.
    
    Args:
        url: The web address of the image to download
        save_path: Where to save the file on your computer
    
    Returns:
        True if successful, False if failed
    """
    try:
        headers = {"User-Agent": "LMWT/1.0"}
        # Send a request to get the image
        response = requests.get(url, headers=headers, timeout=15)
        
        # If the request was successful (status code 200)
        if response.status_code == 200:
            # Write the image data to a file
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Download error: {e}")
    return False
#---------------------------------------------------------------------------------------------------
def create_movie_tile(movie, click_handler, delete_handler=None):
    tile = QWidget()
    tile.setFixedHeight(300)  # Fixed height to prevent vertical stretching
    tile.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    layout = QVBoxLayout()
    layout.setSpacing(5)
    layout.setContentsMargins(0, 0, 0, 0)
    tile.setLayout(layout)
    tile.setStyleSheet("""QWidget {
                       background-color: transparent;}""")

    #Poster - wrap in a centered horizontal layout
    poster_container = QHBoxLayout()
    poster_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    poster_label = QLabel()
    poster_label.setFixedSize(180, 240)

    # Create overlay for dimming effect
    poster_overlay = QWidget(poster_label)
    poster_overlay.setGeometry(0, 0, 180, 240)
    poster_overlay.setStyleSheet("background-color: transparent; border-radius: 8px;")
    poster_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    if movie["poster"] and os.path.exists(movie["poster"]):
        pixmap = QPixmap(movie["poster"])
        poster_label.setPixmap(pixmap.scaled(180, 240, 
                                             Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                             Qt.TransformationMode.SmoothTransformation))
    else:
        poster_label.setStyleSheet("""
                                   background-color: #333;
                                   border-radius: 8px;""")
        poster_label.setText("No Image")
        poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    poster_container.addWidget(poster_label)
    
    # Delete button (top-right corner, hidden by default)
    delete_btn = None
    if delete_handler:
        delete_btn = QPushButton("✕", poster_label)
        delete_btn.setGeometry(150, 5, 30, 30)
        delete_btn.setStyleSheet("""
                                 QPushButton {
                                 background-color: rgba(0, 0, 0, 180);
                                 color: white;
                                 border: none;
                                 border-radius: 15px;
                                 font-size: 14px;
                                 font-weight: bold;
                                 }
                                 QPushButton:hover {
                                 background-color: rgba(255, 0, 0, 200);
                                 }
                                 """)
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Use a lambda with default argument to capture the movie
        delete_btn.clicked.connect(lambda checked, m=movie: delete_handler(m))
        delete_btn.hide()

    # Title - centered and constrained
    title_label = QLabel(movie["title"])
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("font-size: 14px; color: white; background-color: transparent;")
    title_label.setMaximumWidth(200)
    title_label.setMaximumHeight(50)  # Limit title height

    #Add Widgets
    layout.addLayout(poster_container)
    layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignCenter)
    
    # Hover enter event - dim poster and highlihgt title
    def enterEvent(event):
        poster_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 100); border-radius: 8px;")
        title_label.setStyleSheet("font-size: 14px; color: #0099ff; background-color: transparent;")
        if delete_btn:
            delete_btn.show()
        tile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # Hand on hover
    
    # Hover leave event - restore
    def leaveEvent(event):
        poster_overlay.setStyleSheet("background-color: transparent; border-radius: 8px;")
        title_label.setStyleSheet("font-size: 14px; color: white; background-color: transparent;")
        if delete_btn:
            delete_btn.hide()
        tile.setCursor(QCursor(Qt.CursorShape.ArrowCursor))  # Default arrow when leaving
    
    tile.enterEvent = enterEvent
    tile.leaveEvent = leaveEvent

    #click handling
    def tile_click(event):
        if delete_btn and delete_btn.isVisible():
            # Dont trigger if clicking the delete button
            return
        click_handler([movie])
    
    poster_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    poster_label.mousePressEvent = lambda event, m=movie: click_handler([m])
    title_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    title_label.mousePressEvent = lambda event, m=movie: click_handler([m])

    return tile
#---------------------------------------------------------------------------------------------------
def scan_movies(folder_path):
    movies = []

    #if folder not found break out
    if not os.path.exists(folder_path):
        print(f"Movies path not found: {folder_path}")
        return movies
    
    for genre in os.listdir(folder_path):
        genre_path = os.path.join(folder_path, genre)

        if not os.path.isdir(genre_path):
            continue

        for item in sorted(os.listdir(genre_path)):
            item_path = os.path.join(genre_path, item)

            # Case 1: Movies found in folder
            if os.path.isfile(item_path) and item.lower().endswith(VIDEO_EXTENSIONS):
                poster = find_poster(genre_path, item)
                movies.append({"title": os.path.splitext(item)[0],
                              "path": item_path,
                              "genre": genre,
                              "franchise": None,
                              "poster": poster})
            
            # Case 2: Movie Franchise Folder Found
            elif os.path.isdir(item_path):
                franchise_name = item

                for file in sorted(os.listdir(item_path)):
                    file_path = os.path.join(item_path, file)

                    if file.lower().endswith(VIDEO_EXTENSIONS):
                        poster = find_poster(item_path, file)
                        movies.append({
                            "title": os.path.splitext(file)[0],
                            "path": file_path,
                            "genre": genre,
                            "franchise": franchise_name,
                            "poster": poster})
    
    return movies
#---------------------------------------------------------------------------------------------------
def scan_tv(folder_path):
    """
    Scan TV folder structure and return show titles with their genres.
    Expected structure: tv_path -> Genre -> Show Title
    
    Returns a list of dictionaries with show title and genre.
    """
    shows = []

    # If folder not found break out
    if not os.path.exists(folder_path):
        print(f"Shows path not found: {folder_path}")
        return shows
    
    for genre in os.listdir(folder_path):
        genre_path = os.path.join(folder_path, genre)

        if not os.path.isdir(genre_path):
            continue

        for show_name in sorted(os.listdir(genre_path)):
            show_path = os.path.join(genre_path, show_name)

            if not os.path.isdir(show_path):
                continue

            # Find poster image in the show folder
            poster = find_poster(show_path)

            # For now, just store the show title and genre
            shows.append({
                "title": show_name,
                "genre": genre,
                "path": show_path,
                "poster": poster
            })
    
    return shows
#---------------------------------------------------------------------------------------------------
def scan_tv_seasons(show_path):
    """
    Scan a TV show folder for seasons and episodes
    show_path -> season X -> episodes
    
    Args:
        Show_path: Path to the TV show folder
        
    Returns:
        dict: seasons with their episodes
        format: {"season 1": [{"title": "Episode Name", "path": "..."}],...}
        """
    seasons = {}

    if not os.path.exists(show_path):
        print(f"Show path not found: {show_path}")
        return seasons
    
    for item in sorted(os.listdir(show_path)):
        item_path = os.path.join(show_path, item)

        # Skip files (like poster images)
        if not os.path.isdir(item_path):
            continue

        # Scan for video files in this folder
        episodes = []
        for file in sorted(os.listdir(item_path)):
            if file.lower().endswith(VIDEO_EXTENSIONS):
                episodes.append({
                    "title": os.path.splitext(file)[0],
                    "path": os.path.join(item_path, file)
                })
        
        # if episodes found, consider this a season folder
        if episodes:
            seasons[item] = episodes
    
    return seasons
#---------------------------------------------------------------------------------------------------
def group_movies(movies):
    grouped = {}

    for movie in movies:
        genre = movie["genre"]
        franchise = movie["franchise"]

        if genre not in grouped:
            grouped[genre] = {}
        
        # Group Key (franchise or singles)
        key = franchise if franchise else movie["title"]

        if key not in grouped[genre]:
            grouped[genre][key] = []
        
        grouped[genre][key].append(movie)

    return grouped
#---------------------------------------------------------------------------------------------------
def create_movies_browse_page(movies_list, click_handler, title="Movies", switch_to_tv_callback=None, switch_to_home_callback=None, movies_folder_callback=None, search_callback=None):
    """
    Create a browse page widget with movie tiles in a scrollable grid.
    
    Args:
        movies_list: List of movie dictionaries from scan_movies()
        click_handler: Function to call when a movie tile is clicked
        title: Optional title for the page
    
    Returns:
        QWidget: The complete browse page widget
    """
    COLUMNS = 6
    
    # Create main page widget
    browse_page = QWidget()
    browse_layout = QVBoxLayout()
    browse_layout.setContentsMargins(0, 0, 0, 0)
    browse_layout.setSpacing(0)
    browse_page.setLayout(browse_layout)

    # =========================
    # 🏠 MENU BAR (Fixed at top)
    # =========================
    menu_bar = QWidget()
    menu_bar.setFixedHeight(60)
    menu_bar.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            border-bottom: 2px solid #333;
        }
    """)
    
    menu_layout = QHBoxLayout()
    menu_layout.setContentsMargins(20, 10, 20, 10)
    menu_layout.setSpacing(20)
    menu_bar.setLayout(menu_layout)
    
    # Menu title/logo (left side)
    logo_label = QLabel(title)
    logo_label.setStyleSheet("""
        color: white;
        font-size: 24px;
        font-weight: bold;
        border: none;
    """)
    
    # Navigation buttons
    nav_buttons_layout = QHBoxLayout()
    nav_buttons_layout.setSpacing(15)
    
    home_btn = QPushButton("Home")
    home_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    home_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    movies_btn = QPushButton("Movies")
    movies_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #0099ff;
            border: none;
            font-size: 16px;
            font-weight: bold;
            padding: 5px 15px;
            border-bottom: 2px solid #0099ff;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    movies_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    tv_shows_btn = QPushButton("TV Shows")
    tv_shows_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            color: white;      
        }
    """)
    tv_shows_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    nav_buttons_layout.addWidget(home_btn)
    nav_buttons_layout.addWidget(movies_btn)
    nav_buttons_layout.addWidget(tv_shows_btn)
    
    if switch_to_home_callback:
        home_btn.clicked.connect(switch_to_home_callback)
    if switch_to_tv_callback:
        tv_shows_btn.clicked.connect(switch_to_tv_callback)

    # Spacer
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    
    # Right side items
    right_side_layout = QHBoxLayout()
    right_side_layout.setSpacing(10)
    
    search_btn = QPushButton("🔍")
    search_btn.setFixedSize(40, 40)
    search_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 18px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 10);
            color: white;
        }
    """)
    search_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    folder_btn = QPushButton("📁")
    folder_btn.setFixedSize(40, 40)
    folder_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 18px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 10);
            color: white;
        }
    """)
    folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if movies_folder_callback:
        folder_btn.clicked.connect(movies_folder_callback)

    right_side_layout.addWidget(search_btn)
    right_side_layout.addWidget(folder_btn)
    
    # Assemble menu bar
    menu_layout.addWidget(logo_label)
    menu_layout.addLayout(nav_buttons_layout)
    menu_layout.addWidget(spacer)
    menu_layout.addLayout(right_side_layout)

    # =========================
    # 🔍 SEARCH BAR (hidden by default)
    # =========================
    search_bar = create_search_bar(
        lambda text: filter_grid(text),
        lambda: toggle_search()
    )
    search_bar.hide()
    browse_layout.addWidget(search_bar)

    # =========================
    # 📜 SCROLLABLE CONTENT AREA
    # =========================
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: #222222;
        }
        QWidget {
            background-color: #222222;
        }
    """)

    scroll_container = QWidget()
    scroll_container.setStyleSheet("background-color: #222222;")
    scroll_layout = QVBoxLayout()
    scroll_layout.setSpacing(20)
    scroll_layout.setContentsMargins(20, 20, 20, 20)
    scroll_container.setLayout(scroll_layout)

    scroll.setWidget(scroll_container)

    # Grid
    grid_container = QWidget()
    grid_container.setStyleSheet("background-color: transparent;")
    grid_container.setMinimumWidth(COLUMNS * 215)
    grid_layout = QGridLayout()
    grid_layout.setSpacing(15)
    grid_container.setLayout(grid_layout)

    scroll_layout.addWidget(grid_container)

    # Store all tiles for efficient filtering
    all_tiles = []
    
    # Populate grid initially
    for index, movie in enumerate(movies_list):
        row = index // COLUMNS
        col = index % COLUMNS
        tile = create_movie_tile(movie, click_handler)
        grid_layout.addWidget(tile, row, col)
        all_tiles.append((tile, movie))

    # Add stretch to push grid to top
    scroll_layout.addStretch()

    # Filter function - hide/show instead of rebuilding
    def filter_grid(search_text):
        search_lower = search_text.lower().strip()
        
        # Remove all widgets from grid
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(0)
            if item and item.widget():
                grid_layout.removeWidget(item.widget())
        
        if not search_lower:
            # No search - restore original positions
            for index, (tile, _) in enumerate(all_tiles):
                tile.show()
                row = index // COLUMNS
                col = index % COLUMNS
                grid_layout.addWidget(tile, row, col)
        else:
            # Add only matching tiles
            visible_index = 0
            for tile, movie in all_tiles:
                if search_lower in movie["title"].lower():
                    tile.show()
                    row = visible_index // COLUMNS
                    col = visible_index % COLUMNS
                    grid_layout.addWidget(tile, row, col)
                    visible_index += 1
                else:
                    tile.hide()
    # Toggle search function
    def toggle_search():
        if search_bar.isVisible():
            search_bar.hide()
            search_bar.search_input.clear()
            filter_grid("")
        else:
            search_bar.show()
            search_bar.search_input.setFocus()
    
    # Connect search button
    search_btn.clicked.connect(lambda: toggle_search())
    
    # =========================
    # ASSEMBLE PAGE
    # =========================
    browse_layout.addWidget(menu_bar)
    browse_layout.addWidget(scroll)

    return browse_page
#---------------------------------------------------------------------------------------------------
def create_tv_browse_page(tv_shows_list, click_handler, title="TV Shows", switch_to_movies_callback=None, switch_to_home_callback=None, tv_folder_callback=None, search_callback=None):
    """
    Create a browse page widget for TV shows with show tiles in a scrollable grid.
    
    Args:
        tv_shows_list: List of TV show dictionaries from scan_tv()
        click_handler: Function to call when a show tile is clicked
        title: Optional title for the page
    
    Returns:
        QWidget: The complete browse page widget
    """
    COLUMNS = 6
    
    # Create main page widget
    browse_page = QWidget()
    browse_layout = QVBoxLayout()
    browse_layout.setContentsMargins(0, 0, 0, 0)
    browse_layout.setSpacing(0)
    browse_page.setLayout(browse_layout)

    # =========================
    # 🏠 MENU BAR (Fixed at top)
    # =========================
    menu_bar = QWidget()
    menu_bar.setFixedHeight(60)
    menu_bar.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            border-bottom: 2px solid #333;
        }
    """)
    
    menu_layout = QHBoxLayout()
    menu_layout.setContentsMargins(20, 10, 20, 10)
    menu_layout.setSpacing(20)
    menu_bar.setLayout(menu_layout)
    
    # Menu title/logo (left side)
    logo_label = QLabel(title)
    logo_label.setStyleSheet("""
        color: white;
        font-size: 24px;
        font-weight: bold;
        border: none;
    """)
    
    # Navigation buttons
    nav_buttons_layout = QHBoxLayout()
    nav_buttons_layout.setSpacing(15)
    
    home_btn = QPushButton("Home")
    home_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    home_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    movies_btn = QPushButton("Movies")
    movies_btn.setStyleSheet("""
        QPushButton{
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
            }
        QPushButton:hover{
            color: white;
        }
    """)
    movies_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if switch_to_home_callback:
        home_btn.clicked.connect(switch_to_home_callback)
    if switch_to_movies_callback:
        movies_btn.clicked.connect(switch_to_movies_callback)

    tv_shows_btn = QPushButton("TV Shows")
    tv_shows_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #0099ff;
            border: none;
            font-size: 16px;
            font-weight: bold;
            padding: 5px 15px;
            border-bottom: 2px solid #0099ff;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    tv_shows_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    nav_buttons_layout.addWidget(home_btn)
    nav_buttons_layout.addWidget(movies_btn)
    nav_buttons_layout.addWidget(tv_shows_btn)
    
    # Spacer
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    
    # Right side items
    right_side_layout = QHBoxLayout()
    right_side_layout.setSpacing(10)
    
    search_btn = QPushButton("🔍")
    search_btn.setFixedSize(40, 40)
    search_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 18px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 10);
            color: white;
        }
    """)
    search_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    folder_btn = QPushButton("📁")
    folder_btn.setFixedSize(40, 40)
    folder_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 18px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 10);
            color: white;
        }
    """)
    folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if tv_folder_callback:
        folder_btn.clicked.connect(tv_folder_callback)

    right_side_layout.addWidget(search_btn)
    right_side_layout.addWidget(folder_btn)
    
    # Assemble menu bar
    menu_layout.addWidget(logo_label)
    menu_layout.addLayout(nav_buttons_layout)
    menu_layout.addWidget(spacer)
    menu_layout.addLayout(right_side_layout)
    
    # =========================
    # Search bar
    # =========================
    search_bar = create_search_bar(
        lambda text: filter_grid(text),
        lambda: toggle_search()
    )
    search_bar.hide()
    browse_layout.addWidget(search_bar)

    # =========================
    # 📜 SCROLLABLE CONTENT AREA
    # =========================
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded) # Check movie browse page
    scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: #222222;
        }
        QWidget {
            background-color: #222222;
        }
    """)

    scroll_container = QWidget()
    scroll_container.setStyleSheet("background-color: #222222;")
    scroll_layout = QVBoxLayout()
    scroll_layout.setSpacing(20)
    scroll_layout.setContentsMargins(20, 20, 20, 20)
    scroll_container.setLayout(scroll_layout)

    scroll.setWidget(scroll_container)

    # Grid
    grid_container = QWidget()
    grid_container.setStyleSheet("background-color: transparent;")
    grid_container.setMinimumWidth(COLUMNS * 215)
    grid_layout = QGridLayout()
    grid_layout.setSpacing(15)
    grid_container.setLayout(grid_layout)

    scroll_layout.addWidget(grid_container)

    # Store all tiles for efficient filtering
    all_tiles = []

    # Populate grid initially
    for index, show in enumerate(tv_shows_list):
        row = index // COLUMNS
        col = index % COLUMNS
        tile = create_movie_tile(show, click_handler)
        grid_layout.addWidget(tile, row, col)
        all_tiles.append((tile, show))

    # Add stretch to push grid to top
    scroll_layout.addStretch()
    # Filter function - hide/show instead of rebuilding
    # Filter function - hide/show instead of rebuilding
    # Filter function - hide/show instead of rebuilding
    def filter_grid(search_text):
        search_lower = search_text.lower().strip()
        
        # Remove all widgets from grid
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(0)
            if item and item.widget():
                grid_layout.removeWidget(item.widget())
        
        if not search_lower:
            # No search - restore original positions
            for index, (tile, _) in enumerate(all_tiles):
                tile.show()
                row = index // COLUMNS
                col = index % COLUMNS
                grid_layout.addWidget(tile, row, col)
        else:
            # Add only matching tiles
            visible_index = 0
            for tile, movie in all_tiles:
                if search_lower in movie["title"].lower():
                    tile.show()
                    row = visible_index // COLUMNS
                    col = visible_index % COLUMNS
                    grid_layout.addWidget(tile, row, col)
                    visible_index += 1
                else:
                    tile.hide()
    # Toggle search function
    def toggle_search():
        if search_bar.isVisible():
            search_bar.hide()
            search_bar.search_input.clear()
            filter_grid("")
        else:
            search_bar.show()
            search_bar.search_input.setFocus()
    
    # Connect search button
    search_btn.clicked.connect(lambda: toggle_search())
    # =========================
    # ASSEMBLE PAGE
    # =========================
    browse_layout.addWidget(menu_bar)  # Menu bar first = at top
    browse_layout.addWidget(scroll)     # Scroll area second = below menu bar

    return browse_page
#---------------------------------------------------------------------------------------------------
def create_home_page(switch_to_movies_callback=None, switch_to_tv_callback=None, continue_watching_items=None, continue_click_handler=None, clear_all_callback=None, delete_item_callback=None):
    """
    Create the Home page widget with continue watching and recently added sections.
    For now, this is a blank page with navigation.
    
    Args:
        switch_to_movies_callback: Function to call when Movies button is clicked
        switch_to_tv_callback: Function to call when TV Shows button is clicked
    
    Returns:
        QWidget: The complete home page widget
    """
    # Create main page widget
    home_page = QWidget()
    home_layout = QVBoxLayout()
    home_layout.setContentsMargins(0, 0, 0, 0)
    home_layout.setSpacing(0)
    home_page.setLayout(home_layout)

    # =========================
    # 🏠 MENU BAR (Fixed at top)
    # =========================
    menu_bar = QWidget()
    menu_bar.setFixedHeight(60)
    menu_bar.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            border-bottom: 2px solid #333;
        }
    """)
    
    menu_layout = QHBoxLayout()
    menu_layout.setContentsMargins(20, 10, 20, 10)
    menu_layout.setSpacing(20)
    menu_bar.setLayout(menu_layout)
    
    # Menu title/logo (left side)
    logo_label = QLabel("🏠︎")
    logo_label.setStyleSheet("""
        color: white;
        font-size: 24px;
        font-weight: bold;
        border: none;
    """)
    
    # Navigation buttons
    nav_buttons_layout = QHBoxLayout()
    nav_buttons_layout.setSpacing(15)
    
    home_btn = QPushButton("Home")
    home_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #0099ff;
            border: none;
            font-size: 16px;
            font-weight: bold;
            padding: 5px 15px;
            border-bottom: 2px solid #0099ff;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    home_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    movies_btn = QPushButton("Movies")
    movies_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    movies_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if switch_to_movies_callback:
        movies_btn.clicked.connect(switch_to_movies_callback)
    
    tv_shows_btn = QPushButton("TV Shows")
    tv_shows_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 16px;
            padding: 5px 15px;
        }
        QPushButton:hover {
            color: white;
        }
    """)
    tv_shows_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if switch_to_tv_callback:
        tv_shows_btn.clicked.connect(switch_to_tv_callback)
    
    nav_buttons_layout.addWidget(home_btn)
    nav_buttons_layout.addWidget(movies_btn)
    nav_buttons_layout.addWidget(tv_shows_btn)
    
    # Spacer
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    
    # Right side items
    right_side_layout = QHBoxLayout()
    right_side_layout.setSpacing(10)

    
    # Assemble menu bar
    menu_layout.addWidget(logo_label)
    menu_layout.addLayout(nav_buttons_layout)
    menu_layout.addWidget(spacer)
    menu_layout.addLayout(right_side_layout)
    
    # =========================
    # 📜 SCROLLABLE CONTENT AREA
    # =========================
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: #222222;
        }
        QWidget {
            background-color: #222222;
        }
    """)

    scroll_container = QWidget()
    scroll_container.setStyleSheet("background-color: #222222;")
    scroll_layout = QVBoxLayout()
    scroll_layout.setSpacing(20)
    scroll_layout.setContentsMargins(40, 40, 40, 40)
    scroll_container.setLayout(scroll_layout)

    scroll.setWidget(scroll_container)

    # Placeholder content
    placeholder_label = QLabel("o/")
    placeholder_label.setStyleSheet("""
        color: #aaa;
        font-size: 24px;
        padding: 50px;
    """)
    placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    placeholder_label.setWordWrap(True)
    
    scroll_layout.addWidget(placeholder_label)
    # =========================
    # Continue Watching
    # =========================
    continue_watching_panel = QWidget()
    continue_watching_panel.setStyleSheet("""
        QWidget {
            background-color: #2a2a2a;
            border-radius: 10px;
        }
    """)
    continue_watching_panel.setMinimumHeight(200)
    
    panel_layout = QVBoxLayout()
    panel_layout.setContentsMargins(20, 15, 20, 15)
    panel_layout.setSpacing(10)
    continue_watching_panel.setLayout(panel_layout)
    
    # Panel header with title and clear all button
    panel_header = QHBoxLayout()
    panel_header.setSpacing(10)
    
    panel_title = QLabel("Continue Watching")
    panel_title.setStyleSheet("""
        color: white;
        font-size: 20px;
        font-weight: bold;
        border: none;
    """)
    
    clear_all_btn = QPushButton("Clear All")
    clear_all_btn.setFixedSize(100, 30)
    clear_all_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(255, 255, 255, 20);
            color: #aaa;
            border: 1px solid #555;
            border-radius: 5px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: rgba(255, 0, 0, 100);
            color: white;
            border: 1px solid #ff0000;
        }
    """)
    clear_all_btn.clicked.connect(clear_all_callback if clear_all_callback else lambda: None)
    clear_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    panel_header.addWidget(panel_title)
    panel_header.addStretch()
    panel_header.addWidget(clear_all_btn)
    
    panel_layout.addLayout(panel_header)
    
    
    # Check if there are continue watching items
    if continue_watching_items and len(continue_watching_items) > 0:
        # Grid layout for tiles - 4 columns
        COLUMNS = 6
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_widget.setLayout(grid_layout)
        
        # Make columns stretch evenly
        for col in range(COLUMNS):
            grid_layout.setColumnStretch(col, 1)
        
        # Add tiles to grid
        for index, item in enumerate(continue_watching_items):
            row = index // COLUMNS
            col = index % COLUMNS
            tile = create_movie_tile(item, continue_click_handler, delete_item_callback)
            grid_layout.addWidget(tile, row, col)
        
        panel_layout.addWidget(grid_widget)
    else:
        # Placeholder text
        panel_placeholder = QLabel("Videos you start watching will appear here")
        panel_placeholder.setStyleSheet("""
            color: #888;
            font-size: 14px;
            border: none;
        """)
        panel_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(panel_placeholder)
        panel_layout.addStretch()
    
    scroll_layout.addWidget(continue_watching_panel)
    scroll_layout.addStretch()

    # =========================
    # ASSEMBLE PAGE
    # =========================
    home_layout.addWidget(menu_bar)
    home_layout.addWidget(scroll)

    return home_page
#---------------------------------------------------------------------------------------------------
def toggle_episode_list(episode_list, button, checked):
    """Toggle episode list visibility"""
    if checked:
        # Show the list
        episode_list.setVisible(True)

        # Calculate height based on all items
        total_height = 0
        for i in range(episode_list.count()):
            total_height += episode_list.sizeHintForRow(i)

        episode_list.setMaximumHeight(total_height)
        episode_list.setMinimumHeight(total_height) # Force exact height)
        button.setText("▲")
    else:
        # Hide the list
        episode_list.setMaximumHeight(0)
        episode_list.setVisible(False)
        button.setText("▼")
#---------------------------------------------------------------------------------------------------
def create_tv_seasons_episodes_page(show_data, click_handler, switch_to_tv_callback=None):
    """ Create browse page for specific tv shows. containing their seasons with a dropdown
    menu with their episodes in order
    
    Args:
    show_data: Dictionary containing show info with 'title' and 'seasons'
    click handler: function to call when an episode is clicked
    switch_to_tv_callback: function to call when button is clicked
    ...
    
    Returns:
        QWidget: the complete browse page"""
    
    show_title = show_data.get("title", "Unknown Show")
    
    # Create main page widget
    browse_page = QWidget()
    browse_layout = QVBoxLayout()
    browse_layout.setContentsMargins(0, 0, 0, 0)
    browse_layout.setSpacing(0)
    browse_page.setLayout(browse_layout)

    # =========================
    # 🏠 MENU BAR (Fixed at top)
    # =========================
    menu_bar = QWidget()
    menu_bar.setFixedHeight(60)
    menu_bar.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            border-bottom: 2px solid #333;
        }
    """)
    
    menu_layout = QHBoxLayout()
    menu_layout.setContentsMargins(20, 10, 20, 10)
    menu_layout.setSpacing(20)
    menu_bar.setLayout(menu_layout)
    
    # Back button (left side)
    back_button = QPushButton("← Back")
    back_button.setStyleSheet("""
                              QPushButton {
                              background-color: transparent;
                              color: #0099ff;
                              border: none;
                              font-size: 16px;
                              font-weight: bold;
                              padding: 5px 15px;
                              }
                              QPushButton:hover {
                              color: #00bbff;
                              }
                              """)
    
    if switch_to_tv_callback:
        back_button.clicked.connect(switch_to_tv_callback)

    # Menu title (center)
    logo_label = QLabel(show_title)
    logo_label.setStyleSheet("""
        color: white;
        font-size: 24px;
        font-weight: bold;
        border: none;
    """)
    logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # Spacers for centering title
    left_spacer = QWidget()
    left_spacer.setFixedWidth(back_button.sizeHint().width())

    right_spacer = QWidget()
    right_spacer.setFixedWidth(back_button.sizeHint().width())

    # Assemble menu bar
    menu_layout.addWidget(back_button)
    menu_layout.addStretch()
    menu_layout.addWidget(logo_label)
    menu_layout.addStretch()
    menu_layout.addWidget(right_spacer)

    # =========================
    # 📜 SCROLLABLE CONTENT AREA
    # =========================
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: #222222;
        }
    """)

    scroll_container = QWidget()
    scroll_container.setStyleSheet("background-color: #222222;")
    scroll_layout = QVBoxLayout()
    scroll_layout.setSpacing(15)
    scroll_layout.setContentsMargins(50, 30, 50, 30)
    scroll_container.setLayout(scroll_layout)

    scroll.setWidget(scroll_container)

    # =========================
    # Season Dropdown
    # =========================
    seasons = show_data.get("seasons", {})

    if not seasons:
        # No seasons found
        no_seasons_label = QLabel("No seasons found")
        no_seasons_label.setStyleSheet("""
                                       color: #aaa;
                                       font-size: 18px;
                                       padding: 20px;
                                       """)
        no_seasons_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(no_seasons_label)
    else:
        # Sort seasons naturally (season 1, 2, 3,...)
        import re
        def sort_key(season_name):
            numbers = re.findall(r'\d+', season_name)
            return int(numbers[0]) if numbers else 0
        
        sorted_seasons = sorted(seasons.keys(), key=sort_key)

        for season_name in sorted_seasons:
            episodes = seasons[season_name]

            # Season container
            season_widget = QWidget()
            season_widget.setStyleSheet("""
                                        QWidget {
                                        background-color: #2a2a2a;
                                        border-radius: 8px;
                                        }
                                        """)
            season_layout = QVBoxLayout()
            season_layout.setContentsMargins(20, 15, 20, 15)
            season_layout.setSpacing(10)
            season_widget.setLayout(season_layout)

            # Season header with dropdown button
            header_layout = QHBoxLayout()

            season_label = QLabel(season_name)
            season_label.setStyleSheet("""
                                       color: white;
                                       font-size: 20px;
                                       font-weight: bold;
                                       background-color: transparent;
                                       border: none;
                                       """)
            
            episode_count_label = QLabel(f"({len(episodes)} episodes)")
            episode_count_label.setStyleSheet("""
                                              color: #aaa;
                                              font-size: 14px;
                                              background-color: transparent;
                                              border: none;
                                              """)
            
            dropdown_btn = QPushButton("▼")
            dropdown_btn.setFixedSize(40, 40)
            dropdown_btn.setCheckable(True)
            dropdown_btn.setStyleSheet("""
                                       QPushButton {
                                       background-color: #333;
                                       color: white;
                                       border: none;
                                       border-radius: 5px;
                                       font-size: 18px;
                                       }
                                       QPushButton:hover{
                                       background-color: #444;
                                       }
                                       QPushButton:checked{
                                       background-color: #555;
                                       }
                                       """)
            
            header_layout.addWidget(season_label)
            header_layout.addWidget(episode_count_label)
            header_layout.addStretch()
            header_layout.addWidget(dropdown_btn)

            season_layout.addLayout(header_layout)

            # Episode List (hidden by default)
            episode_list = QListWidget()
            episode_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Disables scroll bar for dropdown menu
            episode_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            episode_list.setStyleSheet("""
                                       QListWidget {
                                       background-color: #333;
                                       border: none;
                                       border-radius: 5px;
                                       padding: 5px;
                                       }
                                       QListWidget::item{
                                       color: white;
                                       padding: 10px;
                                       border-bottom: 1px solid #444;
                                       font-size: 14px;
                                       }
                                       QListWidget::item:hover{
                                       background-color: #444;
                                       border-radius: 3px;
                                       }
                                       QListWidget::item:selected{
                                       background-color: #0099ff;
                                       border-radius: 3px;
                                       }
                                       """)
            episode_list.setMaximumHeight(0) # start collapsed
            episode_list.setVisible(False)

            # Add sorted episodes
            sorted_episodes = sorted(episodes, key=lambda x: x["title"])
            for episode in sorted_episodes:
                item = QListWidgetItem(episode["title"])
                item.setData(Qt.ItemDataRole.UserRole, episode) #Store full episode data
                episode_list.addItem(item)

            season_layout.addWidget(episode_list)

            # Connect dropdown button
            dropdown_btn.clicked.connect(
                lambda checked, ep_list=episode_list, btn=dropdown_btn: toggle_episode_list(ep_list, btn, checked)
            )
            
            # Connect episode click
            episode_list.itemClicked.connect(
                lambda item, handler=click_handler: handler(item.data(Qt.ItemDataRole.UserRole))
            )
            
            scroll_layout.addWidget(season_widget)
    
    # Add stretch to push content to top
    scroll_layout.addStretch()

    # =========================
    # ASSEMBLE PAGE
    # =========================
    browse_layout.addWidget(menu_bar)  # Menu bar first = at top
    browse_layout.addWidget(scroll)     # Scroll area second = below menu bar

    return browse_page
#---------------------------------------------------------------------------------------------------
def toggle_episode_list_simple(episode_list):
    """Toggle episode list visibility (no button)"""
    is_visible = episode_list.isVisible()

    if not is_visible:
        episode_list.setVisible(True)
        total_height = 0
        for i in range(episode_list.count()):
            total_height += episode_list.sizeHintForRow(i)
        total_height += episode_list.count() * 2 + 10
        episode_list.setMaximumHeight(total_height)
        episode_list.setMinimumHeight(total_height)
    else:
        episode_list.setMaximumHeight(0)
        episode_list.setMinimumHeight(0)
        episode_list.setVisible(False)
#---------------------------------------------------------------------------------------------------
def run_vlc_cache_gen():
    """Run VLC cache generator to speed up initial VLC loading"""
    try:
        # Common VLC installation paths
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC",
            r"C:\Program Files (x86)\VideoLAN\VLC",
            r"D:\VLC",
        ]

        for path in vlc_paths:
            cache_gen = os.path.join(path, "vlc-cache-gen.exe")
            if os.path.exists(cache_gen):
                plugins_dir = os.path.join(path, "plugins")
                # Run silently in background
                subprocess.run(
                    [cache_gen, plugins_dir],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                print("VLC plugin cache generated")
                return
    except Exception as e:
        print(f"Could not run vlc-cache-gen: {e}")
#---------------------------------------------------------------------------------------------------
def create_search_bar(search_callback, close_callback):
    """
    Create a search bar widget.
    
    Args:
        search_callback: Function to call when text changes (receives search text)
        close_callback: Function to call when search is closed
    
    Returns:
        QWidget: The search bar widget
    """
    from PyQt6.QtWidgets import QLineEdit
    
    search_widget = QWidget()
    search_widget.setFixedHeight(50)
    search_widget.setStyleSheet("""
        QWidget {
            background-color: #1a1a1a;
            border-bottom: 2px solid #333;
        }
    """)
    
    search_layout = QHBoxLayout()
    search_layout.setContentsMargins(20, 5, 20, 5)
    search_layout.setSpacing(10)
    search_widget.setLayout(search_layout)
    
    # Search icon
    search_icon = QLabel("🔍")
    search_icon.setStyleSheet("color: white; font-size: 18px; border: none;")
    
    # Search input
    search_input = QLineEdit()
    search_input.setPlaceholderText("Search...")
    search_input.setStyleSheet("""
        QLineEdit {
            background-color: #333;
            color: white;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 8px 15px;
            font-size: 16px;
        }
        QLineEdit:focus {
            border: 1px solid #0099ff;
        }
    """)
    search_input.textChanged.connect(search_callback)
    
    # Close button
    close_btn = QPushButton("✕")
    close_btn.setFixedSize(35, 35)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #aaa;
            border: none;
            font-size: 18px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 10);
            color: white;
        }
    """)
    close_btn.clicked.connect(close_callback)
    
    search_layout.addWidget(search_icon)
    search_layout.addWidget(search_input, 1)
    search_layout.addWidget(close_btn)
    
    # Store reference to input for clearing
    search_widget.search_input = search_input
    
    return search_widget
#---------------------------------------------------------------------------------------------------
class WatchTracker:
    def __init__(self, db_path="watch_progress.db"):
        """Initialize the watch tracker with a SQLite database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the database and tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watch_progress (
                path TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                poster TEXT,
                completed INTEGER DEFAULT 0,
                last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_progress(self, path, title, video_type, progress, duration, poster=None):
        """Save or update watch progress for a video."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if video is completed (within 30 seconds of the end)
        completed = 0
        if duration > 0 and (duration - progress) < 30000:
            completed = 1
        
        cursor.execute('''
            INSERT OR REPLACE INTO watch_progress 
            (path, title, type, progress, duration, poster, completed, last_watched)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (path, title, video_type, progress, duration, poster, completed))
        
        conn.commit()
        conn.close()
    
    def delete_progress(self, path):
        """Delete watch progress for a specific video"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM watch_progress WHERE path = ?', (path,))
        conn.commit()
        conn.close()

    def get_progress(self, path):
        """Get watch progress for a specific video."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM watch_progress WHERE path = ?', (path,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'path': result[0],
                'title': result[1],
                'type': result[2],
                'progress': result[3],
                'duration': result[4],
                'poster': result[5],
                'completed': bool(result[6]),
                'last_watched': result[7]
            }
        return None
    
    def get_continue_watching(self, limit=10):
        """Get videos that have been started but not completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM watch_progress 
            WHERE completed = 0 AND progress > 0
            ORDER BY last_watched DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        videos = []
        for row in results:
            videos.append({
                'path': row[0],
                'title': row[1],
                'type': row[2],
                'progress': row[3],
                'duration': row[4],
                'poster': row[5],
                'completed': bool(row[6]),
                'last_watched': row[7]
            })
        
        return videos
    
    def get_progress_percentage(self, path):
        """Get watch progress as a percentage (0-100)."""
        progress_data = self.get_progress(path)
        if progress_data and progress_data['duration'] > 0:
            return (progress_data['progress'] / progress_data['duration']) * 100
        return 0

    def clear_all(self):
        """Clear all watch progress data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM watch_progress')
        conn.commit()
        conn.close()
#---------------------------------------------------------------------------------------------------
class VideoPlayer(QWidget):
    def __init__(self, video_path, back_callback, watch_tracker=None, video_type=None, show_title=None, season=None, next_episode_callback=None, episode_list_callback=None):
        super().__init__()
        
        # Store the callback as an instance variable
        self.back_callback = back_callback
        self.video_type = video_type
        self.next_episode_callback = next_episode_callback
        self.episode_list_callback = episode_list_callback
        self.is_fullscreen = False
        self.is_playing = True
        self.current_media_path = video_path

        # =========================
        # 🎥 MAIN LAYOUT
        # =========================
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # Video frame (will hold VLC output)
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.video_frame)

        # =========================
        # 🎛 OVERLAY - Separate Window
        # =========================
        self.overlay = None  # Will be created after parent is set
        self.overlay_created = False
        
        # Don't create the overlay until the widget is properly parented
        QTimer.singleShot(0, self.create_overlay)

        # =========================
        # ⏱ TIMERS
        # =========================
        self.hide_timer = QTimer()
        self.hide_timer.setInterval(2000)
        self.hide_timer.timeout.connect(self.hide_overlay)
        
        # Mouse check timer
        self.mouse_check_timer = QTimer()
        self.mouse_check_timer.setInterval(100)
        self.mouse_check_timer.timeout.connect(self.check_mouse_position)
        self.last_mouse_pos = None
        
        # Seek bar update timer
        self.update_timer = QTimer()
        self.update_timer.setInterval(250)  # Update every 250ms
        self.update_timer.timeout.connect(self.update_seek_bar)

        # =========================
        # 🎬 VLC SETUP
        # =========================
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        # Disable VLC mouse and key input
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)

        media = self.instance.media_new(video_path)
        self.player.set_media(media)

        # Attach VLC to Qt widget
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform == "win32":
            self.player.set_hwnd(int(self.video_frame.winId()))

        # Enable mouse tracking
        self.setMouseTracking(True)
        self.video_frame.setMouseTracking(True)
        self.video_frame.installEventFilter(self)

        # Delay play and start timers
        QTimer.singleShot(100, self.start_playback)
        
        # Auto save timer (every 10s)
        self.save_timer = QTimer()
        self.save_timer.setInterval(10000)
        self.save_timer.timeout.connect(self.auto_save_progress)

    def start_playback(self):
        """Start playback and timers"""
        self.player.play()
        self.update_timer.start()
        self.mouse_check_timer.start()
        self.save_timer.start()
        self.setFocus() # Ensures the widget has keyboard access
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    def auto_save_progress(self):
        """save progress periodically while watching"""
        if self.player.get_length() > 0:
            current_time = self.player.get_time()
            if current_time > 0:
                watch_tracker.save_progress(
                    path=self.current_media_path,
                    title=os.path.basename(self.current_media_path),
                    video_type=self.video_type or 'movie',
                    progress=current_time,
                    duration=self.player.get_length()
                ) 
    def eventFilter(self, obj, event):
        """Filter events to catch mouse movement on video frame"""
        if obj == self.video_frame:
            if event.type() in [event.Type.MouseMove, event.Type.Enter]:
                self.show_overlay()
                self.hide_timer.start()
        # Close episode popup on focus loss
        elif hasattr(self, 'episode_popup') and obj == self.episode_popup:
            if event.type() == event.Type.WindowDeactivate:
                self.episode_popup.close()
                self.episode_popup = None
        return super().eventFilter(obj, event)
    def check_mouse_position(self):
        """Periodically check if mouse has moved"""
        if not self.isVisible():
            return
        
        # Close episode popup if clicking outside it
        if hasattr(self, 'episode_popup') and self.episode_popup and self.episode_popup.isVisible():
            if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
                current_pos = QCursor.pos()
                popup_geo = self.episode_popup.geometry()
                if not popup_geo.contains(current_pos):
                    self.episode_popup.close()
                    self.episode_popup = None
                    return
            
        current_pos = QCursor.pos()
        
        frame_rect = self.video_frame.rect()
        frame_top_left_global = self.video_frame.mapToGlobal(frame_rect.topLeft())
        frame_bottom_right_global = self.video_frame.mapToGlobal(frame_rect.bottomRight())
        frame_global_rect = QRect(frame_top_left_global, frame_bottom_right_global)

        if frame_global_rect.contains(current_pos):
            if self.last_mouse_pos is None:
                self.last_mouse_pos = current_pos
            elif current_pos != self.last_mouse_pos:
                self.last_mouse_pos = current_pos
                self.show_overlay()
                self.hide_timer.start()
        
        # Keep overlay in sync with window
        if self.overlay and self.overlay.isVisible():
            self.update_overlay_position()
    def create_overlay(self):
        """Create the overlay window with full HUD"""
        if self.overlay_created:
            return
            
        top_window = self.window()
        if not top_window:
            QTimer.singleShot(100, self.create_overlay)
            return
            
        # Create overlay
        self.overlay = QWidget(None)
        self.overlay.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.overlay.setMouseTracking(True)
        
        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(10, 10, 10, 10) # reduced from 10, recheck to see
        overlay_layout.setSpacing(0)
        self.overlay.setLayout(overlay_layout)

        # =========================
        # 🎛 TOP BAR (Title & Back)
        # =========================
        top_bar = QWidget()
        top_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 150); 
                border-radius: 8px;
            }
        """)
        top_bar.setFixedHeight(45)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(10, 0, 10, 0)
        top_bar.setLayout(top_bar_layout)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedSize(80, 35)
        self.back_btn.setStyleSheet(self.get_button_style())
        self.back_btn.clicked.connect(self.back_callback)
        self.back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.title_label = QLabel(os.path.basename(self.current_media_path))
        self.title_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_bar_layout.addWidget(self.back_btn)
        top_bar_layout.addWidget(self.title_label)
        top_bar_layout.addStretch()

        overlay_layout.addWidget(top_bar)
        overlay_layout.addStretch()

        # =========================
        # 🎛 BOTTOM BAR (Controls)
        # =========================
        self.bottom_bar = QWidget()
        self.bottom_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 150);
                border-radius: 8px;
            }
        """)
        self.bottom_bar.setFixedHeight(100)
        self.bottom_bar.setMouseTracking(True)
        
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(10, 5, 10, 5)
        bottom_layout.setSpacing(5)
        self.bottom_bar.setLayout(bottom_layout)

        # Seek bar
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setStyleSheet(self.get_slider_style())
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self.seek_position)
        self.seek_slider.sliderPressed.connect(self.seek_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.seek_slider_released)
        self.seek_slider.mousePressEvent = self.seek_bar_clicked
        
        # Time labels
        time_layout = QHBoxLayout()
        time_layout.setSpacing(0)
        
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: white; font-size: 12px; background: transparent;")
        
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: white; font-size: 12px; background: transparent;")
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)

        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(5) 
        controls_layout.setContentsMargins(0, 5, 0, 0) #adds a small top margin
        
        # Skip Backwards button
        self.skip_back_btn = QPushButton("↺")
        self.skip_back_btn.setFixedSize(35, 35)
        self.skip_back_btn.setStyleSheet(self.get_control_button_style())
        self.skip_back_btn.setToolTip("Skip Back 10s (←)")
        self.skip_back_btn.clicked.connect(self.skip_backward)
        self.skip_back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Play/Pause button
        self.play_pause_btn = QPushButton("⏸\uFE0E")  # Pause symbol
        self.play_pause_btn.setFixedSize(35, 35) # Adjust size here
        self.play_pause_btn.setStyleSheet(self.get_control_button_style())
        self.play_pause_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Skip Forwards Button
        self.skip_fwd_btn = QPushButton("↻")
        self.skip_fwd_btn.setFixedSize(35, 35)
        self.skip_fwd_btn.setStyleSheet(self.get_control_button_style())
        self.skip_fwd_btn.setToolTip("Skip Forward 10s (→)")
        self.skip_fwd_btn.clicked.connect(self.skip_forward)
        self.skip_fwd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Volume button
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setFixedSize(35, 35) # Adjust size here
        self.volume_btn.setStyleSheet(self.get_control_button_style())
        self.volume_btn.clicked.connect(self.toggle_mute)
        self.volume_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setStyleSheet(self.get_slider_style())
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80) # Adjust here
        self.volume_slider.valueChanged.connect(self.change_volume)
        
        # Left Side HUD placement
        controls_layout.addWidget(self.skip_back_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.skip_fwd_btn)
        controls_layout.addWidget(self.volume_btn)
        controls_layout.addWidget(self.volume_slider)

        # Spacer pushes remaining controls to the right
        controls_layout.addStretch()
        
        # Episode List Button
        self.episode_list_btn = QPushButton("☰")
        self.episode_list_btn.setFixedSize(35, 35)
        self.episode_list_btn.setToolTip("Episode List")
        self.episode_list_btn.clicked.connect(self.show_episode_list)
        self.episode_list_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Grey out if movie is playing
        if self.video_type == 'movie':
            self.episode_list_btn.hide()
        else:
            self.episode_list_btn.setStyleSheet(self.get_control_button_style())

        # Next episode Button
        self.next_episode_btn = QPushButton("⏭\uFE0E")
        self.next_episode_btn.setFixedSize(35, 35)
        self.next_episode_btn.setToolTip("Next Episode")
        self.next_episode_btn.clicked.connect(self.play_next_episode)
        self.play_pause_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_episode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Grey out if movie is playing
        if self.video_type == 'movie' or not self.next_episode_callback:
            self.next_episode_btn.hide()
        else:
            self.next_episode_btn.setStyleSheet(self.get_control_button_style())
            self.next_episode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Audio Track Button
        self.audio_btn = QPushButton("♪")
        self.audio_btn.setFixedSize(35,35)
        self.audio_btn.setStyleSheet(self.get_control_button_style())
        self.audio_btn.setToolTip("Audio Track")
        self.audio_btn.clicked.connect(self.toggle_audio_tracks)
        self.audio_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Subtitle button
        self.subtitle_btn = QPushButton("CC")
        self.subtitle_btn.setFixedSize(35, 35) # Adjust here
        self.subtitle_btn.setStyleSheet(self.get_control_button_style())
        self.subtitle_btn.clicked.connect(self.toggle_subtitles)
        self.subtitle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Fullscreen button
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(35, 35) # Adjust here
        self.fullscreen_btn.setStyleSheet(self.get_control_button_style())
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Right side HUD Placement
        controls_layout.addWidget(self.episode_list_btn)
        controls_layout.addWidget(self.next_episode_btn)
        controls_layout.addWidget(self.audio_btn)
        controls_layout.addWidget(self.subtitle_btn)
        controls_layout.addWidget(self.fullscreen_btn)

        bottom_layout.addLayout(time_layout)
        bottom_layout.addWidget(self.seek_slider)
        bottom_layout.addLayout(controls_layout)

        overlay_layout.addWidget(self.bottom_bar)
        
        self.overlay_created = True
        QTimer.singleShot(500, self.show_overlay_initial)
    def get_button_style(self):
        """Style for navigation buttons"""
        return """
            QPushButton {
                background-color: rgba(80, 80, 80, 200);
                color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 50);
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 200);
            }
        """
    def get_control_button_style(self):
        """Style for control buttons"""
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
                border-radius: 5px;
                outline: none;
                font-family: "Segoe UI Symbol", "Arial", sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QPushButton:focus {
                border: none;
                outline: none;
            }
        """
    def get_slider_style(self):
        """Style for sliders"""
        return """
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 30);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #0099ff;
            }
            QSlider::sub-page:horizontal {
                background: #0099ff;
                border-radius: 2px;
            }
        """
    # =========================
    # 🎮 PLAYBACK CONTROLS
    # =========================
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.player.pause()
            self.play_pause_btn.setText("▶")
            self.is_playing = False
        else:
            self.player.play()
            self.play_pause_btn.setText("⏸")
            self.is_playing = True
    def seek_slider_pressed(self):
        """Called when user starts dragging seek slider"""
        self.update_timer.stop()
    def seek_slider_released(self):
        """Called when user releases seek slider"""
        self.update_timer.start()
    def seek_position(self, position):
        """Seek to position (0-1000)"""
        if self.player.get_length() > 0:
            seek_time = int(position * self.player.get_length() / 1000)
            self.player.set_time(seek_time)
    def update_seek_bar(self):
        """Update seek bar and time labels"""
        if self.player.get_length() > 0:
            current_time = self.player.get_time()
            total_time = self.player.get_length()
            
            # Update slider
            if not self.seek_slider.isSliderDown():
                slider_pos = int(current_time * 1000 / total_time)
                self.seek_slider.setValue(slider_pos)
            
            # Update time labels
            self.current_time_label.setText(self.format_time(current_time))
            self.total_time_label.setText(self.format_time(total_time))
    def format_time(self, milliseconds):
        """Format milliseconds to MM:SS or HH:MM:SS"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}"
        else:
            return f"{minutes:02d}:{seconds % 60:02d}"
    def toggle_mute(self):
        """Toggle mute"""
        if self.player.audio_get_volume() > 0:
            self.player.audio_set_volume(0)
            self.volume_btn.setText("🔇")
            self.volume_slider.setValue(0)
        else:
            self.player.audio_set_volume(100)
            self.volume_btn.setText("🔊")
            self.volume_slider.setValue(100)
    def change_volume(self, volume):
        """Change volume"""
        self.player.audio_set_volume(volume)
        if volume == 0:
            self.volume_btn.setText("🔇")
        elif volume < 50:
            self.volume_btn.setText("🔉")
        else:
            self.volume_btn.setText("🔊")
    def toggle_subtitles(self):
        """Toggle subtitles using VLC's native menu"""
        # Get available subtitle tracks
        spu_count = self.player.video_get_spu_count()

        if spu_count <= 0:
            print("No subtitle tracks available")
            return

        # Get track descriptions
        track_descriptions = self.player.video_get_spu_description()
        
        if not track_descriptions:
            print("No subtitle tracks found")
            return
        
        # Create popup menu
        cc_menu = QMenu(self)
        cc_menu.setStyleSheet("""
                              QMenu{
                              background-color: #2a2a2a;
                              color: white;
                              border: 1px solid #555;
                              border-radius: 5px;
                              padding: 5px;
                              }
                              QMenu::item{
                              padding: 8px 30px 8px 20px;
                              border-radius: 3px;
                              }
                              QMenu::item:selected{
                              background-color: #0099ff;
                              }
                              QMenu::separator{
                              height: 1px;
                              background: #444;
                              margin: 5px 10px;
                              }
                              """)
        
        # Add disable subtitle option
        disable_action = cc_menu.addAction("Disable Subtitles")
        current_spu = self.player.video_get_spu()

        if current_spu == -1:
            font = disable_action.font()
            font.setBold(True)
            disable_action.setFont(font)
        
        cc_menu.addSeparator()
        
        # Process subtitle tracks - format is (track_id, track_name)
        for track_id, track_name in track_descriptions:
            # Skip the "Disable" track (ID -1)
            if track_id == -1:
                continue
            
            # Decode name if it's bytes
            if isinstance(track_name, bytes):
                display_name = track_name.decode('utf-8', errors='replace')
            else:
                display_name = str(track_name)
            
            # Clean up the name - remove the bracketed language tag if desired
            # display_name = display_name.split(' - [')[0]  # Uncomment to show just "English" instead of "English - [English]"
            
            # Convert track_id to int if needed
            if isinstance(track_id, bytes):
                try:
                    track_id = int(track_id.decode())
                except (ValueError, AttributeError):
                    continue
            elif isinstance(track_id, str):
                try:
                    track_id = int(track_id)
                except ValueError:
                    continue
            
            action = cc_menu.addAction(display_name)
            action.setData(track_id)
            
            # Bold the currently active track
            if track_id == current_spu:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
        
        # Show menu above the bottom UI
        bottom_bar_pos = self.bottom_bar.mapToGlobal(self.bottom_bar.rect().topLeft())
        button_pos = self.subtitle_btn.mapToGlobal(self.subtitle_btn.rect().topRight())

        # Position menu above the bottom bar
        button_pos.setY(bottom_bar_pos.y() - cc_menu.sizeHint().height() - 10) # 10px gap

        selected_action = cc_menu.exec(button_pos)

        if selected_action:
            if selected_action == disable_action:
                # Disable subtitles
                self.player.video_set_spu(-1)
                self.subtitle_btn.setStyleSheet(self.get_control_button_style())
            else:
                # Enable selected track
                track_id = selected_action.data()
                if isinstance(track_id, int):
                    self.player.video_set_spu(track_id)
                    self.subtitle_btn.setStyleSheet("""
                                                    QPushButton{
                                                    background-color: rgba(0, 153, 255, 100);
                                                    color: white;
                                                    border: none;
                                                    font-size: 16px;
                                                    border-radius: 5px;
                                                    }
                                                    QPushButton:hover{
                                                    background-color: rgba(0, 153, 255, 150);
                                                    }
                                                    """)
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.is_fullscreen:
            # Check if window was maximized before fullscreen
            if hasattr(self, 'was_maximized') and self.was_maximized:
                self.window().showMaximized()
            else:
                self.window().showNormal()
            self.fullscreen_btn.setText("⛶")
            self.is_fullscreen = False
        else:
            # Save whether window is currently maximized
            self.was_maximized = self.window().isMaximized()
            self.window().showFullScreen()
            self.fullscreen_btn.setText("⌗")
            self.is_fullscreen = True
    def toggle_audio_tracks(self):
        """Toggle audio track selection menu"""
        # Get available audio tracks
        audio_count = self.player.audio_get_track_count()

        if audio_count <= 0:
            print("No audio tracks available")
            return

        # Get track descriptions
        track_descriptions = self.player.audio_get_track_description()
        
        if not track_descriptions:
            print("No audio tracks found")
            return
        
        # Create popup menu
        audio_menu = QMenu(self)
        audio_menu.setStyleSheet("""
                              QMenu{
                              background-color: #2a2a2a;
                              color: white;
                              border: 1px solid #555;
                              border-radius: 5px;
                              padding: 5px;
                              }
                              QMenu::item{
                              padding: 8px 30px 8px 20px;
                              border-radius: 3px;
                              }
                              QMenu::item:selected{
                              background-color: #0099ff;
                              }
                              QMenu::separator{
                              height: 1px;
                              background: #444;
                              margin: 5px 10px;
                              }
                              """)
        
        # Get current audio track
        current_audio = self.player.audio_get_track()
        print(f"Current audio track: {current_audio}")
        
        # Process audio tracks - format is (track_id, track_name)
        for track_id, track_name in track_descriptions:
            print(f"Audio track - ID: {track_id}, Name: {track_name}")
            
            # Skip the "Disable" track (ID -1)
            if track_id == -1:
                continue
            
            # Decode name if it's bytes
            if isinstance(track_name, bytes):
                display_name = track_name.decode('utf-8', errors='replace')
            else:
                display_name = str(track_name)
            
            # Convert track_id to int if needed
            if isinstance(track_id, bytes):
                try:
                    track_id = int(track_id.decode())
                except (ValueError, AttributeError):
                    continue
            elif isinstance(track_id, str):
                try:
                    track_id = int(track_id)
                except ValueError:
                    continue
            
            action = audio_menu.addAction(display_name)
            action.setData(track_id)
            
            # Bold the currently active track
            if track_id == current_audio:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
        
        # Show menu above the bottom bar
        bottom_bar_pos = self.bottom_bar.mapToGlobal(self.bottom_bar.rect().topLeft())
        button_pos = self.audio_btn.mapToGlobal(self.audio_btn.rect().topRight())
        
        # Position menu above the bottom bar
        button_pos.setY(bottom_bar_pos.y() - audio_menu.sizeHint().height() - 10)
        
        selected_action = audio_menu.exec(button_pos)

        if selected_action:
            track_id = selected_action.data()
            print(f"Selected audio track ID: {track_id}")
            if isinstance(track_id, int):
                # Use audio_set_track with the correct track ID
                result = self.player.audio_set_track(track_id)
                print(f"audio_set_track result: {result}")
                
                # Verify the change
                new_track = self.player.audio_get_track()
                print(f"New audio track: {new_track}")
                
                # Highlight the audio button
                self.audio_btn.setStyleSheet("""
                                                QPushButton{
                                                background-color: rgba(0, 153, 255, 100);
                                                color: white;
                                                border: none;
                                                font-size: 16px;
                                                border-radius: 5px;
                                                }
                                                QPushButton:hover{
                                                background-color: rgba(0, 153, 255, 150);
                                                }
                                                """)
    def skip_forward(self):
        """Skip forwards 10 seconds"""
        if self.player.get_length() > 0:
            new_time = min(self.player.get_length(), self.player.get_time() + 10000)
            self.player.set_time(new_time)
            # Show overlay briefly so user can see the time change
            self.show_overlay()
            self.hide_timer.start()
    def skip_backward(self):
        """Skip backward 10 seconds"""
        new_time = max(0, self.player.get_time() - 10000)
        self.player.set_time(new_time)
        # Show overlay briefly
        self.show_overlay()
        self.hide_timer.start()
    def play_next_episode(self):
        """Play the next episode"""
        if self.next_episode_callback:
            self.player.stop()
            self.update_timer.stop()
            self.mouse_check_timer.stop()
            self.next_episode_callback()
    def show_episode_list(self):
        """Show episode list popup with collapsible seasons, limited size"""
        # Close existing popup if open
        if hasattr(self, 'episode_popup') and self.episode_popup:
            self.episode_popup.close()
            self.episode_popup = None
            
        if self.episode_list_callback:
            episodes_data = self.episode_list_callback()
            if not episodes_data:
                return
            
            # Create a custom popup widget
            popup = QWidget(None)
            popup.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.Popup  # Closes when clicking outside
            )
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            popup.setStyleSheet("background-color: #2a2a2a; border: 1px solid #555; border-radius: 8px;")
            
            popup_layout = QVBoxLayout()
            popup_layout.setContentsMargins(10, 10, 10, 10)
            popup_layout.setSpacing(5)
            popup.setLayout(popup_layout)

            # Title
            title_label = QLabel("Episodes")
            title_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none; padding: 5px;")
            popup_layout.addWidget(title_label)
            
            # Scroll area with fixed size
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
            """)
            scroll.setFixedHeight(300)  # MAX HEIGHT - scroll if more
            scroll.setFixedWidth(300)   # FIXED WIDTH
            
            scroll_content = QWidget()
            scroll_content.setStyleSheet("background-color: transparent;")
            scroll_layout = QVBoxLayout()
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(5)
            scroll_content.setLayout(scroll_layout)
            
            scroll.setWidget(scroll_content)
            
            # Get current episode path
            current_path = self.current_media_path
            
            import re
            def sort_key(season_name):
                numbers = re.findall(r'\d+', season_name)
                return int(numbers[0]) if numbers else 0
            
            sorted_seasons = sorted(episodes_data.keys(), key=sort_key)
            
            for season_name in sorted_seasons:
                episodes = episodes_data[season_name]
                
                # Season container
                season_widget = QWidget()
                season_widget.setStyleSheet("background-color: transparent; border: none;")
                season_layout = QVBoxLayout()
                season_layout.setContentsMargins(0, 0, 0, 0)
                season_layout.setSpacing(2)
                season_widget.setLayout(season_layout)
                
                # Season header
                season_header = QPushButton(f"📁 {season_name} ({len(episodes)} episodes)")
                season_header.setCheckable(True)
                season_header.setStyleSheet("""
                    QPushButton {
                        background-color: #333;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 8px;
                        text-align: left;
                        font-size: 13px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #444;
                    }
                """)
                season_layout.addWidget(season_header)
                
                # Episode list (hidden by default)
                episode_list = QListWidget()
                episode_list.setStyleSheet("""
                    QListWidget {
                        background-color: #333;
                        border: none;
                        border-radius: 5px;
                        padding: 3px;
                    }
                    QListWidget::item {
                        color: white;
                        padding: 6px;
                        border-bottom: 1px solid #444;
                        font-size: 12px;
                    }
                    QListWidget::item:hover {
                        background-color: #444;
                        border-radius: 3px;
                    }
                    QListWidget::item:selected {
                        background-color: #0099ff;
                        border-radius: 3px;
                    }
                """)
                episode_list.setMaximumHeight(0)
                episode_list.setVisible(False)
                episode_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                episode_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                
                # Add sorted episodes
                sorted_episodes = sorted(episodes, key=lambda x: x["title"])
                for ep in sorted_episodes:
                    display_title = ep["title"]
                    if ep["path"] == current_path:
                        display_title = f"▶ {display_title}"
                    
                    item = QListWidgetItem(display_title)
                    item.setData(Qt.ItemDataRole.UserRole, ep)
                    
                    if ep["path"] == current_path:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    
                    episode_list.addItem(item)
                
                season_layout.addWidget(episode_list)
                
                # Connect expand/collapse
                season_header.clicked.connect(
                    lambda checked, ep_list=episode_list: toggle_episode_list_simple(ep_list)
                )
                
                scroll_layout.addWidget(season_widget)
            
            scroll_layout.addStretch()
            popup_layout.addWidget(scroll)
            
            # Install event filter to close on focus loss
            popup.installEventFilter(self)

            # Show popup
            popup.adjustSize()
            
            # Position above the bottom bar
            bottom_bar_pos = self.bottom_bar.mapToGlobal(self.bottom_bar.rect().topLeft())
            button_pos = self.episode_list_btn.mapToGlobal(self.episode_list_btn.rect().topRight())
            
            popup.move(button_pos.x() - 320, bottom_bar_pos.y() - popup.height() - 10)
            popup.show()
            
            # Store reference for cleanup
            self.episode_popup = popup
            popup.destroyed.connect(lambda: setattr(self, 'episode_popup', None))
            
            # Connect episode clicks
            for i in range(scroll_layout.count()):
                sw = scroll_layout.itemAt(i).widget()
                if sw:
                    ep_list = sw.findChild(QListWidget)
                    if ep_list:
                        ep_list.itemClicked.connect(
                            lambda item, p=popup: self.on_episode_selected(item, p)
                        )
    def on_episode_selected(self, item, popup):
        """Handle episode selection from popup"""
        episode_data = item.data(Qt.ItemDataRole.UserRole)
        if episode_data:
            popup.close()
            self.player.stop()
            self.update_timer.stop()
            self.mouse_check_timer.stop()
            if hasattr(self, 'play_episode_callback'):
                self.play_episode_callback(episode_data)
    def seek_bar_clicked(self, event):
        """Handle mouse click anywhere on the seek bar"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate position based on click location
            slider_width = self.seek_slider.width()
            click_x = event.position().x()

            # Convert click position to slider value (0-1000)
            if slider_width > 0:
                value = int((click_x/slider_width) * 1000)
                value = max(0, min(1000, value)) # Clamp to valid range

                self.seek_slider.setValue(value)
                self.seek_position(value)

                # Show overlay briefly
                self.show_overlay()
                self.hide_timer.start()
        
        # Call the origianl event to keep drag functionality
        QSlider.mousePressEvent(self.seek_slider, event)
    # =========================
    # 🖥 OVERLAY MANAGEMENT
    # =========================
    def hide_overlay(self):
        """Hide the overlay"""
        if self.overlay:
            self.overlay.hide()
        # Close episode popup if open
        if hasattr(self, 'episode_popup') and self.episode_popup:
            self.episode_popup.close()
            self.episode_popup = None
        # Reset Cursor
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    def show_overlay(self):
        """Show the overlay"""
        if not self.overlay or not self.overlay_created:
            return
            
        self.update_overlay_position()
        self.overlay.show()
        self.overlay.raise_()
        
        if sys.platform == "win32":
            import ctypes
            
            overlay_hwnd = int(self.overlay.winId())
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            
            ctypes.windll.user32.SetWindowPos(
                overlay_hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
    def update_overlay_position(self):
        """Position overlay window over the video area"""
        if not self.video_frame or not self.overlay or not self.overlay_created:
            return
            
        pos = self.video_frame.mapToGlobal(self.video_frame.rect().topLeft())
        size = self.video_frame.size()
        self.overlay.setGeometry(pos.x(), pos.y(), size.width(), size.height())
    def show_overlay_initial(self):
        """Show overlay initially"""
        self.show_overlay()
        self.hide_timer.start()
    # =========================
    # 🪟 WINDOW EVENTS
    # =========================
    def showEvent(self, event):
        super().showEvent(event)
        if self.overlay_created:
            QTimer.singleShot(500, self.show_overlay_initial)
    def moveEvent(self, event):
        super().moveEvent(event)
        if self.overlay and self.overlay.isVisible():
            self.update_overlay_position()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay and self.overlay.isVisible():
            self.update_overlay_position()
    def hideEvent(self, event):
        super().hideEvent(event)
        if self.overlay:
            self.overlay.hide()
        self.mouse_check_timer.stop()
        self.update_timer.stop()
        self.save_timer.stop()
    def closeEvent(self, event):
        self.mouse_check_timer.stop()
        self.update_timer.stop()
        self.save_timer.stop()
        self.auto_save_progress()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        if self.overlay:
            self.overlay.close()
        # Close episode popup
        if hasattr(self, 'episode_popup') and self.episdoe_popup:
            self.episode_popup.close()
            self.episode_popup = None
        super().closeEvent(event)
    # =========================
    # 🖱 MOUSE EVENTS
    # =========================
    def mouseMoveEvent(self, event):
        self.show_overlay()
        self.hide_timer.start()
    def enterEvent(self, event):
        self.show_overlay()
        self.hide_timer.start()
    def leaveEvent(self, event):
        self.hide_timer.start()
    def mouseDoubleClickEvent(self, event):
        """Double click to toggle fullscreen"""
        self.toggle_fullscreen()
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
        elif event.key() == Qt.Key.Key_F or event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Left:
            self.player.set_time(max(0, self.player.get_time() - 10000))  # Skip back 10s
        elif event.key() == Qt.Key.Key_Right:
            self.player.set_time(min(self.player.get_length(), self.player.get_time() + 10000))  # Skip forward 10s
        elif event.key() == Qt.Key.Key_Up:
            self.change_volume(min(100, self.player.audio_get_volume() + 5))
            self.volume_slider.setValue(self.player.audio_get_volume())
        elif event.key() == Qt.Key.Key_Down:
            self.change_volume(max(0, self.player.audio_get_volume() - 5))
            self.volume_slider.setValue(self.player.audio_get_volume())
        else:
            super().keyPressEvent(event)
#---------------------------------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.ico"))

        # Paths (temporary)
        self.movies_path = r"F:\Downloads\Movies"
        self.tv_path = r"F:\Downloads\TV Shows"

        # Try to load saved paths
        self.load_paths()

        self.movies = scan_movies(self.movies_path)
        self.tv_shows = scan_tv(self.tv_path)

        print(f"Total Movies: {len(self.movies)}")
        print(f"Total TV Shows: {len(self.tv_shows)}")

        # Window
        self.setWindowTitle("LMWT")
        self.setGeometry(100, 100, 1000, 700)

        # =========================
        # STACK (PAGE SYSTEM)
        # =========================
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # =========================
        # Page 0 - Home
        # =========================
        self.create_home_page()
        self.home_page = create_home_page(
            switch_to_movies_callback=self.switch_to_movies,
            switch_to_tv_callback=self.switch_to_tv
        )

        # =========================
        # 🎬 PAGE 1 — BROWSE - Movies
        # =========================
        self.browse_page = create_movies_browse_page(
            self.movies, 
            self.on_item_clicked, 
            "🎬",
            switch_to_tv_callback=self.switch_to_tv,
            switch_to_home_callback=self.switch_to_home,
            movies_folder_callback=self.select_movies_folder #Movies only
            )

        # =========================
        # 🎥 PAGE 2 — BROWSE - TV Shows
        # =========================
        self.tv_browse_page = create_tv_browse_page(
            self.tv_shows,
            self.on_show_clicked,
            "📺",
            switch_to_movies_callback=self.switch_to_movies,
            switch_to_home_callback=self.switch_to_home,
            tv_folder_callback=self.select_tv_folder #TV only
        )

        # =========================
        # 🎥 PAGE 3 — TV Shows Seasons / Episodes
        # =========================
        # Created dynamically when a show is clicked

        # =========================
        # 🎥 PAGE 4 — PLAYER
        # =========================
        self.player_page = QWidget()
        self.player_layout = QVBoxLayout()
        self.player_layout.setContentsMargins(0, 0, 0, 0)
        self.player_layout.setSpacing(0)
        self.player_page.setLayout(self.player_layout)
        self.player_page.setStyleSheet("background-color: black;")

        # =========================
        # ADD PAGES
        # =========================
        self.stack.addWidget(self.home_page) # Index 0
        self.stack.addWidget(self.browse_page) # Index 1
        self.stack.addWidget(self.tv_browse_page) # Index 2
        self.stack.addWidget(self.player_page) # Index 3  
    # =========================
    # Switch to Home
    # =========================
    def create_home_page(self):
        """Create or refresh the home page with continue watching data"""
        # Get continue watching items from database
        continue_items = watch_tracker.get_continue_watching()
        
        # Group episodes by show and keep only the latest one per show
        enhanced_items = []
        show_episodes = {}  # {show_path: latest_episode}
        
        for item in continue_items:
            if item['type'] == 'episode':
                # Find which show this episode belongs to
                show_path = None
                show_title = None
                show_poster = None
                
                for show in self.tv_shows:
                    if item['path'].startswith(show['path']):
                        show_path = show['path']
                        show_title = show['title']
                        show_poster = show.get('poster')
                        break
                
                if show_path:
                    # Only keep the latest episode per show
                    if show_path not in show_episodes:
                        show_episodes[show_path] = {
                            'path': item['path'],
                            'title': f"{show_title}: {item['title']}",
                            'type': 'episode',
                            'poster': show_poster,
                            'progress': item['progress'],
                            'duration': item['duration'],
                            'last_watched': item['last_watched'],
                            'episode_title': item['title'],
                            'show_path': show_path
                        }
                    else:
                        # Compare last_watched timestamps
                        if item['last_watched'] > show_episodes[show_path]['last_watched']:
                            show_episodes[show_path] = {
                                'path': item['path'],
                                'title': f"{show_title}: {item['title']}",
                                'type': 'episode',
                                'poster': show_poster,
                                'progress': item['progress'],
                                'duration': item['duration'],
                                'last_watched': item['last_watched'],
                                'episode_title': item['title'],
                                'show_path': show_path
                            }
            else:
                # Movies - just add directly
                enhanced = item.copy()
                for movie in self.movies:
                    if movie['path'] == item['path']:
                        enhanced['title'] = movie['title']
                        enhanced['poster'] = movie.get('poster')
                        break
                enhanced_items.append(enhanced)
        
        # Add grouped episodes
        for show_path, ep_data in show_episodes.items():
            enhanced_items.append(ep_data)
        
        # Sort by last watched (most recent first)
        enhanced_items.sort(key=lambda x: x.get('last_watched', ''), reverse=True)
        
        self.home_page = create_home_page(
            switch_to_movies_callback=self.switch_to_movies,
            switch_to_tv_callback=self.switch_to_tv,
            continue_watching_items=enhanced_items,
            continue_click_handler=self.on_continue_watching_click,
            clear_all_callback=self.clear_all_progress,
            delete_item_callback=self.delete_progress_item
        )

        # Add to stack (index 0)
        if self.stack.count() > 0:
            old_widget = self.stack.widget(0)
            if old_widget:
                self.stack.removeWidget(old_widget)
        self.stack.insertWidget(0, self.home_page)
    def on_continue_watching_click(self, item_list):
        """Handle click on a continue watching tile"""
        if isinstance(item_list, list):
            item = item_list[0]
        else:
            item = item_list
        
        print(f"Continue watching: {item['title']} (type: {item['type']})")
        
        # Remove old player
        if hasattr(self, "player"):
            self.save_current_progress()
            self.player.player.stop()
            self.player.setParent(None)
        
        if item['type'] == 'movie':
            # Play as movie - go back to home
            self.player = VideoPlayer(item["path"], self.go_back_to_home, video_type='movie')
            self.player_layout.addWidget(self.player)
            self.stack.setCurrentWidget(self.player_page)
        else:
            # For TV episodes, restore the show context
            show_path = item.get('show_path')
            
            if show_path:
                # Scan seasons to restore episode list and next episode functionality
                seasons = scan_tv_seasons(show_path)
                
                show_data = {
                    "title": item.get('title', '').split(':')[0].strip(),
                    "path": show_path,
                    "seasons": seasons
                }
                self.current_seasons_data = show_data
                self.current_episode = {
                    "path": item["path"],
                    "title": item.get("episode_title", item["title"])
                }
                
                # Go back to home page
                self.player = VideoPlayer(
                    item["path"], 
                    self.go_back,  # Always go back to home
                    video_type='episode',
                    next_episode_callback=self.play_next_episode,
                    episode_list_callback=self.get_episodes_data
                )
                self.player.play_episode_callback = self.on_episode_clicked
            else:
                self.player = VideoPlayer(item["path"], self.go_back_to_home, video_type='episode')
            
            self.player_layout.addWidget(self.player)
            self.stack.setCurrentWidget(self.player_page)
        
        # Resume from saved position
        progress_data = watch_tracker.get_progress(item["path"])
        if progress_data and progress_data['progress'] > 0:
            QTimer.singleShot(500, lambda: self.player.player.set_time(progress_data['progress']))
    def save_current_progress(self):
        """Save current playback progress to database"""
        if hasattr(self, "player") and self.player.player.get_length() > 0:
            current_time = self.player.player.get_time()
            total_time = self.player.player.get_length()
            
            if current_time > 0:
                path = self.player.current_media_path
                title = os.path.basename(path)
                video_type = self.player.video_type or 'movie'
                
                # For episodes, find and store the show path
                if video_type == 'episode' and hasattr(self, 'current_seasons_data'):
                    # Store with show title prefix for better display
                    show_title = self.current_seasons_data.get('title', '')
                    title = f"{show_title}: {title}" if show_title else title
                
                watch_tracker.save_progress(
                    path=path,
                    title=title,
                    video_type=video_type,
                    progress=current_time,
                    duration=total_time
                )
    def switch_to_home(self):
        """Switch to home page"""
        self.create_home_page()
        self.stack.setCurrentWidget(self.home_page)
    def clear_all_progress(self):
        """Clear all watch progress"""
        watch_tracker.clear_all()
        self.create_home_page()
        self.stack.setCurrentWidget(self.home_page)
    def delete_progress_item(self, item):
        """Delete all watch progress entries for a show/movie"""
        if isinstance(item, list):
            item = item[0]
        
        if item['type'] == 'movie':
            # Delete just this movie
            watch_tracker.delete_progress(item['path'])
        else:
            # For TV shows, delete ALL episodes from this show
            show_path = item.get('show_path')
            if show_path:
                # Get all entries and delete those matching this show path
                all_entries = watch_tracker.get_continue_watching(limit=1000)
                for entry in all_entries:
                    if entry['path'].startswith(show_path):
                        watch_tracker.delete_progress(entry['path'])
            else:
                # Fallback: delete just this episode
                watch_tracker.delete_progress(item['path'])
        
        self.create_home_page()
        self.stack.setCurrentWidget(self.home_page)
    # =========================
    # Switch to TV
    # =========================
    def switch_to_tv(self):
        """Switch from movies browse to tv browse"""
        self.stack.setCurrentWidget(self.tv_browse_page)
    # =========================
    # Switch to Movies
    # =========================
    def switch_to_movies(self):
        """Switch from TV browse to Movies browse"""
        self.stack.setCurrentWidget(self.browse_page)
    # =========================
    # Movie/TV Folder Setup
    # =========================
    def select_movies_folder(self):
        """Select the movie folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Movies Folder",
            self.movies_path
        )
        if folder:
            self.movies_path = folder
            self.save_paths()
            self.refresh_movies()
    def select_tv_folder(self):
        """Select the TV folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select TV Shows Folder",
            self.tv_path
        )
        if folder:
            self.tv_path = folder
            self.save_paths()
            self.refresh_tv()
    def refresh_movies(self):
        """Rescan movies and update browse page"""
        self.movies = scan_movies(self.movies_path)
        print(f"Total Movies: {len(self.movies)}")

        self.browse_page = create_movies_browse_page(
            self.movies,
            self.on_item_clicked,
            "🎬",
            switch_to_tv_callback=self.switch_to_tv,
            switch_to_home_callback=self.switch_to_home,
            movies_folder_callback=self.select_movies_folder
        )
        #update stack
        self.stack.removeWidget(self.stack.widget(1))
        self.stack.insertWidget(1, self.browse_page)
        self.stack.setCurrentWidget(self.browse_page)
    def refresh_tv(self):
        """Rescan TV shows and update browse page"""
        self.tv_shows = scan_tv(self.tv_path)
        print(f"Total TV Shows: {len(self.tv_shows)}")
        
        self.tv_browse_page = create_tv_browse_page(
            self.tv_shows,
            self.on_show_clicked,
            "📺",
            switch_to_movies_callback=self.switch_to_movies,
            switch_to_home_callback=self.switch_to_home,
            tv_folder_callback=self.select_tv_folder
        )
        
        # Update stack
        self.stack.removeWidget(self.stack.widget(2))
        self.stack.insertWidget(2, self.tv_browse_page)
        self.stack.setCurrentWidget(self.tv_browse_page) 
    def load_paths(self):
        """Load saved paths if they exist"""
        try:
            with open("media_paths.txt", "r") as f:
                lines = f.readlines()
                if len(lines) >= 1:
                    self.movies_path = lines[0].strip()
                if len(lines) >= 2:
                    self.tv_path = lines[1].strip()
        except FileNotFoundError:
            pass
    def save_paths(self):
        """Save current paths to file"""
        with open("media_paths.txt", "w") as f:
            f.write(self.movies_path + "\n")
            f.write(self.tv_path + "\n")
    # =========================
    # 🎬 CLICK HANDLER
    # =========================
    def on_item_clicked(self, movie_list):
        movie = movie_list[0]
        print("Playing:", movie["title"])

        # Remove old player
        if hasattr(self, "player"):
            self.player.player.stop()
            self.player.setParent(None)

        # Create new player
        self.player = VideoPlayer(movie["path"], self.go_back, video_type='movie')
        self.player_layout.addWidget(self.player)

        # Switch to player
        self.stack.setCurrentWidget(self.player_page)
    def on_show_clicked(self, show_list):
        """Handle click on a tv show tile"""
        show = show_list[0]
        print(f"Selected show: {show['title']} ({show['genre']})")
        
        # Scan seasons for this show
        seasons = scan_tv_seasons(show["path"])

        # Create show data with seasons
        show_data = {
            "title": show["title"],
            "genre": show["genre"],
            "path": show["path"],
            "poster": show["poster"],
            "seasons": seasons
        }

        # Store for next episode logic
        self.current_seasons_data = show_data

        # Create the seasons page
        self.tv_seasons_page = create_tv_seasons_episodes_page(
            show_data,
            self.on_episode_clicked,
            switch_to_tv_callback=self.switch_to_tv
        )

        # Add to stack and switch to it
        self.stack.addWidget(self.tv_seasons_page)
        self.stack.setCurrentWidget(self.tv_seasons_page)
    def on_episode_clicked(self, episode_data):
        """Handle click on an episode"""
        print(f"Playing episode: {episode_data['title']}")

        # remove old player
        if hasattr(self, "player"):
            self.player.player.stop()
            self.player.setParent(None)
        
        # Store current episode for next episode logic
        self.current_episode = episode_data
        
        # Create new player
        self.player = VideoPlayer(
            episode_data["path"], 
            self.go_back,
            video_type='episode',
            next_episode_callback=self.play_next_episode,
            episode_list_callback=self.get_episodes_data
            )
        self.player.play_episode_callback = self.on_episode_clicked
        self.player_layout.addWidget(self.player)

        # Switch to player
        self.stack.setCurrentWidget(self.player_page)  
    def get_episodes_data(self):
        """Return episodes data for the episode list popup"""
        if hasattr(self, 'current_seasons_data'):
            return self.current_seasons_data['seasons']
        return None
    def play_next_episode(self):
        """Play the next episode in the current show"""
        # Debug checks
        print("=== play_next_episode called ===")
        print(f"Has current_episode: {hasattr(self, 'current_episode')}")
        print(f"Has current_seasons_data: {hasattr(self, 'current_seasons_data')}")
        
        if not hasattr(self, 'current_episode'):
            print("ERROR: No current_episode")
            return
        
        if not hasattr(self, 'current_seasons_data'):
            print("ERROR: No current_seasons_data")
            return
        
        print(f"Current episode: {self.current_episode['title']}")
        print(f"Seasons data: {self.current_seasons_data['title']}")
        print(f"Seasons keys: {list(self.current_seasons_data['seasons'].keys())}")
        
        # Flatten all episodes into a single list
        all_episodes = []
        for season_name, episodes in self.current_seasons_data['seasons'].items():
            print(f"  Season: {season_name}, Episodes: {len(episodes)}")
            for ep in episodes:
                all_episodes.append({
                    'episode': ep,
                    'season': season_name
                })
                print(f"    - {ep['title']}")
        
        print(f"Total episodes: {len(all_episodes)}")
        
        # Find current episode index
        current_index = -1
        for i, ep_data in enumerate(all_episodes):
            if ep_data['episode']['path'] == self.current_episode['path']:
                current_index = i
                break
        
        print(f"Current index: {current_index}")
        
        # Play next episode if available
        if current_index >= 0 and current_index + 1 < len(all_episodes):
            next_ep = all_episodes[current_index + 1]
            print(f"Playing next episode: {next_ep['episode']['title']}")
            self.current_episode = next_ep['episode']
            self.on_episode_clicked(next_ep['episode'])
        else:
            print("No more episodes available")
    def go_back_to_seasons(self):
        """Go back from player to seasons page"""
        if hasattr(self, "player"):
            self.save_current_progress()
            self.player.player.stop()
        self.stack.setCurrentWidget(self.tv_seasons_page)
    # =========================
    # 🔙 BACK
    # =========================
    def go_back(self):
        """Go back to home page"""
        if hasattr(self, "player"):
            # exit fullscreen if active
            was_maximized = self.window().isMaximized()

            if self.player.is_fullscreen:
                if hasattr(self.player, 'was_maximized') and self.player.was_maximized:
                    self.window().showMaximized()
                else:
                    self.window().showNormal()
                self.player.is_fullscreen=False
            self.save_current_progress()
            self.player.player.stop()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        QApplication.restoreOverrideCursor
        self.create_home_page()
        self.stack.setCurrentWidget(self.home_page)      
    def go_back_to_home(self):
        """Go back from player to home page"""
        if hasattr(self, "player"):
            self.save_current_progress()
            self.player.player.stop()
        self.create_home_page()
        self.stack.setCurrentWidget(self.home_page)
    # =========================
    # Extra
    # =========================
    def closeEvent(self, event):
        """Save progress when application is closed"""
        self.save_current_progress()
        event.accept()
# Create global watch tracker instance
watch_tracker = WatchTracker()
# VLC cache gen (runs to video player opens faster)
run_vlc_cache_gen()

# Set the app user model ID BEFORE creating QApplication
if sys.platform == "win32":
    myappid = 'lmwt.media.player.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
app = QApplication(sys.argv)
app.setWindowIcon(QIcon("icon.ico"))

window = MainWindow()
window.show()
sys.exit(app.exec())