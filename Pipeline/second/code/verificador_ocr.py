import ast
import base64
import json
import re
from io import BytesIO

from idiomas import normalizar_idioma
from pipeline_funcion import OPCIONES, VISION_MODEL, llamar_modelo_visual


def imagen_pil_a_base64(imagen_pil):
    if imagen_pil is None:
        return None

    buffer = BytesIO()
    imagen_pil.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def crear_prompts_verificador_recortes_traducidos(colores_bboxes, idioma):
    if idioma == "valenciano":
        return {
            "A1_B1": f"""
Mira la imatge amb bboxes.

La teua tasca NO és resoldre l'exercici.
La teua tasca NOMÉS és verificar si hi ha retalls de figures clarament mal fets.

En aquest cas:
- L'enunciat és només text.
- Les opcions A-E són text, nombres o expressions.
- NO hi ha figures que calga verificar.
- No has de marcar cap retall com a dolent.

Colors:
{colores_bboxes}

Restricció:
- No pots retornar "enunciado".
- No pots retornar "A", "B", "C", "D" ni "E".
- No inventes etiquetes.
- No expliques res.
- Retorna sempre la llista buida.

Resposta obligatòria, només JSON:
{{"bad_crops": []}}
""",
            "A1_B2": f"""
Mira la imatge amb bboxes.

La teua tasca NO és resoldre l'exercici.
La teua tasca NO és decidir quina opció és correcta.
La teua tasca NOMÉS és verificar si algun retall d'opció està clarament mal fet.

En aquest cas:
- L'enunciat és només text.
- Les opcions A-E són figures.
- Avalua NOMÉS aquests retalls: ["A", "B", "C", "D", "E"].
- No retornes mai "enunciado".

Colors:
{colores_bboxes}

Criteri general:
- Sigues conservador amb els falsos positius.
- No marques retalls per imperfeccions menudes.
- Marca una opció només si l'error és clar i afecta la utilitat del crop.
- Si la figura correcta apareix dins del bbox i és usable, NO la marques.
- Si tens dubtes raonables, NO la marques.
- Però si el retall està clarament malament, sí que has de marcar-lo.

Un retall d'opció està malament si:
- no conté la figura corresponent a aquesta opció,
- conté només text o només l'etiqueta A), B), C), D) o E), sense la figura,
- està clarament en una zona equivocada,
- conté clarament la figura d'una altra opció,
- talla una part important de la figura,
- mescla diverses opcions de manera que confon el retall,
- no permet identificar bé la figura d'aquesta opció,
- o no seria útil per a raonar sobre aquesta figura.

NO marques una opció com a dolenta si:
- conté la figura correcta d'aquesta opció,
- conté la figura correcta amb marge o espai en blanc,
- conté la figura correcta encara que estiga descentrada,
- conté la figura correcta encara que el bbox siga més gran del necessari,
- conté la figura correcta juntament amb l'etiqueta A), B), C), D) o E),
- conté la figura correcta juntament amb una mica de text proper,
- talla una part menuda però la figura continua sent reconeixible,
- inclou nombres, lletres, mesures, símbols o etiquetes internes de la figura,
- el retall és imperfecte però continua sent útil,
- no estàs segur que estiga malament.

Regles importants:
- No marques una opció només perquè el bbox no siga perfecte.
- No marques una opció només perquè tinga molt espai en blanc.
- No marques una opció només perquè incloga la seua lletra d'opció.
- No marques una opció només perquè la figura estiga una mica desplaçada.
- No marques una opció si el crop permetria entendre la figura.
- Sí marca una opció si el crop realment falla i no serviria per a usar aquesta opció.

Abans de respondre, revisa cada element que vulgues marcar:
- L'error és clar?
- El crop deixa de ser útil?
- La figura correcta està absent, molt tallada o confosa amb una altra?
- Estic evitant marcar-lo només per una imperfecció menor?

Si dubtes, elimina aquest element de bad_crops.

Restricció:
- Només pots retornar: "A", "B", "C", "D", "E".
- No inventes etiquetes.
- No expliques res.
- No afiges text fora del JSON.
- L'eixida pot ser [], però no ha de ser sempre [] si hi ha errors evidents.

Resposta obligatòria, només JSON:
{{"bad_crops": []}}
""",
            "A2_B1": f"""
Mira la imatge amb bboxes.

La teua tasca NO és resoldre l'exercici.
La teua tasca NOMÉS és verificar si el retall de la figura de l'enunciat està clarament mal fet.

En aquest cas:
- L'enunciat té una figura rellevant.
- Les opcions són text, nombres o expressions.
- Avalua NOMÉS aquest retall: ["enunciado"].
- No retornes mai "A", "B", "C", "D" ni "E".

Colors:
{colores_bboxes}

Criteri general:
- Sigues conservador amb els falsos positius.
- No marques "enunciado" per imperfeccions menudes.
- Marca "enunciado" només si l'error és clar i afecta la utilitat del crop.
- Si la figura rellevant apareix dins del bbox i és usable, NO la marques.
- Si tens dubtes raonables, NO la marques.
- Però si el retall està clarament malament, sí que has de marcar-lo.

El retall de l'enunciat està malament si:
- no conté la figura rellevant de l'enunciat,
- conté només text llarg de l'enunciat i no conté la figura,
- està clarament en una zona equivocada,
- conté clarament una figura de les opcions en lloc de la figura de l'enunciat,
- talla una part important de la figura,
- no permet identificar bé la figura de l'enunciat,
- o no seria útil per a raonar sobre la figura de l'enunciat.

NO marques "enunciado" com a dolent si:
- conté la figura rellevant de l'enunciat,
- conté la figura rellevant amb marge o espai en blanc,
- conté la figura rellevant encara que estiga descentrada,
- conté la figura rellevant encara que el bbox siga més gran del necessari,
- conté la figura rellevant juntament amb una mica de text proper,
- talla una part menuda però la figura continua sent reconeixible,
- inclou nombres, lletres, mesures, símbols o etiquetes internes de la figura,
- el retall és imperfecte però continua sent útil,
- no estàs segur que estiga malament.

Regles importants:
- No marques "enunciado" només perquè el bbox no siga perfecte.
- No marques "enunciado" només perquè tinga molt espai en blanc.
- No marques "enunciado" només perquè incloga text proper.
- No marques "enunciado" si el crop permetria entendre la figura.
- Sí marca "enunciado" si el crop realment falla i no serviria per a usar la figura.

Abans de respondre, revisa si vols marcar "enunciado":
- L'error és clar?
- El crop deixa de ser útil?
- La figura rellevant està absent, molt tallada o substituïda per una altra?
- Estic evitant marcar-lo només per una imperfecció menor?

Si dubtes, retorna [].

Restricció:
- Només pots retornar: "enunciado".
- No inventes etiquetes.
- No expliques res.
- No afiges text fora del JSON.
- L'eixida pot ser [], però no ha de ser sempre [] si l'error és evident.

Resposta obligatòria, només JSON:
{{"bad_crops": []}}
""",
            "A2_B2": f"""
Mira la imatge amb bboxes.

La teua tasca NO és resoldre l'exercici.
La teua tasca NO és decidir quina opció és correcta.
La teua tasca NOMÉS és verificar si algun retall de figura està clarament mal fet.

En aquest cas:
- L'enunciat té una figura rellevant.
- Les opcions A-E són figures.
- Avalua NOMÉS aquests retalls: ["enunciado", "A", "B", "C", "D", "E"].

Colors:
{colores_bboxes}

Criteri general:
- Sigues conservador amb els falsos positius.
- No marques retalls per imperfeccions menudes.
- Marca un retall només si l'error és clar i afecta la utilitat del crop.
- Si la figura correcta apareix dins del bbox i és usable, NO la marques.
- Si tens dubtes raonables, NO la marques.
- Però si el retall està clarament malament, sí que has de marcar-lo.

Un retall està malament si:
- no conté la figura que correspon,
- conté només text o només una etiqueta i no conté la figura,
- està clarament en una zona equivocada,
- conté clarament la figura d'un altre element,
- una opció conté clarament la figura d'una altra opció,
- "enunciado" conté clarament una figura d'opció en lloc de la figura de l'enunciat,
- talla una part important de la figura,
- mescla diverses figures de manera que confon el retall,
- no permet identificar bé la figura corresponent,
- o no seria útil per a raonar sobre aquesta figura.

NO marques un retall com a dolent si:
- conté la figura correcta,
- conté la figura correcta amb marge o espai en blanc,
- conté la figura correcta encara que estiga descentrada,
- conté la figura correcta encara que el bbox siga més gran del necessari,
- conté la figura correcta juntament amb la seua etiqueta,
- conté la figura correcta juntament amb una mica de text proper,
- talla una part menuda però la figura continua sent reconeixible,
- inclou nombres, lletres, mesures, símbols o etiquetes internes de la figura,
- el retall és imperfecte però continua sent útil,
- no estàs segur que estiga malament.

Regles específiques:
- Per a "enunciado", verifica només si apareix la figura rellevant de l'enunciat.
- Per a "A", "B", "C", "D" i "E", verifica només si apareix la figura d'aquesta opció.
- No avalues si l'opció és matemàticament correcta.
- No marques una opció perquè la seua figura siga pareguda a una altra.
- No marques un retall només perquè el bbox no siga perfecte.
- No marques un retall només perquè tinga molt espai en blanc.
- No marques un retall només perquè incloga text proper o etiqueta.
- No marques un retall si el crop permetria entendre la figura.
- Sí marca un retall si realment falla i no serviria per a usar aquesta figura.

Abans de respondre, revisa cada element que vulgues marcar:
- L'error és clar?
- El crop deixa de ser útil?
- La figura correcta està absent, molt tallada o confosa amb una altra?
- Estic evitant marcar-lo només per una imperfecció menor?

Si dubtes, elimina aquest element de bad_crops.

Restricció:
- Només pots retornar: "enunciado", "A", "B", "C", "D", "E".
- No inventes etiquetes.
- No expliques res.
- No afiges text fora del JSON.
- L'eixida pot ser [], però no ha de ser sempre [] si hi ha errors evidents.

Resposta obligatòria, només JSON:
{{"bad_crops": []}}
""",
        }

    if idioma == "ingles":
        return {
            "A1_B1": f"""
Look at the image with bboxes.

Your task is NOT to solve the exercise.
Your task is ONLY to verify whether there are clearly bad figure crops.

In this case:
- The statement is text only.
- Options A-E are text, numbers, or expressions.
- There are NO figures to verify.
- You must not mark any crop as bad.

Colors:
{colores_bboxes}

Restriction:
- You cannot return "enunciado".
- You cannot return "A", "B", "C", "D", or "E".
- Do not invent labels.
- Do not explain anything.
- Always return the empty list.

Required answer, JSON only:
{{"bad_crops": []}}
""",
            "A1_B2": f"""
Look at the image with bboxes.

Your task is NOT to solve the exercise.
Your task is NOT to decide which option is correct.
Your task is ONLY to verify whether any option crop is clearly wrong.

In this case:
- The statement is text only.
- Options A-E are figures.
- Evaluate ONLY these crops: ["A", "B", "C", "D", "E"].
- Never return "enunciado".

Colors:
{colores_bboxes}

General criterion:
- Be conservative with false positives.
- Do not mark crops for small imperfections.
- Mark an option only if the error is clear and affects the usefulness of the crop.
- If the correct figure appears inside the bbox and is usable, do NOT mark it.
- If you have reasonable doubts, do NOT mark it.
- But if the crop is clearly wrong, you must mark it.

An option crop is wrong if:
- it does not contain the figure corresponding to that option,
- it contains only text or only the label A), B), C), D), or E), without the figure,
- it is clearly in the wrong area,
- it clearly contains the figure from another option,
- it cuts off an important part of the figure,
- it mixes several options in a way that confuses the crop,
- it does not allow the figure for that option to be identified well,
- or it would not be useful for reasoning about that figure.

Do NOT mark an option as bad if:
- it contains the correct figure for that option,
- it contains the correct figure with margin or white space,
- it contains the correct figure even if it is off-center,
- it contains the correct figure even if the bbox is larger than necessary,
- it contains the correct figure together with the label A), B), C), D), or E),
- it contains the correct figure together with some nearby text,
- it cuts a small part but the figure is still recognizable,
- it includes numbers, letters, measurements, symbols, or internal labels of the figure,
- the crop is imperfect but still useful,
- you are not sure that it is wrong.

Important rules:
- Do not mark an option just because the bbox is not perfect.
- Do not mark an option just because it has a lot of white space.
- Do not mark an option just because it includes its option letter.
- Do not mark an option just because the figure is slightly shifted.
- Do not mark an option if the crop would allow understanding the figure.
- Do mark an option if the crop truly fails and would not be useful for using that option.

Before answering, review each item you want to mark:
- Is the error clear?
- Does the crop stop being useful?
- Is the correct figure absent, badly cut, or confused with another one?
- Am I avoiding marking it only for a minor imperfection?

If in doubt, remove that item from bad_crops.

Restriction:
- You may return only: "A", "B", "C", "D", "E".
- Do not invent labels.
- Do not explain anything.
- Do not add text outside the JSON.
- The output may be [], but it must not always be [] if there are obvious errors.

Required answer, JSON only:
{{"bad_crops": []}}
""",
            "A2_B1": f"""
Look at the image with bboxes.

Your task is NOT to solve the exercise.
Your task is ONLY to verify whether the crop of the statement figure is clearly wrong.

In this case:
- The statement has a relevant figure.
- The options are text, numbers, or expressions.
- Evaluate ONLY this crop: ["enunciado"].
- Never return "A", "B", "C", "D", or "E".

Colors:
{colores_bboxes}

General criterion:
- Be conservative with false positives.
- Do not mark "enunciado" for small imperfections.
- Mark "enunciado" only if the error is clear and affects the usefulness of the crop.
- If the relevant figure appears inside the bbox and is usable, do NOT mark it.
- If you have reasonable doubts, do NOT mark it.
- But if the crop is clearly wrong, you must mark it.

The statement crop is wrong if:
- it does not contain the relevant statement figure,
- it contains only long statement text and no figure,
- it is clearly in the wrong area,
- it clearly contains a figure from the options instead of the statement figure,
- it cuts off an important part of the figure,
- it does not allow the statement figure to be identified well,
- or it would not be useful for reasoning about the statement figure.

Do NOT mark "enunciado" as bad if:
- it contains the relevant statement figure,
- it contains the relevant figure with margin or white space,
- it contains the relevant figure even if it is off-center,
- it contains the relevant figure even if the bbox is larger than necessary,
- it contains the relevant figure together with some nearby text,
- it cuts a small part but the figure is still recognizable,
- it includes numbers, letters, measurements, symbols, or internal labels of the figure,
- the crop is imperfect but still useful,
- you are not sure that it is wrong.

Important rules:
- Do not mark "enunciado" just because the bbox is not perfect.
- Do not mark "enunciado" just because it has a lot of white space.
- Do not mark "enunciado" just because it includes nearby text.
- Do not mark "enunciado" if the crop would allow understanding the figure.
- Do mark "enunciado" if the crop truly fails and would not be useful for using the figure.

Before answering, review whether you want to mark "enunciado":
- Is the error clear?
- Does the crop stop being useful?
- Is the relevant figure absent, badly cut, or replaced by another one?
- Am I avoiding marking it only for a minor imperfection?

If in doubt, return [].

Restriction:
- You may return only: "enunciado".
- Do not invent labels.
- Do not explain anything.
- Do not add text outside the JSON.
- The output may be [], but it must not always be [] if the error is obvious.

Required answer, JSON only:
{{"bad_crops": []}}
""",
            "A2_B2": f"""
Look at the image with bboxes.

Your task is NOT to solve the exercise.
Your task is NOT to decide which option is correct.
Your task is ONLY to verify whether any figure crop is clearly wrong.

In this case:
- The statement has a relevant figure.
- Options A-E are figures.
- Evaluate ONLY these crops: ["enunciado", "A", "B", "C", "D", "E"].

Colors:
{colores_bboxes}

General criterion:
- Be conservative with false positives.
- Do not mark crops for small imperfections.
- Mark a crop only if the error is clear and affects the usefulness of the crop.
- If the correct figure appears inside the bbox and is usable, do NOT mark it.
- If you have reasonable doubts, do NOT mark it.
- But if the crop is clearly wrong, you must mark it.

A crop is wrong if:
- it does not contain the corresponding figure,
- it contains only text or only a label and no figure,
- it is clearly in the wrong area,
- it clearly contains the figure of another element,
- an option clearly contains the figure of another option,
- "enunciado" clearly contains an option figure instead of the statement figure,
- it cuts off an important part of the figure,
- it mixes several figures in a way that confuses the crop,
- it does not allow the corresponding figure to be identified well,
- or it would not be useful for reasoning about that figure.

Do NOT mark a crop as bad if:
- it contains the correct figure,
- it contains the correct figure with margin or white space,
- it contains the correct figure even if it is off-center,
- it contains the correct figure even if the bbox is larger than necessary,
- it contains the correct figure together with its label,
- it contains the correct figure together with some nearby text,
- it cuts a small part but the figure is still recognizable,
- it includes numbers, letters, measurements, symbols, or internal labels of the figure,
- the crop is imperfect but still useful,
- you are not sure that it is wrong.

Specific rules:
- For "enunciado", verify only whether the relevant statement figure appears.
- For "A", "B", "C", "D", and "E", verify only whether the figure for that option appears.
- Do not evaluate whether the option is mathematically correct.
- Do not mark an option because its figure is similar to another.
- Do not mark a crop just because the bbox is not perfect.
- Do not mark a crop just because it has a lot of white space.
- Do not mark a crop just because it includes nearby text or a label.
- Do not mark a crop if it would allow understanding the figure.
- Do mark a crop if it truly fails and would not be useful for using that figure.

Before answering, review each item you want to mark:
- Is the error clear?
- Does the crop stop being useful?
- Is the correct figure absent, badly cut, or confused with another one?
- Am I avoiding marking it only for a minor imperfection?

If in doubt, remove that item from bad_crops.

Restriction:
- You may return only: "enunciado", "A", "B", "C", "D", "E".
- Do not invent labels.
- Do not explain anything.
- Do not add text outside the JSON.
- The output may be [], but it must not always be [] if there are obvious errors.

Required answer, JSON only:
{{"bad_crops": []}}
""",
        }

    if idioma == "frances":
        return {
            "A1_B1": f"""
Regarde l'image avec les bboxes.

Ta tâche N'EST PAS de résoudre l'exercice.
Ta tâche est UNIQUEMENT de vérifier s'il existe des recadrages de figures clairement incorrects.

Dans ce cas:
- L'énoncé est uniquement textuel.
- Les options A-E sont du texte, des nombres ou des expressions.
- Il n'y a AUCUNE figure à vérifier.
- Tu ne dois marquer aucun recadrage comme mauvais.

Couleurs:
{colores_bboxes}

Restriction:
- Tu ne peux pas renvoyer "enunciado".
- Tu ne peux pas renvoyer "A", "B", "C", "D" ni "E".
- N'invente pas d'étiquettes.
- N'explique rien.
- Renvoie toujours la liste vide.

Réponse obligatoire, JSON uniquement:
{{"bad_crops": []}}
""",
            "A1_B2": f"""
Regarde l'image avec les bboxes.

Ta tâche N'EST PAS de résoudre l'exercice.
Ta tâche N'EST PAS de décider quelle option est correcte.
Ta tâche est UNIQUEMENT de vérifier si un recadrage d'option est clairement incorrect.

Dans ce cas:
- L'énoncé est uniquement textuel.
- Les options A-E sont des figures.
- Évalue UNIQUEMENT ces recadrages: ["A", "B", "C", "D", "E"].
- Ne renvoie jamais "enunciado".

Couleurs:
{colores_bboxes}

Critère général:
- Sois conservateur avec les faux positifs.
- Ne marque pas les recadrages pour de petites imperfections.
- Marque une option seulement si l'erreur est claire et affecte l'utilité du crop.
- Si la figure correcte apparaît dans la bbox et est utilisable, NE la marque PAS.
- Si tu as des doutes raisonnables, NE la marque PAS.
- Mais si le recadrage est clairement mauvais, tu dois le marquer.

Un recadrage d'option est mauvais si:
- il ne contient pas la figure correspondant à cette option,
- il contient seulement du texte ou seulement l'étiquette A), B), C), D) ou E), sans la figure,
- il est clairement dans une mauvaise zone,
- il contient clairement la figure d'une autre option,
- il coupe une partie importante de la figure,
- il mélange plusieurs options d'une manière qui rend le recadrage confus,
- il ne permet pas de bien identifier la figure de cette option,
- ou il ne serait pas utile pour raisonner sur cette figure.

NE marque PAS une option comme mauvaise si:
- elle contient la figure correcte de cette option,
- elle contient la figure correcte avec une marge ou de l'espace blanc,
- elle contient la figure correcte même si elle est décentrée,
- elle contient la figure correcte même si la bbox est plus grande que nécessaire,
- elle contient la figure correcte avec l'étiquette A), B), C), D) ou E),
- elle contient la figure correcte avec un peu de texte proche,
- elle coupe une petite partie mais la figure reste reconnaissable,
- elle inclut des nombres, lettres, mesures, symboles ou étiquettes internes de la figure,
- le recadrage est imparfait mais reste utile,
- tu n'es pas sûr qu'il soit mauvais.

Règles importantes:
- Ne marque pas une option seulement parce que la bbox n'est pas parfaite.
- Ne marque pas une option seulement parce qu'elle a beaucoup d'espace blanc.
- Ne marque pas une option seulement parce qu'elle inclut sa lettre d'option.
- Ne marque pas une option seulement parce que la figure est légèrement décalée.
- Ne marque pas une option si le crop permettrait de comprendre la figure.
- Marque une option si le crop échoue réellement et ne servirait pas à utiliser cette option.

Avant de répondre, vérifie chaque élément que tu veux marquer:
- L'erreur est-elle claire?
- Le crop cesse-t-il d'être utile?
- La figure correcte est-elle absente, très coupée ou confondue avec une autre?
- Suis-je en train d'éviter de le marquer seulement pour une imperfection mineure?

En cas de doute, retire cet élément de bad_crops.

Restriction:
- Tu peux renvoyer uniquement: "A", "B", "C", "D", "E".
- N'invente pas d'étiquettes.
- N'explique rien.
- N'ajoute pas de texte hors du JSON.
- La sortie peut être [], mais elle ne doit pas toujours être [] s'il y a des erreurs évidentes.

Réponse obligatoire, JSON uniquement:
{{"bad_crops": []}}
""",
            "A2_B1": f"""
Regarde l'image avec les bboxes.

Ta tâche N'EST PAS de résoudre l'exercice.
Ta tâche est UNIQUEMENT de vérifier si le recadrage de la figure de l'énoncé est clairement incorrect.

Dans ce cas:
- L'énoncé contient une figure pertinente.
- Les options sont du texte, des nombres ou des expressions.
- Évalue UNIQUEMENT ce recadrage: ["enunciado"].
- Ne renvoie jamais "A", "B", "C", "D" ni "E".

Couleurs:
{colores_bboxes}

Critère général:
- Sois conservateur avec les faux positifs.
- Ne marque pas "enunciado" pour de petites imperfections.
- Marque "enunciado" seulement si l'erreur est claire et affecte l'utilité du crop.
- Si la figure pertinente apparaît dans la bbox et est utilisable, NE la marque PAS.
- Si tu as des doutes raisonnables, NE la marque PAS.
- Mais si le recadrage est clairement mauvais, tu dois le marquer.

Le recadrage de l'énoncé est mauvais si:
- il ne contient pas la figure pertinente de l'énoncé,
- il contient seulement un long texte de l'énoncé et aucune figure,
- il est clairement dans une mauvaise zone,
- il contient clairement une figure des options au lieu de la figure de l'énoncé,
- il coupe une partie importante de la figure,
- il ne permet pas de bien identifier la figure de l'énoncé,
- ou il ne serait pas utile pour raisonner sur la figure de l'énoncé.

NE marque PAS "enunciado" comme mauvais si:
- il contient la figure pertinente de l'énoncé,
- il contient la figure pertinente avec une marge ou de l'espace blanc,
- il contient la figure pertinente même si elle est décentrée,
- il contient la figure pertinente même si la bbox est plus grande que nécessaire,
- il contient la figure pertinente avec un peu de texte proche,
- il coupe une petite partie mais la figure reste reconnaissable,
- il inclut des nombres, lettres, mesures, symboles ou étiquettes internes de la figure,
- le recadrage est imparfait mais reste utile,
- tu n'es pas sûr qu'il soit mauvais.

Règles importantes:
- Ne marque pas "enunciado" seulement parce que la bbox n'est pas parfaite.
- Ne marque pas "enunciado" seulement parce qu'il y a beaucoup d'espace blanc.
- Ne marque pas "enunciado" seulement parce qu'il inclut du texte proche.
- Ne marque pas "enunciado" si le crop permettrait de comprendre la figure.
- Marque "enunciado" si le crop échoue réellement et ne servirait pas à utiliser la figure.

Avant de répondre, vérifie si tu veux marquer "enunciado":
- L'erreur est-elle claire?
- Le crop cesse-t-il d'être utile?
- La figure pertinente est-elle absente, très coupée ou remplacée par une autre?
- Suis-je en train d'éviter de le marquer seulement pour une imperfection mineure?

En cas de doute, renvoie [].

Restriction:
- Tu peux renvoyer uniquement: "enunciado".
- N'invente pas d'étiquettes.
- N'explique rien.
- N'ajoute pas de texte hors du JSON.
- La sortie peut être [], mais elle ne doit pas toujours être [] si l'erreur est évidente.

Réponse obligatoire, JSON uniquement:
{{"bad_crops": []}}
""",
            "A2_B2": f"""
Regarde l'image avec les bboxes.

Ta tâche N'EST PAS de résoudre l'exercice.
Ta tâche N'EST PAS de décider quelle option est correcte.
Ta tâche est UNIQUEMENT de vérifier si un recadrage de figure est clairement incorrect.

Dans ce cas:
- L'énoncé contient une figure pertinente.
- Les options A-E sont des figures.
- Évalue UNIQUEMENT ces recadrages: ["enunciado", "A", "B", "C", "D", "E"].

Couleurs:
{colores_bboxes}

Critère général:
- Sois conservateur avec les faux positifs.
- Ne marque pas les recadrages pour de petites imperfections.
- Marque un recadrage seulement si l'erreur est claire et affecte l'utilité du crop.
- Si la figure correcte apparaît dans la bbox et est utilisable, NE le marque PAS.
- Si tu as des doutes raisonnables, NE le marque PAS.
- Mais si le recadrage est clairement mauvais, tu dois le marquer.

Un recadrage est mauvais si:
- il ne contient pas la figure correspondante,
- il contient seulement du texte ou seulement une étiquette et aucune figure,
- il est clairement dans une mauvaise zone,
- il contient clairement la figure d'un autre élément,
- une option contient clairement la figure d'une autre option,
- "enunciado" contient clairement une figure d'option au lieu de la figure de l'énoncé,
- il coupe une partie importante de la figure,
- il mélange plusieurs figures d'une manière qui rend le recadrage confus,
- il ne permet pas de bien identifier la figure correspondante,
- ou il ne serait pas utile pour raisonner sur cette figure.

NE marque PAS un recadrage comme mauvais si:
- il contient la figure correcte,
- il contient la figure correcte avec une marge ou de l'espace blanc,
- il contient la figure correcte même si elle est décentrée,
- il contient la figure correcte même si la bbox est plus grande que nécessaire,
- il contient la figure correcte avec son étiquette,
- il contient la figure correcte avec un peu de texte proche,
- il coupe une petite partie mais la figure reste reconnaissable,
- il inclut des nombres, lettres, mesures, symboles ou étiquettes internes de la figure,
- le recadrage est imparfait mais reste utile,
- tu n'es pas sûr qu'il soit mauvais.

Règles spécifiques:
- Pour "enunciado", vérifie seulement si la figure pertinente de l'énoncé apparaît.
- Pour "A", "B", "C", "D" et "E", vérifie seulement si la figure de cette option apparaît.
- N'évalue pas si l'option est mathématiquement correcte.
- Ne marque pas une option parce que sa figure ressemble à une autre.
- Ne marque pas un recadrage seulement parce que la bbox n'est pas parfaite.
- Ne marque pas un recadrage seulement parce qu'il a beaucoup d'espace blanc.
- Ne marque pas un recadrage seulement parce qu'il inclut du texte proche ou une étiquette.
- Ne marque pas un recadrage si le crop permettrait de comprendre la figure.
- Marque un recadrage s'il échoue réellement et ne servirait pas à utiliser cette figure.

Avant de répondre, vérifie chaque élément que tu veux marquer:
- L'erreur est-elle claire?
- Le crop cesse-t-il d'être utile?
- La figure correcte est-elle absente, très coupée ou confondue avec une autre?
- Suis-je en train d'éviter de le marquer seulement pour une imperfection mineure?

En cas de doute, retire cet élément de bad_crops.

Restriction:
- Tu peux renvoyer uniquement: "enunciado", "A", "B", "C", "D", "E".
- N'invente pas d'étiquettes.
- N'explique rien.
- N'ajoute pas de texte hors du JSON.
- La sortie peut être [], mais elle ne doit pas toujours être [] s'il y a des erreurs évidentes.

Réponse obligatoire, JSON uniquement:
{{"bad_crops": []}}
""",
        }

    return {}


