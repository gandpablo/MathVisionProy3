# final_decision (ingles)

```text
f"""
You are an expert at solving multiple-choice math questions.

Each option has already been evaluated separately with a visual model.
Now you must make a final decision using the individual reasonings.

Classification:
- Statement: {statement_type} = {desc_statement}
- Options: {options_type} = {desc_options}

Statement:
{statement_text}

Options:
{opciones}

Individual reasoning by option:
{razonamientos_json}

Your task:
- Analyze the reasoning for all options step by step.
- Decide which of the five options A, B, C, D, or E is the correct answer.
- Give a general reasoning that justifies why that option is correct.
- Also use the individual reasonings to rule out the other options.
- If there are contradictions between reasonings, prioritize the reasoning most consistent with the statement.
- If an option appears as uncertain, do not discard it automatically: assess whether it may still be the best choice.
- Do not invent visual information that does not appear in the reasonings.
- You must choose exactly one option among A, B, C, D, and E.

Return only a valid JSON object with this structure:

{{
  "answer": "A|B|C|D|E",
  "reasoning": "General step-by-step reasoning, explaining why the chosen option is correct and why the others are not."
}}

Answer:
""".strip()
```
