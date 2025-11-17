# my_prompts.py

Contribution_Score_Analysis_Prompt = r"""
You generate one compact, old-style natural-language template used by our v1 tree builder.

INPUT (unchanged)
You receive ONE JSON object with:
{
  "domains": [
    { "name": "Temperature", "sensors": [ { "name": "<sensor>", "value": <float> }, ... ] },
    { "name": "Pressure",    "sensors": [ { "name": "<sensor>", "value": <float> }, ... ] },
    { "name": "Voltage",     "sensors": [ { "name": "<sensor>", "value": <float> }, ... ] }
  ],
  "ranking": [
    { "name": "<D1>", "score": <float> },   // sorted DESC by score; treat as authoritative
    { "name": "<D2>", "score": <float> }
  ],
  "ratio_2_over_1": <float>,
  "cross_domain_close": <bool>
}

General rules
- Never recompute scores; use 'ranking' as truth.
- Round numeric values to 2 decimals and prefix with "~".
- When listing sensors for any mentioned domain:
  • Sort by 'value' DESC.
  • Include sensors with value ≥ 0.50; if none ≥ 0.50, include the top few that best characterize the pattern.
- Output MUST be EXACTLY: {"template":"<one concise sentence>."}

Single-domain (cross_domain_close == false)
- Let D1 = ranking[0].name.
- Describe the behavior for D1 only, e.g.:
  • "v_ch2 jumps sharply (contribution ~1.00) while other Voltage sensors stay near baseline."
  • "v_ch2 and v_ch7 are elevated (~0.85, ~0.79) while others remain low(~0.21)."

Cross-domain (cross_domain_close == true)  // NEAR-TIE semantics
- Let D1 = ranking[0].name, D2 = ranking[1].name.
- Compute pct = round(ratio_2_over_1 * 100).
- Use a near-tie phrasing and SHOW the ratio to verify closeness:
  • "D1 and D2 are Cross Domain. Total contribution scores for <D1> and <D2> are nearly tied (S2/S1 ~ <pct>%); <D1> {s1(~v1), s2(~v2)} vs <D2> {t1(~w1), t2(~w2)}."
  • Synonyms for “nearly tied” allowed: “very close”, “comparable”, “near balance”. 
- Keep it one sentence; list a few top sensors per domain, formatted inside braces.

Output:
{"template":"<your sentence>."}
"""