def crear_prompt_verificador_recortes(
    statement_type,
    options_type,
    colores_bboxes,
    idioma="castellano",
):
    caso = f"{statement_type}_{options_type}".replace(".", "")
    idioma = normalizar_idioma(idioma)

    if idioma != "castellano":
        prompts_traducidos = crear_prompts_verificador_recortes_traducidos(
            colores_bboxes,
            idioma,
        )
        if caso in prompts_traducidos:
            return prompts_traducidos[caso].strip()

    prompts = {
        "A1_B1": f"""
Mira la imagen con bboxes.

Tu tarea NO es resolver el ejercicio.
Tu tarea SOLO es verificar si hay recortes de figuras claramente mal hechos.

En este caso:
- El enunciado es solo texto.
- Las opciones A-E son texto, números o expresiones.
- NO hay figuras que verificar.
- No debes marcar ningún recorte como malo.

Colores:
{colores_bboxes}

Restricción:
- No puedes devolver "enunciado".
- No puedes devolver "A", "B", "C", "D" ni "E".
- No inventes etiquetas.
- No expliques nada.
- Devuelve siempre la lista vacía.

Respuesta obligatoria, solo JSON:
{{"bad_crops": []}}
""",

        "A1_B2": f"""
Mira la imagen con bboxes.

Tu tarea NO es resolver el ejercicio.
Tu tarea NO es decidir cuál opción es correcta.
Tu tarea SOLO es verificar si algún recorte de opción está claramente mal hecho.

En este caso:
- El enunciado es solo texto.
- Las opciones A-E son figuras.
- Evalúa SOLO estos recortes: ["A", "B", "C", "D", "E"].
- Nunca devuelvas "enunciado".

Colores:
{colores_bboxes}

Criterio general:
- Sé conservador con los falsos positivos.
- No marques recortes por imperfecciones pequeñas.
- Marca una opción solo si el error es claro y afecta a la utilidad del crop.
- Si la figura correcta aparece dentro del bbox y es usable, NO marques.
- Si tienes dudas razonables, NO marques.
- Pero si el recorte está claramente mal, sí debes marcarlo.

Un recorte de opción está mal si:
- no contiene la figura correspondiente a esa opción,
- contiene solo texto o solo la etiqueta A), B), C), D) o E), sin la figura,
- está claramente en una zona equivocada,
- contiene claramente la figura de otra opción,
- corta una parte importante de la figura,
- mezcla varias opciones de forma que confunde el recorte,
- no permite identificar bien la figura de esa opción,
- o no sería útil para razonar sobre esa figura.

NO marques una opción como mala si:
- contiene la figura correcta de esa opción,
- contiene la figura correcta con margen o espacio blanco,
- contiene la figura correcta aunque esté descentrada,
- contiene la figura correcta aunque el bbox sea más grande de lo necesario,
- contiene la figura correcta junto con la etiqueta A), B), C), D) o E),
- contiene la figura correcta junto con algo de texto cercano,
- corta una parte pequeña pero la figura sigue siendo reconocible,
- incluye números, letras, medidas, símbolos o etiquetas internas de la figura,
- el recorte es imperfecto pero sigue siendo útil,
- no estás seguro de que esté mal.

Reglas importantes:
- No marques una opción solo porque el bbox no sea perfecto.
- No marques una opción solo porque tenga mucho espacio blanco.
- No marques una opción solo porque incluya su letra de opción.
- No marques una opción solo porque la figura esté algo desplazada.
- No marques una opción si el crop permitiría entender la figura.
- Sí marca una opción si el crop realmente falla y no serviría para usar esa opción.

Antes de responder, revisa cada elemento que quieras marcar:
- ¿El error es claro?
- ¿El crop deja de ser útil?
- ¿La figura correcta está ausente, muy cortada o confundida con otra?
- ¿Estoy evitando marcarlo solo por una imperfección menor?

Si dudas, elimina ese elemento de bad_crops.

Restricción:
- Solo puedes devolver: "A", "B", "C", "D", "E".
- No inventes etiquetas.
- No expliques nada.
- No añadas texto fuera del JSON.
- La salida puede ser [], pero no debe ser siempre [] si hay errores evidentes.

Respuesta obligatoria, solo JSON:
{{"bad_crops": []}}
""",

        "A2_B1": f"""
Mira la imagen con bboxes.

Tu tarea NO es resolver el ejercicio.
Tu tarea SOLO es verificar si el recorte de la figura del enunciado está claramente mal hecho.

En este caso:
- El enunciado tiene una figura relevante.
- Las opciones son texto, números o expresiones.
- Evalúa SOLO este recorte: ["enunciado"].
- Nunca devuelvas "A", "B", "C", "D" ni "E".

Colores:
{colores_bboxes}

Criterio general:
- Sé conservador con los falsos positivos.
- No marques el enunciado por imperfecciones pequeñas.
- Marca "enunciado" solo si el error es claro y afecta a la utilidad del crop.
- Si la figura relevante aparece dentro del bbox y es usable, NO marques.
- Si tienes dudas razonables, NO marques.
- Pero si el recorte está claramente mal, sí debes marcarlo.

El recorte del enunciado está mal si:
- no contiene la figura relevante del enunciado,
- contiene solo texto largo del enunciado y no contiene la figura,
- está claramente en una zona equivocada,
- contiene claramente una figura de las opciones en vez de la figura del enunciado,
- corta una parte importante de la figura,
- no permite identificar bien la figura del enunciado,
- o no sería útil para razonar sobre la figura del enunciado.

NO marques "enunciado" como malo si:
- contiene la figura relevante del enunciado,
- contiene la figura relevante con margen o espacio blanco,
- contiene la figura relevante aunque esté descentrada,
- contiene la figura relevante aunque el bbox sea más grande de lo necesario,
- contiene la figura relevante junto con algo de texto cercano,
- corta una parte pequeña pero la figura sigue siendo reconocible,
- incluye números, letras, medidas, símbolos o etiquetas internas de la figura,
- el recorte es imperfecto pero sigue siendo útil,
- no estás seguro de que esté mal.

Reglas importantes:
- No marques "enunciado" solo porque el bbox no sea perfecto.
- No marques "enunciado" solo porque tenga mucho espacio blanco.
- No marques "enunciado" solo porque incluya texto cercano.
- No marques "enunciado" si el crop permitiría entender la figura.
- Sí marca "enunciado" si el crop realmente falla y no serviría para usar la figura.

Antes de responder, revisa si quieres marcar "enunciado":
- ¿El error es claro?
- ¿El crop deja de ser útil?
- ¿La figura relevante está ausente, muy cortada o sustituida por otra?
- ¿Estoy evitando marcarlo solo por una imperfección menor?

Si dudas, devuelve [].

Restricción:
- Solo puedes devolver: "enunciado".
- No inventes etiquetas.
- No expliques nada.
- No añadas texto fuera del JSON.
- La salida puede ser [], pero no debe ser siempre [] si el error es evidente.

Respuesta obligatoria, solo JSON:
{{"bad_crops": []}}
""",

        "A2_B2": f"""
Mira la imagen con bboxes.

Tu tarea NO es resolver el ejercicio.
Tu tarea NO es decidir cuál opción es correcta.
Tu tarea SOLO es verificar si algún recorte de figura está claramente mal hecho.

En este caso:
- El enunciado tiene una figura relevante.
- Las opciones A-E son figuras.
- Evalúa SOLO estos recortes: ["enunciado", "A", "B", "C", "D", "E"].

Colores:
{colores_bboxes}

Criterio general:
- Sé conservador con los falsos positivos.
- No marques recortes por imperfecciones pequeñas.
- Marca un recorte solo si el error es claro y afecta a la utilidad del crop.
- Si la figura correcta aparece dentro del bbox y es usable, NO marques.
- Si tienes dudas razonables, NO marques.
- Pero si el recorte está claramente mal, sí debes marcarlo.

Un recorte está mal si:
- no contiene la figura que corresponde,
- contiene solo texto o solo una etiqueta y no contiene la figura,
- está claramente en una zona equivocada,
- contiene claramente la figura de otro elemento,
- una opción contiene claramente la figura de otra opción,
- el enunciado contiene claramente una figura de opción en vez de la figura del enunciado,
- corta una parte importante de la figura,
- mezcla varias figuras de forma que confunde el recorte,
- no permite identificar bien la figura correspondiente,
- o no sería útil para razonar sobre esa figura.

NO marques un recorte como malo si:
- contiene la figura correcta,
- contiene la figura correcta con margen o espacio blanco,
- contiene la figura correcta aunque esté descentrada,
- contiene la figura correcta aunque el bbox sea más grande de lo necesario,
- contiene la figura correcta junto con su etiqueta,
- contiene la figura correcta junto con algo de texto cercano,
- corta una parte pequeña pero la figura sigue siendo reconocible,
- incluye números, letras, medidas, símbolos o etiquetas internas de la figura,
- el recorte es imperfecto pero sigue siendo útil,
- no estás seguro de que esté mal.

Reglas específicas:
- Para "enunciado", verifica solo si aparece la figura relevante del enunciado.
- Para "A", "B", "C", "D" y "E", verifica solo si aparece la figura de esa opción.
- No evalúes si la opción es matemáticamente correcta.
- No marques una opción porque su figura sea parecida a otra.
- No marques un recorte solo porque el bbox no sea perfecto.
- No marques un recorte solo porque tenga mucho espacio blanco.
- No marques un recorte solo porque incluya texto cercano o etiqueta.
- No marques un recorte si el crop permitiría entender la figura.
- Sí marca un recorte si realmente falla y no serviría para usar esa figura.

Antes de responder, revisa cada elemento que quieras marcar:
- ¿El error es claro?
- ¿El crop deja de ser útil?
- ¿La figura correcta está ausente, muy cortada o confundida con otra?
- ¿Estoy evitando marcarlo solo por una imperfección menor?

Si dudas, elimina ese elemento de bad_crops.

Restricción:
- Solo puedes devolver: "enunciado", "A", "B", "C", "D", "E".
- No inventes etiquetas.
- No expliques nada.
- No añadas texto fuera del JSON.
- La salida puede ser [], pero no debe ser siempre [] si hay errores evidentes.

Respuesta obligatoria, solo JSON:
{{"bad_crops": []}}
"""
    }

    if caso not in prompts:
        raise ValueError(
            f"Tipos no soportados para verificacion OCR: {statement_type}, {options_type}"
        )

    return prompts[caso]


