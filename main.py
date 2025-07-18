#!/usr/bin/env python3
"""
Media File Organizer using LangChain
Organizes movies, TV series, and audiobooks using AI-powered file operations
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from jinja2 import Environment, FileSystemLoader

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not OPENROUTER_API_KEY:
    print("Please set OPENROUTER_API_KEY environment variable")
    sys.exit(1)

if not TMDB_API_KEY:
    print("Please set TMDB_API_KEY environment variable")
    sys.exit(1)

@dataclass
class MediaInfo:
    title: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    media_type: str = "movie"  # movie, tv, audiobook

class MediaOrganizer:
    def __init__(self, target_directory: str, media_type: str):
        self.target_directory = Path(target_directory)
        self.media_type = media_type
        self.processed_files = set()
        self.hash_filename = ".media_hashes.json"
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="anthropic/claude-3.5-sonnet",
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        
        # Create agent with tools
        self.tools = [self.search_tmdb, self.move_rename_file, self.mark_completed, self.calculate_folder_hashes]
        self.agent = self._create_agent()
        
    def _create_agent(self):
        """Create the LangChain agent with tools"""
        prompt_template = self.jinja_env.get_template(f'{self.media_type}_prompt.j2')
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template.render()),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    
    @tool
    def search_tmdb(query: str, media_type: str = "movie") -> str:
        """Search TMDB for movie or TV show information"""
        if media_type == "tv":
            url = f"https://api.themoviedb.org/3/search/tv"
        else:
            url = f"https://api.themoviedb.org/3/search/movie"
            
        params = {
            "api_key": TMDB_API_KEY,
            "query": query,
            "language": "en-US"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["results"]:
                result = data["results"][0]
                if media_type == "tv":
                    return json.dumps({
                        "title": result.get("name", ""),
                        "year": result.get("first_air_date", "")[:4] if result.get("first_air_date") else "",
                        "overview": result.get("overview", "")
                    })
                else:
                    return json.dumps({
                        "title": result.get("title", ""),
                        "year": result.get("release_date", "")[:4] if result.get("release_date") else "",
                        "overview": result.get("overview", "")
                    })
            else:
                return json.dumps({"error": "No results found"})
                
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @tool
    def move_rename_file(old_path: str, new_path: str) -> str:
        """Move and rename a file or folder"""
        try:
            old_path = Path(old_path)
            new_path = Path(new_path)
            
            if not old_path.exists():
                return f"Error: Source path {old_path} does not exist"
            
            # Create parent directories if they don't exist
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file/folder
            shutil.move(str(old_path), str(new_path))
            return f"Successfully moved {old_path} to {new_path}"
            
        except Exception as e:
            return f"Error moving file: {str(e)}"
    
    @tool
    def mark_completed(file_path: str) -> str:
        """Mark a file as completed and properly organized"""
        return f"File {file_path} has been marked as completed and properly organized."

    @tool
    def calculate_folder_hashes(folder_path: str) -> str:
        """Calculate MD5 hashes for all files in a folder and save them to a hash file"""
        try:
            folder = Path(folder_path)
            if not folder.is_dir():
                return f"Error: {folder_path} is not a directory"

            hash_file = folder / ".media_hashes.json"
            file_hashes = {}

            for file_path in folder.rglob("*"):
                if file_path.is_file() and file_path.name != ".media_hashes.json":
                    md5_hash = hashlib.md5()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            md5_hash.update(chunk)
                    file_hashes[str(file_path.relative_to(folder))] = md5_hash.hexdigest()

            with open(hash_file, "w") as f:
                json.dump(file_hashes, f, indent=2)

            return f"Successfully created hash file for {folder_path}"

        except Exception as e:
            return f"Error calculating hashes: {str(e)}"

    def get_directory_state(self) -> Dict[str, Any]:
        """Get current state of the target directory"""
        files = []
        for item in self.target_directory.rglob("*"):
            if item.is_file():
                # Skip if the file is a hash file
                if item.name == self.hash_filename:
                    continue
                    
                # Skip if parent directory has a hash file
                if (item.parent / self.hash_filename).exists():
                    continue
                    
                # Skip if already processed
                if str(item) not in self.processed_files:
                    files.append({
                        "path": str(item),
                        "name": item.name,
                        "size": item.stat().st_size,
                        "parent": str(item.parent)
                    })
        
        return {
            "directory": str(self.target_directory),
            "media_type": self.media_type,
            "files": files,
            "total_files": len(files)
        }
    
    def organize(self):
        """Main organization loop"""
        while True:
            directory_state = self.get_directory_state()
            
            if not directory_state["files"]:
                print("No more files to process!")
                break
            
            # Prepare input for the agent
            input_data = {
                "input": f"Please organize the files in this {self.media_type} directory. Current state: {json.dumps(directory_state, indent=2)}"
            }
            
            try:
                result = self.agent.invoke(input_data)
                print(f"Agent result: {result}")
                
                # Check if any files were marked as completed
                if "marked as completed" in result.get("output", "").lower():
                    # Add processed files to the set (simplified - in real implementation, 
                    # you'd parse the agent's actions more carefully)
                    for file_info in directory_state["files"][:1]:  # Process one at a time
                        self.processed_files.add(file_info["path"])
                
            except Exception as e:
                print(f"Error during organization: {e}")
                break

def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <directory_path> <media_type>")
        print("Media types: movie, tv, audiobook")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    media_type = sys.argv[2]
    
    if media_type not in ["movie", "tv", "audiobook"]:
        print("Invalid media type. Use: movie, tv, or audiobook")
        sys.exit(1)
    
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} does not exist")
        sys.exit(1)
    
    organizer = MediaOrganizer(directory_path, media_type)
    organizer.organize()

if __name__ == "__main__":
    main()