horizontal_expansion_few_shot = """You are given an error tree represented as a dictionary and a template describing a specific error. If the error path corresponding to the template cannot be found in the error tree, extend the error tree by adding a new branch at the appropriate location. Ensure that:
    - The new branch aligns logically with the existing structure of the error tree.
    - The template can be correctly integrated into the tree under the newly added branch.
    - Sensor IDs and domain labels in examples (Temp1..Temp3, Curr1..Curr4, Volt1..Volt2; Temp-related/Curr-related/Volt-related) are ILLUSTRATIVE ONLY. In reality, both the number of sensors and the domain names may differ (e.g., Pressure-related, Vibration-related).
    - Do NOT create per-sensor branches (no leaves named Temp1, Curr3, Volt2).

NAMING RULES (VERY IMPORTANT):
- Child node names should describe HOW MANY SENSORS IN A DOMAIN ARE DRIFTING TOGETHER.
  Common useful patterns:
  • SingleSensorDrift          → exactly one sensor in that domain is abnormal
  • PartialGroupDrift          → some sensors are abnormal, but clearly not most of them
  • MostSensorsDrift           → a clear majority of that domain's sensors are abnormal
  • UniformGroupDrift          → basically all sensors in that domain move together

- It's OK if wording is a tiny variation (e.g. "SingleSensorIssue" instead of "SingleSensorDrift").
- DO NOT create per-sensor leaves. Never name a branch "Temp1", "Curr3", "Volt2", etc.
- DO NOT name branches using speed/intensity adjectives like "sudden", "gradual", "sharp spike",
  "mild", "severe", "violent", "slow drift", etc. Category names must be about GROUP SIZE, not about rate.
- Domain anchors (like "Temp-related", "Pressure-related", "Volt-related", "Curr-related", etc.) may be introduced
  if that domain does not exist yet.

Give a clear explanation.
- Begin with one of:
• "Path not found:"  (Case A)
• "Internal node:"   (Case B)
- Case A (path not found): Explain what anchor/subtype is missing (e.g., no Volt-related or no PartialGroupDrift below Temp-related), why it is not possible for existing nodes to host it, and why it is worth adding a new branch there.
- Case B (right position for internal node): we saw an internal parent (i.e., not a leaf). We will temporarily refer to its current kids, mention why none of them agree with what we have, and note that vertical is not applied since the node is not a leaf. Then we will introduce a fresh child below this parent.

STRICT OUTPUT FORMAT:
- Explanation: <show the reason in detail>
- Line 1 MUST be: Addition: (<SEG1> -> <SEG2> -> ... -> <END>)
- Line 2 MUST be: Explanation: <short reason>

Here are some examples:

Example 1:
Error Tree:
{
    "Temp-related": {
        "UniformGroupSpike": "<END>",
        "SingleSensorDrift": "<END>"
    },
    "Curr-related": {
        "UniformGroupSpike": "<END>",
        "SingleSensorDrift": "<END>"
    }
}
Template:
"Sum of Temp1+Temp2+Temp3 contributions close related to Sum of Curr1+Curr2+Curr3+Curr4 contributions."

Addition: (Cross-domain -> <END>)
Explanation: Explanation: Path not found: the template compares directly total temperature and total current and exhibits a large difference (Sum(Temp*) is close related to Sum(Curr*)); the present Temp-related and Curr-related nodes are domain-specific and do not support mismatches between other domains, so we construct a Cross-domain anchor and collect these cases and refine the subtype afterwards.

Example 2:
Error Tree:
{
    "Temp-related": {
        "UniformGroupSpike": "<END>",
        "SingleSensorDrift": "<END>"
    },
    "Cross-domain": {
        "CrossDomainMismatch": "<END>"
    }
}
Template:
"Curr1, Curr2, Curr3, and Curr4 all slowly drift upward together."

Addition: (Curr-related -> <END>)
Explanation: Path not found: list contains sensors Curr1–Curr4 and exhibits uniform slow drift in that family; displays current domain, yet there is no Curr-related anchor in the tree, so we first construct the domain branch and decide upon the subtype later after seeing more examples.

Example 3:
Error Tree:
{
    "Temp-related": {
        "UniformGroupSpike": "<END>",
        "SingleSensorDrift": "<END>"
    },
    "Curr-related": {
        "UniformGroupSpike": "<END>",
        "SingleSensorDrift": "<END>"
    },
    "Cross-domain": {
        "CrossDomainMismatch": "<END>"
    }
}
Template:
"Temp1 and Temp2 show a gradual upward drift in contribution (e.g., 0.6→1.0), while Temp3 remains near baseline (~0.1)."
Addition: (Temp-related -> PartialGroupDrift  -> <END>)
Explanation: Internal node; we arrived at Temp-related (children: UniformGroupSpike, SingleSensorDrift), but there is a slow drift in a portion of the group evident in the template that none of the children exhibit; vertical is not applied because we are not at a leaf node, so we create a new child, called PartialGroupDrift, underneath this parent node in order to reveal this pattern.

Example 4:
Error Tree:
{
    "Temp-related": {
        "UniformGroupSpike": "<END>"
    },
    "Curr-related": {
        "UniformGroupSpike": "<END>"
    }
}
Template:
"Volt1 and Volt2 jump together abruptly."
Addition: (Volt-related -> <END>)
Explanation: Path not found: the problem clearly belongs to the voltage area, and both Volt1 and Volt2 jump suddenly at the same time. The tree has no Volt-related anchor, and Temp/Curr branches cannot have voltage problems. So, we create the voltage area first and improve the type later by expanding upward.
"""


