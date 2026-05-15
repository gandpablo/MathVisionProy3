# direct_text_resolution (ingles)

```text
f"""
You are an expert at solving multiple-choice math questions.
Solve the problem using only the statement and the options.

Statement:
{statement_text}

Options:
{opciones_json}

Instructions:
- Reason step by step.
- Use clear calculations and check the conditions in the statement.
- Evaluate all options A-E.
- Do not invent information that is not in the statement.
- If there is ambiguity or missing information, state it.

Return only a valid JSON object with this structure:

{{
  "reasoning": "Step-by-step reasoning for the solution.",
  "options_analysis": {{
    "A": "Why this option is correct or incorrect.",
    "B": "Why this option is correct or incorrect.",
    "C": "Why this option is correct or incorrect.",
    "D": "Why this option is correct or incorrect.",
    "E": "Why this option is correct or incorrect."
  }},
  "final_answer": "A/B/C/D/E"
}}

Answer:
""".strip()
```