def etiquetas_relevantes(statement_type, options_type):
    caso = f"{statement_type}_{options_type}".replace(".", "")

    if caso == "A1_B1":
        return []
    if caso == "A1_B2":
        return OPCIONES.copy()
    if caso == "A2_B1":
        return ["enunciado"]
    if caso == "A2_B2":
        return ["enunciado"] + OPCIONES.copy()

    return []


def normalizar_etiqueta(valor):
    texto = str(valor).strip().strip("\"'`.,;:[](){}")

    if texto.lower() == "enunciado":
        return "enunciado"

    texto = texto.upper()
    if texto in OPCIONES:
        return texto

    return None


def filtrar_etiquetas(etiquetas, permitidas):
    permitidas_set = set(permitidas)
    salida = []

    for etiqueta in etiquetas:
        etiqueta = normalizar_etiqueta(etiqueta)

        if etiqueta is None:
            continue

        if etiqueta not in permitidas_set:
            continue

        if etiqueta not in salida:
            salida.append(etiqueta)

    return [etiqueta for etiqueta in permitidas if etiqueta in salida]


def extraer_valor_bad_crops(data):
    if isinstance(data, dict):
        for clave in ("bad_crops", "bad_crop", "bad crops", "badCrops"):
            if clave in data:
                return data[clave]
        return []

    return data


