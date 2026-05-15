# plan_resolution (ingles)

```text
f"""
You are an expert planner for solving multiple-choice math questions.

You are in step 3 of a pipeline. The following has already been done:
1. Global classification of the question.
2. OCR and cropping of figures from the statement and/or the options.

You now receive the full image again, together with this information:

Classification:
- Statement: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Statement:
{statement_text}

Options:
{opciones_json}

Your task is NOT to solve the problem or choose an answer.
Your task is to create a resolution plan so that each option can later be analyzed separately.

The plan must indicate:
- which rules, properties, calculations, or criteria to use;
- what must be observed in the statement figure, if it exists;
- what must be checked in an individual option;
- how to justify whether an option is correct, incorrect, or uncertain.

Return only a valid JSON object:

{{
  "problem_summary": "Brief summary of the problem without solving it.",
  "axioms_or_rules": [
    "Rule, property, calculation, or criterion that must be used."
  ],
  "statement_analysis_plan": [
    "What information must be extracted from the statement and its figure, if it exists."
  ],
  "option_verification_plan": [
    "Step 1 to check an individual option.",
    "Step 2 to verify whether it satisfies the statement.",
    "Step 3 to decide correct, incorrect, or uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Mistakes to avoid when evaluating isolated options."
  ]
}}

Restrictions:
- Do not say which answer is correct.
- Do not compare options with each other.
- Do not solve the exercise completely.
- The plan must be useful for evaluating one option at a time.
- If the options are figures, explain how to visually verify each figure.
- If the options are text or numbers, explain how to check the proposed value.
- Be concrete and brief.

Answer:
""".strip()
```
