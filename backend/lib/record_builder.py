# record_builder.py
import pandas as pd
import math

class RecordBuilder:
    """Builds per-row JSON records from CSV contribution data."""

    @staticmethod
    def sensor_domain(name: str) -> str:
        s = name.lower()
        if ("temperature" in s) or s.startswith(("t_", "temp", "tch", "temp_")):
            return "Temperature"
        # if ("pressure" in s) or s.startswith(("p_", "press", "pch", "pres")):
        #     return "Pressure"
        if ("voltage" in s) or s.startswith(("v_ch", "v_", "volt", "vch")):
            return "Voltage"

        return "Other"

    def build_records_from_csv(self, df: pd.DataFrame):
        sensors = [
            c.removeprefix("contribution_")
            for c in df.columns
            if c.startswith("contribution_")
        ]
        domain_types = ["Temperature", "Voltage"]
        sensor_to_domain = {s: self.sensor_domain(s) for s in sensors}

        records = []
        counts = {d: 0 for d in domain_types}
        for s in sensors:
            d = sensor_to_domain[s]
            if d in counts:
                counts[d] += 1
        sensors_countMin = min(counts.values())
        top_k = sensors_countMin + 1

        for i in range(len(df)):
            row = df.iloc[i]
            per_sensor = {s: float(row[f"contribution_{s}"]) for s in sensors}
            by_dom = {d: [] for d in domain_types}
            for s in sensors:
                d = sensor_to_domain[s]
                v = per_sensor[s]
                if d in by_dom:
                    by_dom[d].append({"name": s, "value": v})
            domains_info = [{"name": d, "sensors": by_dom[d]} for d in domain_types if by_dom[d]]
  

   
            domain_scores = {}
            for d, sensors_list in by_dom.items():
                if not sensors_list:
                    continue
                sorted_vals = sorted([x["value"] for x in sensors_list], reverse=True)
    
                k = min(top_k, len(sorted_vals))
                domain_scores[d] = sum(sorted_vals[:k]) / math.sqrt(top_k)

            ranking = sorted(
                [{"name": d, "score": float(domain_scores.get(d, 0.0))} for d in domain_types],
                key=lambda x: x["score"], reverse=True,
            )

            if len(ranking) >= 2 and ranking[0]["score"] > 0:
                ratio = ranking[1]["score"] / ranking[0]["score"]
                cross_domain = ratio >= 0.95
            else:
                ratio = 0.0
                cross_domain = False
            records.append({    
                "domains": domains_info,
                "ranking": ranking,
                "ratio_2_over_1": ratio,
                "cross_domain_close": cross_domain})  
        return records
