# verify_option_A2_B1 (ingles)

```text
f"""
You are an expert at solving multiple-choice math questions.

You are evaluating ONE option only.
- The statement has a relevant figure.
- The options are text, a number, or an expression.
- You will receive one image: normally the statement figure; if the crop failed, you will receive the full question image.
- The current option is textual.

Statement:
{statement_text}

Resolution plan:
{plan}

Option to evaluate:
- Letter: {letra_opcion}
- Value: {option_text}

Your task:
Determine whether this individual option can be the correct answer.

Instructions:
- Use the statement, the statement figure, and the plan.
- If you receive the full image, visually locate the relevant statement figure and do not rely on other options.
- Reason step by step.
- Explicitly check the value proposed by the option.
- Do not compare with other options.
- Do not choose a global final answer.
- If the figure does not allow a safe check, mark uncertain.
- Clearly justify which observations lead you to that conclusion.

Return only a valid JSON object:

{{
  "option": "{letra_opcion}",
  "option_value": {json.dumps(option_text, ensure_ascii=False)},
  "status": "correct|incorrect|uncertain",
  "reasoning": "Brief but sufficient reasoning.",
  "visual_observations": [
    "Brief and relevant observation extracted from the statement figure."
  ],
  "checks": [
    "Criterion checked for this option."
  ]
}}

Answer:
""".strip()
```
