# tree_node.py
import os
import shutil
from datetime import datetime

class TreeNode:
    """Represents a node in the anomaly/error tree."""

    def __init__(self, name, folder_path=None):
        self.name = name
        self.children = {}
        self.templates = []
        self.folder_path = folder_path

    def is_leaf(self):
        return len(self.children) == 0

    def update_templates(self):
        if not self.folder_path or not os.path.isdir(self.folder_path):
            self.templates = []
            return
        files = sorted([f for f in os.listdir(self.folder_path) if f.endswith(".txt")])
        new_templates = []
        for fname in files:
            with open(os.path.join(self.folder_path, fname), "r", encoding="utf-8") as fh:
                new_templates.append(fh.read().strip())
        self.templates = new_templates

    def add_template(self, content, ts):
        if ts is None or str(ts).strip() == "":
            raise ValueError(f"'ts' is required for node '{self.name}'")
        if not self.folder_path:
            raise ValueError(f"Folder path not set for node '{self.name}'.")
        os.makedirs(self.folder_path, exist_ok=True)
        ts_str = str(ts).strip()
        safe = (ts_str.replace(":", "").replace("-", "")
                        .replace(" ", "_").replace("/", "")
                        .replace("\\", ""))

        fname = f"{safe}.txt"
        path = os.path.join(self.folder_path, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.update_templates()