VERTICAL_EXPANSION_FEW_SHOT  = """
You are organizing hierarchical categories and their associated few-shot examples. Currently, you have two lists of few-shot examples under the same leaf node. Your task is to decide whether these two lists can be meaningfully split into two distinct subcategories.

Constraints
- Sensor IDs and domain labels in examples (Temp1..Temp3, Curr1..Curr4, Volt1..Volt2; Temp-related/Curr-related/Volt-related) are ILLUSTRATIVE ONLY. Real apply may differ.
- Do NOT create per-sensor branches (no leaves named Temp1, Curr3, Volt2).
- If you SPLIT: produce exactly TWO new sub-leaf names (short, generic, CamelCase pattern names).
- If you MERGE: both lists must keep the original parent leaf name exactly.

Analyze the examples in the two lists to determine if there is a clear and meaningful distinction between them.
  - If a distinction exists, create two new sub-leaf names and assign each list to one of them.
  - If no distinction exists, retain both lists under the original parent leaf.

Write a clear Explanation
- Use as many sentences as needed to show your step‑by‑step reasoning. Describe what List 1 shows, what List 2 shows, what they have in common, any differences you consider, and why those differences do or do not warrant a split.
- Avoid angle brackets and quotes in your explanation.


CRITICAL NAMING RULE:
Category names must describe HOW MANY SENSORS IN A DOMAIN ARE DRIFTING TOGETHER.
Typical useful patterns:
- SingleSensorDrift            → exactly one sensor in that domain is abnormal
- PartialGroupDrift            → some sensors in the domain are abnormal, but clearly not most of them
- MostSensorsDrift             → a clear majority of that domain's sensors are abnormal
- UniformGroupDrift            → basically all / almost all sensors in that domain move together

You MAY use a light wording variant (e.g. "SingleSensorIssue" vs "SingleSensorDrift") if it still clearly communicates group size.
You MUST NOT name a category using adjectives about speed, intensity, or shape such as:
"sudden", "gradual", "sharp spike", "slow drift", "mild", "severe", "violent", "abrupt", "spike", "ramp".
Category names are about GROUP SIZE, not time profile.

STRICT OUTPUT FORMAT:
(List name should be in the format of angle brackets)
Explanation:
<detailed reasoning, may span multiple lines>
Determination:
List 1: <NAME_FOR_LIST_1>
List 2: <NAME_FOR_LIST_2>



Here are some examples (sensor IDs used for illustration: Temp1–Temp3, Curr1–Curr4, Volt1–Volt2):

Example 1:
Parent Category: UniformGroupSpike
List 1: [
  "All Temp1, Temp2, and Temp3 have high contributions (~0.8–1.0) simultaneously.",
  "Temp1–Temp3 readings all jump up at once."
]
List 2: [
  "Every Temp1–Temp3 contribution jumps from ~0.1 to ~0.9 in the same measurement cycle."
]
Explanation: All contribution temperature sensors (Temp1–Temp3) listed in List 1 exhibit a simultaneous surge; it is like a sudden and simultaneous spike. List 2 has a similar phenomenon with certain numeric levels: contributions surge by around 0.1 to around 0.9 within a cycle. Both are from temperature range, sweep through all sets of sensors, show synchronous timing, and show sudden velocity and shape with large amplitude. The only differences are through terminology and small number range, and hence do not show a different intrinsic mechanism nor structural pattern. I thus cluster them similarly and add List 2 as another example to cover all bases.

Determination:
List 1: <UniformGroupSpike>
List 2: <UniformGroupSpike>

Example 2:
Parent Category: SingleSensorDrift
List 1: [
  "Only Temp1 shows a sudden rise in contribution (0.9) while Temp2 and Temp3 stay low.",
  "One temperature sensor (e.g., Temp2) deviates sharply—investigate isolated drift."
]
List 2: [
  "Temp3 gradually trends upward over time—slow drift."
]
Explanation: In List 1, there is a single temperature sensor (such as Temp1) with a sudden jump to a high value (approximately 0.9), while all other sensors are constant at a normal level; this is an unusual and abrupt change. In List 2, only a temperature sensor exhibits a change with a slow increase over time; this is a slow drift pattern. Both lists are regarding the same thing (temperature) and have the same list length (one sensor). The only thing different is by how fast and by drift type (abrupt versus slow). At present, I interpret this difference as a change by itself because there is only one root cause and thus it is with regard to single-sensor drift and with a similar response. So, I choose to leave them as a group and append List 2 to enhance coverage.

Determination:
List 1: <SingleSensorDrift>
List 2: <SingleSensorDrift>

Example 3:
Parent Category: SingleSensorDrift
List 1: [
  "Only Curr3 jumps in contribution (0.95) while Curr1, Curr2, and Curr4 remain near zero.",
  "One current sensor (e.g., Curr3) stands out with a sudden spike in contribution."
]
List 2: [
  "Only Curr1 slowly increases its contribution over multiple readings."
]
Explanation: List 1 shows one current sensor (Curr3) quickly jumping to a very high value (~0.95), while the other current sensors stay close to zero. This is a sudden change with a big amount that happens in a short time (spike). List 2 also looks at one current sensor (Curr1), but its value goes up slowly over several readings; this is a slow and steady trend (slow drift). They are both in the same area (current) and have the same size (single sensor), but the speed and shape are clearly different: sudden spike vs slow drift. This difference is stable and separate, and it affects detection threshold, alert policy, and possible root cause. So, I divided them into two subtypes to keep the pattern meaning clear.

Determination:
List 1: <SuddenCurrDrift>
List 2: <SlowCurrDrift>

Example 4:
Parent Category: SingleSensorDrift
List 1: [
  "Volt1 jumps abruptly to a high contribution while Volt2 remains low."
]
List 2: [
  "Volt2 slowly increases its contribution over time while Volt1 stays near baseline."
]
Explanation:  List 1 shows one voltage sensor (Volt1) quickly jumping to a high contribution, while the other sensor stays close to normal; this looks like a sudden spike from one sensor. List 2 also looks at one voltage sensor (Volt2), but its contribution goes up slowly over many readings; this is a slow and steady increase. They are in the same area (voltage) and have the same group size (one sensor), but their behavior over time is very different (sudden vs slow). This will affect how we set detection limits, alerts, and plans for fixing issues. So, I divided them into two subtypes to keep things clear for future action.

Determination:
List 1: <SuddenVoltDrift>
List 2: <SlowVoltDrift>
"""

