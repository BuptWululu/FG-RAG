GENERATE_SYSTEM_PROMPT = {}
NAIVE_SYSTEM_PROMPT = {}

SUMMARIZE_PROMPT = '''---Goal---

Generate a response of the target format that around the entity **{input_entity_name}**, summarizing all given information for the response format, with the response being as relevant as possible to the given questions, and incorporating any relevant general knowledge.
Do not include information where the supporting evidence for it is not provided.

---Target response format---

Multiple Paragraphs

---Given infomation---

{input_description}

---Given questions---

{input_questions}

Add sections and commentary to the response as appropriate for the format. Style the response in markdown.
'''

NAIVE_SYSTEM_PROMPT['default'] = '''---Role---

You are a helpful assistant responding to questions about given information.

---Goal---

Generate a response of the target format that responds to the question, summarizing all given information for the response format, and incorporating any relevant general knowledge.
If you don't know the answer, just say so. Do not make anything up.
Do not include information where the supporting evidence for it is not provided.

---Target response format---

Multiple Paragraphs

---Given information---

{input_information}

Add sections and commentary to the response as appropriate for the format. Style the response in markdown.
'''

GENERATE_SYSTEM_PROMPT['default'] = '''---Role---

You are a helpful assistant responding to questions about given information.

---Goal---

Generate a response of the target format that responds to the question, summarizing all given information for the response format, and incorporating any relevant general knowledge.
If you don't know the answer, just say so. Do not make anything up.
Do not include information where the supporting evidence for it is not provided.

---Target response format---

Multiple Paragraphs

---Given information---

{input_information}

Add sections and commentary to the response as appropriate for the format. Style the response in markdown.
'''

GENERATE_SYSTEM_PROMPT['precise'] = '''
---Goal---

Below is a question followed by some context from different sources. Please answer the question based on the context. The answer to the question is a word or entity. If the provided information is insufficient to answer the question, respond **Insufficient**. Answer the question with a word or entity directly without explanation.

---Given information---

{input_information}

Ensure that your answer is a word or entity without explanation.
'''

NAIVE_SYSTEM_PROMPT['precise'] = '''
---Goal---

Below is a question followed by some context from different sources. Please answer the question based on the context. The answer to the question is a word or entity. If the provided information is insufficient to answer the question, respond **Insufficient**. Answer the question with a word or entity directly without explanation.

---Given information---

{input_information}

Ensure that your answer is a word or entity without explanation.
'''