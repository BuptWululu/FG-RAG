from llama_index.core.node_parser import (
    SentenceSplitter
)
from Config import work_dir, chunk_size, chunk_overlap
from llama_index.core import Document
from Utils.Log import Log
from Utils.CalculateTime import calculate_time
from hashlib import md5
import os, json

class Splitter:
    def __init__(self, chunk_size = chunk_size, chunk_overlap = chunk_overlap):
        self.model = SentenceSplitter(chunk_size = chunk_size, chunk_overlap = chunk_overlap)
        self.output_chunk_list = []
    
    def trans_chunk_list(self, chunk_text_list):
        for chunk_text in chunk_text_list:
            output_chunk_object = {}
            output_chunk_object['context'] = chunk_text.get_content().strip()
            output_chunk_object['md5'] = md5(output_chunk_object['context'].encode('utf-8')).hexdigest()
            self.output_chunk_list.append(output_chunk_object)

    def process_json_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            context_object_list = json.load(file)
            for context_object in context_object_list:
                if isinstance(context_object, dict) and 'context' in context_object:
                    chunk_text_list = self.model.get_nodes_from_documents([Document(text = context_object['context'])])
                else:
                    chunk_text_list = self.model.get_nodes_from_documents([Document(text = context_object)])
                self.trans_chunk_list(chunk_text_list)

    def process_text_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            context = '\n'.join(file.readlines())
            chunk_text_list = self.model.get_nodes_from_documents([Document(text = context)])
            self.trans_chunk_list(chunk_text_list)

    @calculate_time
    def split_chunk(self, input_corpus_dir = os.path.join(work_dir, 'corpus')):
        def save_chunk(output_chunk_path = os.path.join(work_dir, 'output', 'chunk.json')):
            Log().print(f'Chunk Number: {len(self.output_chunk_list)}')
            with open(output_chunk_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_chunk_list, file, ensure_ascii=False, indent=4)

        for root, dirs, files in os.walk(input_corpus_dir):
            for corpus_name in files:
                if corpus_name.endswith('.json'):
                    self.process_json_file(os.path.join(root, corpus_name))
                else:
                    self.process_text_file(os.path.join(root, corpus_name))
        save_chunk()

    def get_chunk_list(self):
        if len(self.output_chunk_list) == 0:
            self.split_chunk()
        return self.output_chunk_list