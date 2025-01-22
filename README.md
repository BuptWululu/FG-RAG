# FG-RAG: Enhancing Query-Focused Summarization with Context-Aware Fine-Grained Graph RAG

![model](framework.png)

## Table of Contents

- [Usage](#usage)

## Usage

```
conda create -n FG-RAG python=3.12.4 -y
conda activate FG-RAG
conda install -c conda-forge faiss-gpu -y
pip install llama_index==0.12.12
python Steps/RunFGRAG.py
```