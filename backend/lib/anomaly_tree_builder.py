# anomaly_tree_builder.py
import json
import re
import pandas as pd
from .gpt_agent import GPTAgent
from .record_builder import RecordBuilder
from .template_tree_manager import  TemplateTreeManager
import os
class AnomalyTreeBuilder:
    """High-level orchestrator for building and updating anomaly trees."""

    def __init__(self, csv_path, prompts, base_path="templates_storage", reset_tree=False):
        self.csv_path = csv_path
        self.prompts = prompts
        self.agent = GPTAgent()
        self.tree_manager = TemplateTreeManager(base_path=base_path, reset=reset_tree)
        self.record_builder = RecordBuilder()
    def parse_found_line(self, response):
        m = re.search(r"Found:\s*(YES|NO|True|False)", response, flags=re.I)
        if not m:
            return None
        val = m.group(1).strip().lower()
        return val in ("yes", "true")
    
    def parse_route_line(self, response):
        m = re.search(r"Route:\s*\((.*?)\)", response, flags=re.S)
        if not m:
            raise RuntimeError(f"Failed to parse route from:\n{response}")
        return [p.strip() for p in m.group(1).split("->") if p.strip()]

    def route_from_llm(self, tree, template):
        prompt = self.prompts["route"] + "Error Tree:\n" + json.dumps(
            self.tree_manager.tree_structure(tree, for_display=False), indent=2, ensure_ascii=False
        ) + f"\n\nTemplate:\n{template}\n"

        response = self.agent.run(prompt)
        print("ROUTE_SELECTION response:\n", response)

        parts = self.parse_route_line(response)
        found_flag = self.parse_found_line(response)

        # Safety: verify whether the path actually exists in the current tree.
        node = tree
        exists_all = True
        for seg in parts:
            node = node.children.get(seg)
            if node is None:
                exists_all = False
                break

        # If LLM said YES but we can’t resolve it in the real tree, override to NO.
        if found_flag is None:
            path_found = exists_all
        else:
            path_found = found_flag and exists_all

        # Previous safety: if LLM returns a deeper path whose first segment is new,
        # truncate to just the top-level. This also implies path_found = False.
        if parts:
            first = parts[0]
            if len(parts) > 1 and first not in tree.children:
                parts = [first]
                path_found = False

        return ":".join(parts), path_found

    def extract_template_from_llm(self, record):
        prompt = self.prompts["contribution"] + "\nThis is the per-row data (JSON):\n" + json.dumps(record)
        raw = self.agent.run(prompt)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"Invalid JSON from LLM: {raw}")
        obj = json.loads(raw[start:end + 1])
        template = str(obj.get("template", "")).strip()
        if not template:
            raise ValueError("LLM JSON missing 'template'.")
        return template

    def run(self, save_augmented_csv: bool = True, out_path: str = None):
        df = pd.read_csv(self.csv_path)
        records = self.record_builder.build_records_from_csv(df)
        tree = self.tree_manager.tree
        
        classifications, templates = [], []

        for idx, rec in enumerate(records):
            template_text = self.extract_template_from_llm(rec)
            print(template_text)
            ts_val = df.iloc[idx]["ts"]
            ev = {"template": template_text}
            route_str, path_found = self.route_from_llm(tree, ev["template"])
            ev["error_code"] = route_str
            ev["path_found"] = path_found
            ev["ts"] = ts_val
            self.tree_manager.update_sensor_tree(
                tree, ev, self.agent, self.prompts["horizontal"], self.prompts["vertical"]
            )


            # derive final classification path by searching where the template landed
            path_segments = self.tree_manager.find_path_by_template(template_text)
            classifications.append(" -> ".join(path_segments))
            templates.append(template_text)

        # print JSON view of the tree (latest template per leaf if for_display=True)
        print(json.dumps(self.tree_manager.tree_structure(tree, for_display=True),
                         indent=2, ensure_ascii=False))

        # build and optionally save augmented CSV
        df_out = df.copy()
        df_out["classification"] = classifications
        df_out["template"] = templates

        if save_augmented_csv:
            if out_path is None:
                base_dir = os.path.dirname(self.csv_path) or "."
                out_path = os.path.join(base_dir, "anomaly_results_classified.csv")
            # Append if file exists, otherwise write with header
            append_mode = 'a' if os.path.exists(out_path) else 'w'
            include_header = not os.path.exists(out_path)
            df_out.to_csv(out_path, mode=append_mode, header=include_header, index=False)
            print(f"[{'appended' if append_mode=='a' else 'saved'}] {out_path}")
        # tree_json = self.tree_manager.export_tree_json(
        #     out_path=(os.path.splitext(self.csv_path)[0] + "__tree.json")
        # )

        # choose consistent JSON filename next to the CSV/input directory
        base_dir_for_json = os.path.dirname(out_path) if save_augmented_csv else (os.path.dirname(self.csv_path) or ".")
        json_out = os.path.join(base_dir_for_json, "anomaly_results_classified_tree.json")
        _ = self.tree_manager.export_tree_simple_json(json_out)
        print(f"[saved] {json_out}")

        return {
            "json_out": json_out,      
            "csv_df": df_out,          

        }

