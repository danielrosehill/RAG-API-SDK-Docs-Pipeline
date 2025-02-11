import sys
import csv
import json
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QTextEdit)
from PyQt6.QtCore import Qt
from urllib.parse import urlparse

class CheckableListWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.checkboxes = {}
        
    def add_item(self, text, checked=False):
        from PyQt6.QtWidgets import QCheckBox
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        self.checkboxes[text] = checkbox
        self.layout.addWidget(checkbox)
        
    def get_checked_items(self):
        return [text for text, cb in self.checkboxes.items() if cb.isChecked()]
    
    def set_checked_items(self, items):
        for text, cb in self.checkboxes.items():
            cb.setChecked(text in items)

class DocsRepoSyncUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docs Repo Sync Utility")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize repos data dictionary
        self.repos_data = {}
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Docs base path selection
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton("Browse")
        path_button.clicked.connect(self.browse_path)
        path_layout.addWidget(QLabel("Docs Base Path:"))
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)
        
        # Repos list with checkboxes
        self.repo_list = CheckableListWidget()
        layout.addWidget(QLabel("Select Repositories:"))
        layout.addWidget(self.repo_list)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.output_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        update_button = QPushButton("Update Config")
        sync_button = QPushButton("Sync Repos")
        update_button.clicked.connect(self.update_config)
        sync_button.clicked.connect(self.sync_repos)
        button_layout.addWidget(update_button)
        button_layout.addWidget(sync_button)
        layout.addLayout(button_layout)
        
        # Load saved config and repos
        self.load_saved_config()
        self.load_repos()

    def load_repos(self):
        try:
            repos = []
            with open('repos.csv', 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row:  # Skip empty rows
                        repos.append(row['name'])
                        self.repos_data[row['name']] = row
            
            # Sort repositories alphabetically
            repos.sort()
            
            # Add to list widget
            for repo in repos:
                self.repo_list.add_item(repo, repo in self.saved_config.get('repos', []))
                
        except FileNotFoundError:
            self.log_output("repos.csv not found")

    def browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Docs Base Directory")
        if folder:
            self.path_input.setText(folder)

    def update_config(self):
        selected_repos = self.repo_list.get_checked_items()
        config = {
            "docs_base": self.path_input.text(),
            "repos": selected_repos
        }
        
        with open('.meta', 'w') as file:
            json.dump(config, file, indent=4)
        
        self.saved_config = config
        self.log_output("Configuration updated successfully")

    def get_repo_folder_name(self, repo_url):
        # Extract the repository name from the URL
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Handle special cases like tree/master/docs
        if 'tree' in path_parts:
            tree_index = path_parts.index('tree')
            return path_parts[tree_index - 1]
        
        return path_parts[-1]

    def sync_repos(self):
        self.log_output("Starting sync process...")
        selected_repos = self.repo_list.get_checked_items()
        
        if not selected_repos:
            self.log_output("No repositories selected")
            return
            
        docs_base = self.path_input.text()
        if not docs_base:
            self.log_output("No docs base path specified")
            return
            
        # Create docs base directory if it doesn't exist
        os.makedirs(docs_base, exist_ok=True)
        
        for repo_name in selected_repos:
            repo_data = self.repos_data.get(repo_name)
            if not repo_data:
                self.log_output(f"Error: No data found for {repo_name}")
                continue
                
            repo_url = repo_data['repo_url']
            if not repo_url:
                self.log_output(f"Error: No URL found for {repo_name}")
                continue
                
            self.log_output(f"Syncing {repo_name}...")
            
            # Determine the target directory
            repo_folder = self.get_repo_folder_name(repo_url)
            target_dir = os.path.join(docs_base, repo_folder)
            
            try:
                if not os.path.exists(target_dir):
                    # Clone the repository
                    self.log_output(f"Cloning {repo_url} to {target_dir}")
                    subprocess.run(['git', 'clone', repo_url, target_dir], 
                                 check=True, 
                                 capture_output=True, 
                                 text=True)
                else:
                    # Pull latest changes if repository exists
                    self.log_output(f"Pulling latest changes for {repo_name}")
                    subprocess.run(['git', '-C', target_dir, 'pull'], 
                                 check=True, 
                                 capture_output=True, 
                                 text=True)
                
                self.log_output(f"Successfully synced {repo_name}")
                
            except subprocess.CalledProcessError as e:
                self.log_output(f"Error syncing {repo_name}: {e.stderr}")
            except Exception as e:
                self.log_output(f"Unexpected error syncing {repo_name}: {str(e)}")
        
        self.log_output("Sync completed!")

    def load_saved_config(self):
        try:
            with open('.meta', 'r') as file:
                self.saved_config = json.load(file)
                self.path_input.setText(self.saved_config.get('docs_base', ''))
        except FileNotFoundError:
            self.saved_config = {"docs_base": "", "repos": []}

    def log_output(self, message):
        self.output_text.append(message)

def main():
    app = QApplication(sys.argv)
    window = DocsRepoSyncUtility()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()