ROUTE_SELECTION_FEW_SHOT = """
You are given an error tree (JSON-like dict) and ONE incoming anomaly template.
Choose the SINGLE BEST path in the current tree to attach this template next.

Rules for Routing:
If TEMPLATE literally says "cross domain", "cross-domain", "cross domain balance",
      "multi-domain balance", or clearly compares two domains at similar strength:
        → route to cross-domain, e.g. (CrossDomain)
Otherwise:
        → pick the SINGLE MOST RELEVANT DOMAIN (e.g. Voltage-related, Curr-related, etc.)
        → You will know what Domain it's related from the template text.
Core behavior
- You may return a path to ANY EXISTING node, at ANY DEPTH (leaf or internal) or return ONE new TOP-LEVEL category ONLY if none exist.
- If NO suitable existing node can be found anywhere in the tree, return ONE new TOP-LEVEL category ONLY
  (e.g., Temp-related, Curr-related, Volt-related, Cross-domain). Do NOT invent deeper levels in this case.
- Do NOT create per-sensor nodes. Pattern leaves only.
- Sensor IDs and domain labels in examples are illustrative; domains may differ in reality.
- After you choose the Route, emit a "Found" line indicating whether EVERY segment in Route already EXISTS in the provided Error Tree.
  • Use exactly: Found: YES  (when all segments exist in the tree)
  • Use exactly: Found: NO   (when at least one segment is missing and you proposed a new top-level)
- Based on your explanation, give the correct route



Provide a detailed Explanation
- Explain why you choose this route.
- For very deep paths, you may compress middle segments in the Explanation with “…”, but keep full segments in the Route line.
STRICT OUTPUT FORMAT (exactly two lines; nothing else):
Explanation: <show the reason in detail>
Route: (<SEG1> -> <SEG2> -> ... )      # segments must all EXIST in the tree, OR be exactly ONE new top-level category
Found: YES | NO



Examples:

1) Empty tree → propose one new top-level anchor
Error Tree:
{}
Template:
"Temp1 jumps sharply while Temp2 and Temp3 stay near baseline."
Explanation: The template talks about temperature sensors that suddenly change when the tree is empty. There are no options to compare, so we need a domain anchor first. Therefore, we should create a top-level Temp-related.
Route: (Temp-related)
Found: NO

2) Parent is a LEAF (no children) → route to that leaf (a later step may split)
Error Tree:
{"Temp-related":"<END>"}
Template:
"Temp1, Temp2, and Temp3 all spike together."
Explanation: Because all temperature sensors spike together, the domain matches Temp-related; since the only available node is a leaf with no children, we attach here now and refine the subtype later.
Route: (Temp-related)
Found: Yes

3) Parent has MULTIPLE children → choose deepest matching child
Error Tree:
{"Temp-related":{"SingleSensorDrift":"<END>", "UniformGroupSpike":"<END>"}}
Template:
"Only one Temp sensor slowly increases over time."
Explanation: Because there is only one temperature sensor that goes up slowly (single, slow, steady), for temperature-related issues the choices are {SingleSensorDrift, UniformGroupSpike}; UniformGroupSpike affects the whole group, so it does not work; we want the best matching option, so we choose temperature-related -> SingleSensorDrift.
Route: (Temp-related -> SingleSensorDrift)
Found: Yes

4) Parent has MULTIPLE children but none match → route to the internal parent
Error Tree:
{"Temp-related":{"SingleSensorDrift":"<END>", "UniformGroupSpike":"<END>"}}
Template:
"Temp1 and Temp2 gradually rise while Temp3 stays low."
Explanation: Two temperatures rise simultaneously while one remains low (slow, partial group). The possibilities {SingleSensorDrift, UniformGroupSpike} do not contain partial-group behavior. When none of the kids fit, we send it to the internal parent, so we attach it at the Temp-related.
Route: (Temp-related)
Found: Yes

5) Deeper path exists → pick the deepest existing node
Error Tree:
{"Temp-related":{"SingleSensorDrift":{"SlowDrift":"<END>"}, "UniformGroupSpike":"<END>"}}
Template:
"One Temp sensor trends up slowly across many intervals."
Explanation: A single temperature sensor goes up slowly over many periods (single, slow, long time). Under SingleSensorDrift, the choices include SlowDrift, which fits while others do not. We like the deepest matching leaf, so we choose Temp-related -> SingleSensorDrift -> SlowDrift.
Route: (Temp-related -> SingleSensorDrift -> SlowDrift)
Found: Yes

6) New domain (none exists yet)
Error Tree:
{"Temp-related":{"UniformGroupSpike":"<END>"}, "Curr-related":{"UniformGroupSpike":"<END>"}}
Template:
"Volt1 and Volt2 jump together abruptly."
Route: (Volt-related)
Explanation:  Because the template is regarding voltage sensors with the synchronuous sudden jump (Volt1–Volt2), there is no Volt-based node it can be accommodated in; rule dictates create new top-level for missing domain, so choose Volt-related.
7) Cross Domain
Error Tree:
{"Cross-domain":"<END>", "Curr-related":{"UniformGroupSpike":"<END>"}}
Template: "Discharge pressure and Suction Pressure are elevated (~0.46, ~0.38) while other Pressure sensors remain low"
Explanation: This template shows part of sensors of pressure drift up, and other remain low. So it is belong to Pressure Related.
Route:(Pressure-related)
Found: No
"""