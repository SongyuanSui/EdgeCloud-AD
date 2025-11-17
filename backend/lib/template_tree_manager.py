# template_tree_manager.py
import os
import re
import json
import shutil
from typing import Dict
from .tree_node import TreeNode

class TemplateTreeManager:
    """Handles tree creation, structure traversal, and LLM-driven expansions."""

    def __init__(self, base_path="templates_storage", reset: bool = False):
        self.base_path = base_path
        if reset and os.path.exists(base_path):
            shutil.rmtree(base_path)
        os.makedirs(base_path, exist_ok=True)
        self.tree = self._load_tree_from_fs(base_path)

    def _load_tree_from_fs(self, base_path: str) -> TreeNode:
        root = TreeNode("root", folder_path=base_path)
        self._load_children(root)
        return root

    def _load_children(self, node: TreeNode) -> None:
        if not node.folder_path or not os.path.isdir(node.folder_path):
            return
        node.update_templates()
        for name in sorted(os.listdir(node.folder_path)):
            p = os.path.join(node.folder_path, name)
            if os.path.isdir(p):
                child = TreeNode(name, folder_path=p)
                node.children[name] = child
                self._load_children(child)
    def find_path_by_template(self, template_text: str):
        def dfs(node: TreeNode, cur):
            node.update_templates()
            if template_text in node.templates:
                return cur
            for name, child in node.children.items():
                got = dfs(child, cur + [name])
                if got is not None:
                    return got
            return None
        return dfs(self.tree, []) or []
    def tree_structure(self, node, for_display=False):
        if node.is_leaf():
            node.update_templates()
            return node.templates[-1:] if (for_display and node.templates) else node.templates.copy()
        return {k: self.tree_structure(v, for_display) for k, v in node.children.items()}

    def horizontal_expansion(self, tree, new_template, agent, prompt_text, ts):
        prompt = prompt_text + "Error Tree:\n" + json.dumps(
            self.tree_structure(tree, for_display=False), indent=2, ensure_ascii=False
        ) + f"\n\nTemplate:\n{new_template}\n\nExplanation:\n"
        response = agent.run(prompt)
        print("Horizontal expansion response:\n", response)
        if "Addition" not in response:
            raise RuntimeError(f"No 'Addition' found in response:\n{response}")
        route_match = re.findall(r"\((.*?)\)", response.split("Addition:")[-1])
        if not route_match:
            raise RuntimeError(f"Failed to parse route from:\n{response}")
        parts = [p.strip() for p in route_match[0].split("->") if p.strip() and p.strip() != "<END>"]
        node = tree
        for error_type in parts:
            if error_type in node.children:
                node = node.children[error_type]
            else:
                new_folder = os.path.join(node.folder_path, error_type)
                os.makedirs(new_folder, exist_ok=True)
                new_leaf = TreeNode(error_type, folder_path=new_folder)
                new_leaf.add_template(new_template, ts=ts)
                node.children[error_type] = new_leaf
                return new_leaf
        node.add_template(new_template, ts=ts)
        return node

    def vertical_expansion(self, parent_node, leaf_node, new_template, agent, prompt_text, ts):
        leaf_node.update_templates()
        few_shot = leaf_node.templates.copy()
        prompt = prompt_text + f"\nParent Category: {leaf_node.name}\n\nList 1: {json.dumps(few_shot)}\nList 2: {json.dumps([new_template])}\n"
        response = agent.run(prompt)
        print("Vertical expansion response:\n", response)
        names = re.findall(r"<(.*?)>", response)
        if len(names) == 2 and names[0] != names[1]:
            old_folder = leaf_node.folder_path
            c1_name, c2_name = names
            c1_folder = os.path.join(old_folder, c1_name)
            c2_folder = os.path.join(old_folder, c2_name)
            os.makedirs(c1_folder, exist_ok=True)
            os.makedirs(c2_folder, exist_ok=True)
            c1 = TreeNode(c1_name, folder_path=c1_folder)
            c2 = TreeNode(c2_name, folder_path=c2_folder)
            for f in os.listdir(old_folder):
                if f.endswith(".txt"):
                    shutil.move(os.path.join(old_folder, f), os.path.join(c1_folder, f))
            c1.update_templates()
            c2.add_template(new_template, ts=ts)
            leaf_node.templates = []
            leaf_node.children = {c1_name: c1, c2_name: c2}
            return c2
        else:
            leaf_node.add_template(new_template, ts=ts)
            return leaf_node
        
    def _build_node_from_fs(self, folder_path: str, name: str):
        """Rehydrate a TreeNode from the filesystem recursively."""
        node = TreeNode(name=name, folder_path=folder_path)
        try:
            entries = sorted(os.listdir(folder_path))
        except FileNotFoundError:
            entries = []
        for entry in entries:
            child_path = os.path.join(folder_path, entry)
            if os.path.isdir(child_path):
                node.children[entry] = self._build_node_from_fs(child_path, entry)
        node.update_templates()  # loads template file contents into node.templates
        return node

    def _node_to_simple(self, node: "TreeNode"):
        """Leaf → list[str]; Internal → dict[str, ...]."""
        if node.children:
            return { child.name: self._node_to_simple(child) for child in node.children.values() }
        # leaf
        return node.templates

    def simple_tree_dict(self):
        """
        Build a rootless simple dict:
        { "<TopCategory>": <list or dict>, ... }
        """
        result = {}
        try:
            for entry in sorted(os.listdir(self.base_path)):
                p = os.path.join(self.base_path, entry)
                if os.path.isdir(p):
                    top = self._build_node_from_fs(p, entry)
                    result[entry] = self._node_to_simple(top)
        except FileNotFoundError:
            pass
        return result

    def export_tree_simple_json(self, out_path: str):
        """Write the simple tree JSON to file and return the dict."""
        data = self.simple_tree_dict()
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
        
    def update_sensor_tree(self, tree, event, agent, h_prompt, v_prompt):
        route_parts = event.get("error_code", "").split(":") if event.get("error_code") else []
        path_found = bool(event.get("path_found", False))

        # If no route or LLM says path not found → Horizontal expansion
        if not route_parts or not path_found:
            return self.horizontal_expansion(tree, event["template"], agent, h_prompt, ts=event["ts"])

        # LLM says path IS found; walk it to locate the node.
        parent, node = None, tree
        for part in route_parts:
            parent = node
            node = node.children.get(part)
            if node is None:
                # Inconsistent (LLM said found but path missing) → fall back horizontal
                return self.horizontal_expansion(tree, event["template"], agent, h_prompt, ts=event["ts"])

        # If the final node is a leaf → Vertical expansion
        if node.is_leaf():
            return self.vertical_expansion(parent, node, event["template"], agent, v_prompt, ts=event["ts"])

        # If the final node is internal (has children), we cannot split a non-leaf;
        # attach horizontally (prompt will guide adding an appropriate child).
        return self.horizontal_expansion(tree, event["template"], agent, h_prompt, ts=event["ts"])

