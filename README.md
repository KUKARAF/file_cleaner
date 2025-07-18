# Media File Organizer

An AI-powered tool that uses LangChain to automatically organize movie, TV show, and audiobook files into a clean, standardized format.

## Features

- **TMDB Integration**: Searches The Movie Database for accurate movie and TV show information
- **Smart File Operations**: Moves and renames files with proper error handling
- **Multiple Media Types**: Supports movies, TV series, and audiobooks
- **AI-Powered**: Uses LLM to make intelligent decisions about file organization
- **Jinja2 Templates**: Customizable prompts for different media types

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Get API keys:
   - OpenRouter API key from https://openrouter.ai/
   - TMDB API key from https://www.themoviedb.org/settings/api

## Usage

```bash
python main.py <directory_path> <media_type>
```

### Examples

```bash
# Organize movies
python main.py /path/to/movies movie

# Organize TV shows
python main.py /path/to/tv-shows tv

# Organize audiobooks
python main.py /path/to/audiobooks audiobook
```

## File Organization Formats

### Movies
```
Movie Title (Year)/
└── Movie Title (Year).ext
```

### TV Shows
```
Show Title (Year)/
├── Season 01/
│   ├── Show Title (Year) - S01e01 - Episode Title.ext
│   └── Show Title (Year) - S01e02 - Episode Title.ext
└── Season 02/
    └── ...
```

### Audiobooks
```
Author Name/
├── Book Title (Year)/
│   └── Book Title.ext
└── Series Name/
    └── 01 - Book Title (Year)/
        └── Book Title.ext
```

## How It Works

1. **Directory Analysis**: Scans the target directory for media files
2. **TMDB Search**: Uses TMDB API to get accurate metadata
3. **AI Decision Making**: LLM analyzes filenames and determines proper organization
4. **File Operations**: Moves and renames files according to standards
5. **Progress Tracking**: Marks files as completed to avoid reprocessing

## Customization

Edit the Jinja2 templates in the `templates/` directory to customize the AI prompts for different media types.
