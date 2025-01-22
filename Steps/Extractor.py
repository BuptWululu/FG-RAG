from prompt.ExtractorPrompt import EXTRACT_CORPUS_PROMPT, EXTRACT_QUERY_PROMPT, EXTRACT_CONTINUE_PROMPT, IF_LOOP_EXTRACT_PROMPT, EXTRACT_QUESTIONS_PROMPT, EXTRACT_WHOLE_QUESTIONS_PROMPT
from Generator import Generator
from Encoder import Encoder
from hashlib import md5
from Utils.CalculateTime import calculate_time
from Utils.Log import Log
from Config import work_dir, tuple_delimiter, record_delimiter, completion_delimiter, query_file, max_gleaning_times, max_extract_entity_number
import json, os, copy, random

class Extractor:
    def __init__(self):
        self.model = Generator()
        self.encoder = Encoder()
        self.output_entity_relationship_list = []
        self.output_entity_list = []
        self.output_relationship_list = []
        self.output_query_entity_list = []
        self.output_query_entity_with_questions_list = []
        self.entity2id = {}
        self.chunk_md5 = {}
        self.strip_str = ' "()' + record_delimiter
        self.max_desc_size = 50

    def output2entity_relationship(self, output):
        ret_list = []
        for line in output.split('\n'):
            if line.startswith('("entity"'):
                try:
                    entity = {}
                    entity['entity_name'] = line.split(tuple_delimiter)[1].strip(self.strip_str)
                    entity['entity_description'] = line.split(tuple_delimiter)[2].strip(self.strip_str)
                    ret_list.append(entity)
                except:
                    pass
            if line.startswith('("relationship"'):
                try:
                    relationship = {}
                    relationship['source_name'] = line.split(tuple_delimiter)[1].strip(self.strip_str)
                    relationship['target_name'] = line.split(tuple_delimiter)[2].strip(self.strip_str)
                    relationship['relationship_description'] = line.split(tuple_delimiter)[3].strip(self.strip_str)
                    ret_list.append(relationship)
                except:
                    pass
        return ret_list
    
    def init_extract(self):
        if os.path.exists(os.path.join(work_dir, 'output', 'chunk_md5.json')):
            with open(os.path.join(work_dir, 'output', 'chunk_md5.json'), 'r', encoding='utf-8') as file:
                self.chunk_md5 = json.load(file)
            with open(os.path.join(work_dir, 'output', 'chunk_with_entity_relationship.json'), 'r', encoding='utf-8') as file:
                self.output_entity_relationship_list = json.load(file)
        Log().print(f'{len(self.chunk_md5)} Chunks already Extract')

    @calculate_time
    def extract_corpus(self, input_chunk_path = os.path.join(work_dir, 'output', 'chunk.json')):
        self.init_extract()
        with open(input_chunk_path, 'r', encoding='utf-8') as file:
            input_chunk_list = json.load(file)
            prompt = []
            extract_id = []
            for i, input_chunk in enumerate(input_chunk_list):
                if input_chunk['md5'] not in self.chunk_md5:
                    self.chunk_md5[input_chunk['md5']] = 'extracted'
                    extract_id.append(i)
                    prompt.append(EXTRACT_CORPUS_PROMPT.format(input_text = input_chunk['context'], tuple_delimiter = tuple_delimiter,
                                                        record_delimiter = record_delimiter, completion_delimiter = completion_delimiter))
            
            outputs = self.model.generate(prompt)
            
            for i, output in enumerate(outputs):
                entity_relationship = copy.deepcopy(input_chunk_list[extract_id[i]])
                entity_relationship['history'] = [{'role': 'user', 'content': prompt[i]},{'role': 'assistant', 'content': output}]
                entity_relationship['entity_relationship'] = self.output2entity_relationship(output)
                self.output_entity_relationship_list.append(entity_relationship)
        
        self.save_chunk_with_entity_relationship()

    @calculate_time
    def gleaning(self):
        if_loop = {}
        self.init_extract()
        for now_gleaning_times in range(max_gleaning_times):
            Log().print(f'Gleaning Times: {now_gleaning_times + 1}')
            prompt = []
            history_list = []
            id_list = []
            for i, input_chunk_with_entity_relationship in enumerate(self.output_entity_relationship_list):
                if if_loop.get(i) == True or self.chunk_md5[input_chunk_with_entity_relationship['md5']] == 'gleaned':
                    continue
                id_list.append(i)
                prompt.append(IF_LOOP_EXTRACT_PROMPT)
                history_list.append(input_chunk_with_entity_relationship['history'])
            
            outputs = self.model.generate(query_list = prompt, history_list = history_list)
            for i, output in enumerate(outputs):
                if output.strip().strip('"').strip("'").lower() != 'yes':
                    if_loop[id_list[i]] = True
            
            prompt.clear()
            history_list.clear()
            id_list.clear()
            for i, input_chunk_with_entity_relationship in enumerate(self.output_entity_relationship_list):
                if if_loop.get(i) == True or self.chunk_md5[input_chunk_with_entity_relationship['md5']] == 'gleaned':
                    self.chunk_md5[input_chunk_with_entity_relationship['md5']] = 'gleaned'
                    continue
                id_list.append(i)
                prompt.append(EXTRACT_CONTINUE_PROMPT)
                history_list.append(input_chunk_with_entity_relationship['history'])
            
            outputs = self.model.generate(query_list = prompt, history_list = history_list)
            for i, output in enumerate(outputs):
                self.output_entity_relationship_list[id_list[i]]['history'].extend([{'role': 'user', 'content': EXTRACT_CONTINUE_PROMPT},{'role': 'assistant', 'content': output}])
                self.output_entity_relationship_list[id_list[i]]['entity_relationship'].extend(self.output2entity_relationship(output))
                if now_gleaning_times == max_gleaning_times - 1:
                    self.chunk_md5[self.output_entity_relationship_list[id_list[i]]['md5']] = 'gleaned'

            self.save_chunk_with_entity_relationship()
            Log().print(f'Loop Chunk Number: {len(if_loop)}')
    
    @calculate_time
    def extract_query(self, input_query_path = os.path.join(work_dir, 'query', query_file)):
        def output2query_entity(output):
            ret_list = output.strip().split('\n')
            entity_list = [item.strip() for item in ret_list if item != '']
            if len(entity_list) > max_extract_entity_number:
                return random.sample(entity_list, max_extract_entity_number)
            return entity_list
        
        def save_query_entity(output_query_entity_path = os.path.join(work_dir, 'output', 'query_entity.json')):
            with open(output_query_entity_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_query_entity_list, file, ensure_ascii=False, indent=4)
        
        with open(input_query_path, 'r', encoding='utf-8') as file:
            input_query_list = json.load(file)
            prompt = []
            for input_query in input_query_list:
                prompt.append(EXTRACT_QUERY_PROMPT.format(input_query = input_query['query']))
            outputs = self.model.generate(prompt)
            for i, output in enumerate(outputs):
                query_entity = copy.deepcopy(input_query_list[i])
                query_entity['history'] = [{'role': 'user', 'content': prompt[i]},{'role': 'assistant', 'content': output}]
                query_entity['query_entity'] = output2query_entity(output)
                self.output_query_entity_list.append(query_entity)
        save_query_entity()

    @calculate_time
    def extract_questions(self, input_query_entity_path = os.path.join(work_dir, 'output', 'query_entity.json')):
        def save_query_with_questions(output_query_entity_with_questions_path = os.path.join(work_dir, 'output', 'query_entity_with_questions.json')):
            with open(output_query_entity_with_questions_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_query_entity_with_questions_list, file, ensure_ascii=False, indent=4)

        with open(input_query_entity_path, 'r', encoding='utf-8') as file:
            self.output_query_entity_with_questions_list = json.load(file)
            prompt = []
            history_list = []
            for query in self.output_query_entity_with_questions_list:
                prompt.extend([EXTRACT_QUESTIONS_PROMPT.format(input_entity_name = entity_name) for entity_name in query['query_entity']])
                prompt.append(EXTRACT_WHOLE_QUESTIONS_PROMPT.format(input_query = query['query']))
                history_list.extend([query['history']] * len(query['query_entity']))
                history_list.append([])
                query['query_entity'].append(query['query'])
            
            outputs = self.model.generate(query_list = prompt, history_list = history_list)
            now_output_id = 0
            for query in self.output_query_entity_with_questions_list:
                query['questions'] = outputs[now_output_id:now_output_id + len(query['query_entity'])]
                now_output_id += len(query['query_entity'])
            save_query_with_questions()

    def add_entity(self, entity, chunk_md5):
        ready_add_entity = {}
        if self.entity2id.get(entity['entity_name'].lower()) == None:
            ready_add_entity['entity_id'] = len(self.output_entity_list)
            ready_add_entity['from_chunk_md5'] = [chunk_md5]
            ready_add_entity['entity_name'] = entity['entity_name']
            ready_add_entity['entity_description'] = [entity['entity_description']]
            self.entity2id[entity['entity_name'].lower()] = ready_add_entity['entity_id']
            self.output_entity_list.append(ready_add_entity)
        else:
            self.output_entity_list[self.entity2id[entity['entity_name'].lower()]]['from_chunk_md5'].append(chunk_md5)
            desc_size = len(self.output_entity_list[self.entity2id[entity['entity_name'].lower()]]['entity_description'])
            if desc_size < self.max_desc_size:
                self.output_entity_list[self.entity2id[entity['entity_name'].lower()]]['entity_description'].append(entity['entity_description'])
            else:
                random.seed(0)
                replace_id = random.randint(0, desc_size)
                if replace_id != desc_size:
                    self.output_entity_list[self.entity2id[entity['entity_name'].lower()]]['entity_description'][replace_id] = entity['entity_description']

    def add_relationship(self, relationship):
        if self.entity2id.get(relationship['source_name'].lower()) == None or self.entity2id.get(relationship['target_name'].lower()) == None:
            return
        ready_add_relationship = {}
        ready_add_relationship['relationship_id'] = len(self.output_relationship_list)
        ready_add_relationship['source_id'] = self.entity2id[relationship['source_name'].lower()]
        ready_add_relationship['source_name'] = relationship['source_name']
        ready_add_relationship['target_id'] = self.entity2id[relationship['target_name'].lower()]
        ready_add_relationship['target_name'] = relationship['target_name']
        ready_add_relationship['relationship_description'] = relationship['relationship_description']
        self.output_relationship_list.append(ready_add_relationship)

    def save_extracted_entity_relationship(self, output_extracted_entity_path = os.path.join(work_dir, 'output', 'extracted_entity.json'),
                                           output_extracted_relationship_path = os.path.join(work_dir, 'output', 'extracted_relationship.json'),
                                           input_chunk_with_entity_relationship_path = os.path.join(work_dir, 'output', 'chunk_with_entity_relationship.json')):
        with open(input_chunk_with_entity_relationship_path, 'r', encoding='utf-8') as file:
            self.output_entity_relationship_list = json.load(file)
        self.entity2id.clear()
        self.output_entity_list.clear()
        self.output_relationship_list.clear()
        for output_entity_relationship in self.output_entity_relationship_list:
            for entity in output_entity_relationship['entity_relationship']:
                if entity.get('entity_description') != None:
                    self.add_entity(entity, output_entity_relationship['md5'])
        for output_entity in self.output_entity_list:
            output_entity['md5'] = md5(record_delimiter.join(output_entity['entity_description']).strip().encode('utf-8')).hexdigest()

        Log().print(f'Extracted Total Entity Number: {len(self.output_entity_list)}')

        with open(output_extracted_entity_path, 'w', encoding='utf-8') as file:
            json.dump(self.output_entity_list, file, ensure_ascii=False, indent=4)
        
        for output_entity_relationship in self.output_entity_relationship_list:
            for relationship in output_entity_relationship['entity_relationship']:
                if relationship.get('relationship_description') != None:
                    self.add_relationship(relationship)
        
        Log().print(f'Extracted Total Relationship Number: {len(self.output_relationship_list)}')
        with open(output_extracted_relationship_path, 'w', encoding='utf-8') as file:
            json.dump(self.output_relationship_list, file, ensure_ascii=False, indent=4)
            
        self.encoder.encode_entity()
    
    def save_chunk_with_entity_relationship(self, output_chunk_with_entity_relationship_path = os.path.join(work_dir, 'output', 'chunk_with_entity_relationship.json')):
        with open(output_chunk_with_entity_relationship_path, 'w', encoding='utf-8') as file:
            json.dump(self.output_entity_relationship_list, file, ensure_ascii=False, indent=4)
        with open(os.path.join(work_dir, 'output', 'chunk_md5.json'), 'w', encoding='utf-8') as file:
            json.dump(self.chunk_md5, file, ensure_ascii=False, indent=4)
        self.save_extracted_entity_relationship()
