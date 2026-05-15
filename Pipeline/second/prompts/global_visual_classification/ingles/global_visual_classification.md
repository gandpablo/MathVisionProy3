# global_visual_classification (ingles)

```text
Analyze the image of this multiple-choice question.

Do not solve the problem or state the correct answer.

Return only a valid JSON object with this information:

{
  "statement_type": "A.1" or "A.2",
  "options_type": "B.1" or "B.2",
  "statement_text": "...",
  "options_text": {
    "A": "... or null",
    "B": "... or null",
    "C": "... or null",
    "D": "... or null",
    "E": "... or null"
  },
}

Criteria:

statement_text: The text of the statement, or null if the statement is only an image.
options_text: A dictionary with the text of each option, or null if the options are only images.

- A.1: the statement is text only.
- A.2: the statement has a relevant figure.
- B.1: the options (A,B,C,D,E) are text, numbers, or expressions, not figures.
- B.2: the possible options (A, B, C, D, E) are not text or numeric; they are figures.
- If the options are B.2, set every option to null.
- Ignore remains of other questions.
- If you see content in the options_text dictionary and you had selected B.2, then it is B.1.
```
