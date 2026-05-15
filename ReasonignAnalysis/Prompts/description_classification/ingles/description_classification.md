# description_classification (ingles)

```text
You are an expert in classifying visual mathematical problems for multimodal model (VLM) analysis.

Your task is to analyze the textual description, the image, and the thematic context of a mathematical problem and assign one or more labels (multilabel classification) that describe the type of reasoning required to solve it. The thematic context is provided to help interpret the problem setting but should not override the actual reasoning required. Select only the labels indispensable for solving the problem.

The output format is extremely important:
Provide ONLY a valid Python-style list of labels.
Do not include explanations, comments, reasoning, markdown, or additional text.
Do not include secondary, incidental, or merely contextual labels.
Select only the reasoning categories that are strictly necessary to solve the problem.
When in doubt, prefer fewer labels rather than over-labeling.

The output must strictly follow this format:
["label1", "label2"]

If there is only one label, still return a list.

Never invent new labels outside the predefined set.

The possible labels are:

geometry_area: Problems focused on calculating, comparing, or transforming geometric areas. Includes shaded regions, equivalent areas, and surface subdivision.

geometry_angle: Problems where the main objective is to calculate or compare angles. Includes angular relationships in polygons, circles, and triangles.

geometry_length: Problems related to distances, perimeters, sides, or geometric proportions. Includes unknown lengths and metric relationships.

grid_reasoning: Problems based on grids, tables, or cells. Discrete spatial arrangement is important.

spatial_rotation: Problems that require mentally rotating objects or pieces. Includes tilings, interlocking figures, and pattern rotation.

spatial_folding: Problems that require imagining how a 2D figure folds or transforms into 3D. Includes cubes, dice, and flat developments (nets).

spatial_path: Problems related to routes, paths, or connectivity. Includes valid trajectories and movements on graphs or grids.

pattern_recognition: Problems where a visual or numerical rule or pattern must be identified. Includes sequences and repetitive regularities.

constraint_satisfaction: Problems where several constraints must be met simultaneously. Includes sudokus, logical constraints, and multiple conditions.

combinatorial_counting: Problems where one must count valid configurations or possibilities. Includes combinations, arrangements, and case counting.

Theme:
{PROBLEM_THEME}

Classify the following problem:
{PROBLEM_DESCRIPTION}

Output example:
["constraint_satisfaction", "pattern_recognition"]

A couple of examples of the classification would be:

Example 1
Description:
"A grid is shown containing the letters of the word BANANA, and the goal is to find how many times BANANA can be read by moving only between adjacent cells."
Output:
["grid_reasoning", "spatial_path", "combinatorial_counting"]

Example 2
Description:
"Several flat developments of dice are shown, and it must be determined which ones form a valid die."
Output:
["spatial_folding", "spatial_rotation"]

Example 3
Description:
"A square divided into regions is shown, and the task is to calculate the shaded area."
Output:
["geometry_area"]
```
