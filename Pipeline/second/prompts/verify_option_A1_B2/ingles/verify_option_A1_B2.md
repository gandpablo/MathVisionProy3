# verify_option_A1_B2 (ingles)

```text
f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement is text only.
- The options are figures.
- You will receive one image: normally the figure of option {letra_opcion}; if the crop failed, you will receive the full question image.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- The received image corresponds to this option, or if it is the full image, you must locate option {letra_opcion}.

Your task:
Determine whether the figure in this option satisfies the statement.

Instructions:
- Use the statement, the option image, and the plan.
- If you receive the full image, analyze only option {letra_opcion}.
- Reason step by step.
- Evaluate only this option.
- Do not compare with other options.
- Do not choose a global final answer.
- Visually check the necessary shape, quantities, orientation, positions, symmetries, measurements, or relationships.
- If the crop or full image does not allow a decision, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "visual_observations": [
    "Brief and relevant observation extracted from the option figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()
```
