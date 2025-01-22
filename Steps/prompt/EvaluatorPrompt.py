
EVALUATE_PROMPT = '''---Goal---

You will evaluate two answers to the same question based on three criteria: **Comprehensiveness**, **Diversity**, and **Empowerment**.

- **Comprehensiveness**: How much detail does the answer provide to cover all aspects and details of the question?

- **Diversity**: How varied and rich is the answer in providing different perspectives and insights on the question?

- **Empowerment**: How well does the answer help the reader understand and make informed judgments about the topic?

For each criterion, choose the better answer (ether Answer 1 or Answer 2) and explain why. Then, select an overal winner based on these three categories.

Here is the question:
{input_query}

Here are the two answers:

**Answer 1:**
{first_answer}

**Answer 2:**
{second_answer}

Evaluate both answers using the three criteria listed above and provide detailed explanations for each criterion.

Output your evaluation in the following JSON format:

{{
    "Comprehensiveness": {{ "Winner": "[Answer 1 or Answer 2]", "Explanation": "[Provide explanation here]" }} ,
    "Diversity": {{ "Winner": "[Answer 1 or Answer 2]", "Explanation": "[Provide explanation here]" }} ,
    "Empowerment": {{ "Winner": "[Answer 1 or Answer 2]", "Explanation": "[Provide explanation here]" }} ,
    "Overall Winner": {{ "Winner": "[Answer 1 or Answer 2]", "Explanation": "[Summarize why ths answer is the overall winner based on the three criteria]" }}
}}
'''
