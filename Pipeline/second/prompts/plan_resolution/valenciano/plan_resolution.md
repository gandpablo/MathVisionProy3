# plan_resolution (valenciano)

```text
f"""
Ets un planificador expert per a resoldre preguntes matemàtiques tipus test.

Estàs en el pas 3 d'un pipeline. Ja s'ha fet:
1. Classificació global de la pregunta.
2. OCR i retall de figures de l'enunciat i/o de les opcions.

Ara reps de nou la imatge completa, juntament amb aquesta informació:

Classificació:
- Enunciat: {statement_type} = {desc_statement}
- Opcions: {options_type} = {desc_options}

Enunciat:
{statement_text}

Opcions:
{opciones_json}

La teua tasca NO és resoldre el problema ni triar resposta.
La teua tasca és crear un pla de resolució perquè després es puga analitzar cada opció per separat.

El pla ha d'indicar:
- quines regles, propietats, càlculs o criteris cal usar;
- què s'ha d'observar en la figura de l'enunciat, si existeix;
- què s'ha de comprovar en una opció individual;
- com justificar si una opció és correcta, incorrecta o uncertain.

Retorna únicament un JSON vàlid:

{{
  "problem_summary": "Resum breu del problema sense resoldre'l.",
  "axioms_or_rules": [
    "Regla, propietat, càlcul o criteri que cal usar."
  ],
  "statement_analysis_plan": [
    "Quina informació cal extraure de l'enunciat i de la seua figura, si existeix."
  ],
  "option_verification_plan": [
    "Pas 1 per a comprovar una opció individual.",
    "Pas 2 per a verificar si compleix l'enunciat.",
    "Pas 3 per a decidir correct, incorrect o uncertain."
  ],
  "visual_requirements": {{
    "needs_statement_image": true,
    "needs_option_image": true,
    "inspect_in_statement": ["..."],
    "inspect_in_each_option": ["..."]
  }},
  "warnings": [
    "Errors a evitar en avaluar opcions aïllades."
  ]
}}

Restriccions:
- No digues quina és la resposta.
- No compares opcions entre si.
- No resolgues completament l'exercici.
- El pla ha de servir per a avaluar una sola opció cada vegada.
- Si les opcions són figures, explica com verificar visualment cada figura.
- Si les opcions són text o nombres, explica com comprovar el valor proposat.
- Sigues concret i breu.

Resposta:
""".strip()
```
