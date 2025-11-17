# main.py
import os
from lib.anomaly_tree_builder import AnomalyTreeBuilder

from lib.my_prompts import (
    Contribution_Score_Analysis_Prompt,
    horizontal_expansion_few_shot,
    VERTICAL_EXPANSION_FEW_SHOT,
    ROUTE_SELECTION_FEW_SHOT,
)

def generate_anomaly_tree(
    csv_path="backend_anomaly_contribution_results.csv",
):
    """
    Run the anomaly tree builder with the provided CSV and prompts.
    This function can be imported and called programmatically.
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    """
    Run the anomaly tree builder with the provided CSV and prompts.
    This function can be imported and called programmatically.
    """
    os.environ["OPENAI_API_KEY"] = openai_api_key
    prompts = {
        "contribution": Contribution_Score_Analysis_Prompt,
        "horizontal": horizontal_expansion_few_shot,
        "vertical": VERTICAL_EXPANSION_FEW_SHOT,
        "route": ROUTE_SELECTION_FEW_SHOT,
    }

    builder = AnomalyTreeBuilder(
        csv_path=csv_path,
        prompts=prompts
    )
    builder.run()
