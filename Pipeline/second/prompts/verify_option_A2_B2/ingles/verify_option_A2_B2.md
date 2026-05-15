# verify_option_A2_B2 (ingles)

```text
f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement has a relevant figure.
- The options are figures.
- You will receive two images:
  1. Normally the statement figure; if that crop failed, the full image.
  2. Normally the figure of option {letra_opcion}; if that crop failed, the full image.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- The second image corresponds to this option, or if it is the full image, you must locate option {letra_opcion}.

Your task:
Determine whether the figure in this option is compatible with the statement figure and with what is being asked.

Instructions:
- Use the statement text, the statement figure, the option figure, and the plan.
- If any image is the full image, locate only the area needed for this analysis.
- Reason step by step.
- Evaluate only this option.
- Do not compare with other options.
- Do not choose a global final answer.
- Visually check relationships between both figures: shape, orientation, perspective, correspondences, positions, quantities, areas, symmetries, or transformations.
- If any image does not allow a decision, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "statement_visual_observations": [
    "Brief and relevant observation from the statement figure."
  ],
  "option_visual_observations": [
    "Brief and relevant observation from the option figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()
```