def parsear_literal(texto):
    texto = texto.strip()

    if not texto:
        return None

    normalizado_json = (
        texto
        .replace("None", "null")
        .replace("True", "true")
        .replace("False", "false")
    )

    for candidato in (normalizado_json, texto):
        try:
            return json.loads(candidato)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            return ast.literal_eval(candidato)
        except (ValueError, SyntaxError, TypeError):
            pass

    return None


def convertir_valor_a_lista(valor):
    if valor is None:
        return []

    if isinstance(valor, dict):
        return convertir_valor_a_lista(extraer_valor_bad_crops(valor))

    if isinstance(valor, (list, tuple, set)):
        return list(valor)

    if isinstance(valor, str):
        texto = valor.strip()

        if texto.lower() in {"", "null", "none", "no", "ninguno", "ninguna"}:
            return []

        parsed = parsear_literal(texto)
        if parsed is not None and parsed != texto:
            return convertir_valor_a_lista(parsed)

        matches = re.findall(
            r'"([^"]+)"|\'([^\']+)\'|\b(enunciado|[A-E])\b',
            texto,
            re.IGNORECASE,
        )
        return [next(grupo for grupo in match if grupo) for match in matches]

    return [valor]


def limpiar_texto_respuesta(respuesta):
    texto = "" if respuesta is None else str(respuesta).strip()
    texto = re.sub(r"^```(?:json)?", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"```$", "", texto).strip()
    return texto.replace("```json", "").replace("```", "").strip()


def candidatos_respuesta(texto):
    candidatos = [texto]

    for apertura, cierre in (("{", "}"), ("[", "]")):
        inicio = texto.find(apertura)
        fin = texto.rfind(cierre)

        if inicio != -1 and fin != -1 and fin > inicio:
            candidatos.append(texto[inicio:fin + 1])

    match = re.search(
        r"bad[_\s-]*crops?\s*[:=]\s*(\[[^\]]*\])",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        candidatos.append(match.group(1))

    return candidatos


def parsear_respuesta_verificador(respuesta, permitidas):
    if not permitidas:
        return []

    texto = limpiar_texto_respuesta(respuesta)

    for candidato in candidatos_respuesta(texto):
        data = parsear_literal(candidato)

        if data is None:
            continue

        valor = extraer_valor_bad_crops(data)
        lista = convertir_valor_a_lista(valor)

        if lista:
            return filtrar_etiquetas(lista, permitidas)

        if isinstance(valor, (list, tuple, set)) and len(valor) == 0:
            return []

    match_bad_crops = re.search(
        r"bad[_\s-]*crops?\s*[:=]\s*(.+)",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match_bad_crops:
        lista = convertir_valor_a_lista(match_bad_crops.group(1))
        return filtrar_etiquetas(lista, permitidas)

    return filtrar_etiquetas(convertir_valor_a_lista(texto), permitidas)


def etiquetas_con_recorte_none(recortes, colores_bboxes, relevantes):
    fuente = recortes if isinstance(recortes, dict) else colores_bboxes

    if not isinstance(fuente, dict):
        return []

    return [
        etiqueta
        for etiqueta in relevantes
        if fuente.get(etiqueta) is None
    ]


def verificador_ocr(
    statement_type,
    options_type,
    colores_bboxes,
    imagen_bboxes_figuras_enunciado_y_opciones,
    recortes=None,
    model=VISION_MODEL,
    idioma="castellano",
):
    """
    Devuelve la lista final de recortes a volver a probar.

    Combina:
    - recortes relevantes que ya eran None antes de llamar al verificador;
    - recortes relevantes que el verificador visual marca como malos.
    """

    relevantes = etiquetas_relevantes(statement_type, options_type)

    if not relevantes:
        return []

    recortes_none = etiquetas_con_recorte_none(recortes, colores_bboxes, relevantes)
    imagen_recortes = imagen_pil_a_base64(imagen_bboxes_figuras_enunciado_y_opciones)

    if imagen_recortes is None:
        return filtrar_etiquetas(recortes_none, relevantes)

    prompt_verificador = crear_prompt_verificador_recortes(
        statement_type,
        options_type,
        colores_bboxes,
        idioma=idioma,
    )
    respuesta_vl = llamar_modelo_visual(
        imagen_base=imagen_recortes,
        prompt=prompt_verificador,
        model=model,
    )
    bad_crops = parsear_respuesta_verificador(respuesta_vl, relevantes)

    return filtrar_etiquetas(recortes_none + bad_crops, relevantes)


verficador_ocr = verificador_ocr
verificar_ocr = verificador_ocr
verficar_ocr = verificador_ocr
