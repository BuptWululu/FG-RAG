from Config import work_dir, initial_selected_entity_number, query_file, naive_topk, encoder_name, max_description_number, query_type
from Graph import Graph
from Splitter import Splitter
from prompt.GeneratorPrompt import SUMMARIZE_PROMPT, NAIVE_SYSTEM_PROMPT, GENERATE_SYSTEM_PROMPT
from Utils.CalculateTime import calculate_time
from Utils.Log import Log
from Encoder import Encoder
from Generator import Generator
from Extractor import Extractor
from Evaluator import Evaluator
from queue import Queue
import json, os, copy, random

class Pipeline:
    def __init__(self):
        self.graph = Graph()
        self.encoder = Encoder()
        self.generator = Generator()
        self.splitter = Splitter()
        self.extractor = Extractor()
        self.evaluator = Evaluator()
        self.initial_selected_entity_number = initial_selected_entity_number
        self.selected_entity_id = []
        self.selected_twice_entity_id = []
        self.selected_relationship = []
        self.is_selected_entity_id_list = []
        self.is_selected_relationship_id_list = []
        self.description_list = []
        self.query_entity_with_summary_list = []
        self.output_detail_list = []
        self.output_simplified_list = []
        self.output_naive_list = []
    
    @calculate_time
    def match_initial_entity(self, query_list):
        query_entity_list = []
        for i, query in enumerate(query_list):
            self.selected_entity_id.append([])
            self.selected_twice_entity_id.append([])
            for query_entity in query['query_entity']:
                self.selected_entity_id[i].append([])
                self.selected_twice_entity_id[i].append([])
                query_entity_list.append(query_entity)
        
        query_embeddings = self.encoder.encode(query_entity_list)
        scores, retrieve_ids = self.encoder.search(os.path.join(work_dir, 'index', encoder_name.lower() + '-entity-description.index'), query_embeddings, self.initial_selected_entity_number)
        now_query_entity_id = 0
        query_entity_list = []
        for i, query in enumerate(query_list):
            for j, query_entity in enumerate(query['query_entity']):
                self.selected_entity_id[i][j].extend(retrieve_ids[now_query_entity_id])
                next_query_entity_list = []
                for retrieve_id in retrieve_ids[now_query_entity_id]:
                    next_query_entity_list.append(self.graph.id2entity[retrieve_id]['entity_name'])
                query_entity_list.append('\n'.join(next_query_entity_list))
                now_query_entity_id += 1
        
        query_embeddings = self.encoder.encode(query_entity_list)
        scores, retrieve_ids = self.encoder.search(os.path.join(work_dir, 'index', encoder_name.lower() + '-entity-description.index'), query_embeddings, self.initial_selected_entity_number)
        now_query_entity_id = 0
        for i, query in enumerate(query_list):
            for j, query_entity in enumerate(query['query_entity']):
                self.selected_twice_entity_id[i][j].extend(retrieve_ids[now_query_entity_id])
                now_query_entity_id += 1

    @calculate_time
    def graph_retrieval(self, query_list, retrieval_times = 1):
        def init_queue(query_id, query_entity_id, q):
            if retrieval_times > 1:
                for entity_id in self.selected_twice_entity_id[query_id][query_entity_id]:
                    q.put(self.graph.id2entity[entity_id])
                    self.is_selected_entity_id_list[query_id][query_entity_id][entity_id] = True
            else:
                for entity_id in self.selected_entity_id[query_id][query_entity_id]:
                    q.put(self.graph.id2entity[entity_id])
                    self.is_selected_entity_id_list[query_id][query_entity_id][entity_id] = True
        
        def extend_entity(query_id, query_entity_id, relationship, q):
            for id_key in ['source_id', 'target_id']:
                if self.is_selected_entity_id_list[query_id][query_entity_id].get(relationship[id_key]) == True:
                    continue
                self.is_selected_entity_id_list[query_id][query_entity_id][relationship[id_key]] = True
                q.put(self.graph.id2entity[relationship[id_key]])

        def add_relationship(query_id, query_entity_id, relationship, q):
            if self.is_selected_relationship_id_list[query_id][query_entity_id].get(relationship['relationship_id']) != None:
                return
            self.is_selected_relationship_id_list[query_id][query_entity_id][relationship['relationship_id']] = True
            self.description_list[query_id][query_entity_id].append(relationship['relationship_description'])
            extend_entity(query_id, query_entity_id, relationship, q)

        def is_description_list_full(query_id, query_entity_id):
            if len(self.description_list[query_id][query_entity_id]) >= retrieval_times * max_description_number:
                return True
            return False
        
        self.is_selected_entity_id_list = []
        self.is_selected_relationship_id_list = []
        for i, query in enumerate(query_list):
            if retrieval_times == 1:
                self.description_list.append([])
            self.is_selected_entity_id_list.append([])
            self.is_selected_relationship_id_list.append([])
            for j in range(len(query['query_entity'])):
                if retrieval_times == 1:
                    self.description_list[i].append([])
                self.is_selected_entity_id_list[i].append({})
                self.is_selected_relationship_id_list[i].append({})

        for i, query in enumerate(query_list):
            self.query_entity_with_summary_list[i]['description_list'] = []
            for j, query_entity in enumerate(query['query_entity']):
                q = Queue()
                init_queue(i, j, q)
                while not q.empty():
                    entity = q.get()
                    self.description_list[i][j].extend(random.sample(entity['entity_description'], min(len(entity['entity_description']), retrieval_times * max_description_number - len(self.description_list[i][j]))))
                    if is_description_list_full(i, j):
                        break
                    for relationship in random.sample(self.graph.graph_vector[entity['entity_id']], min(len(self.graph.graph_vector[entity['entity_id']]), retrieval_times * max_description_number - len(self.description_list[i][j]))):
                        add_relationship(i, j, relationship, q)
                    if is_description_list_full(i, j):
                        break
                self.description_list[i][j] = list(set(self.description_list[i][j]))
                self.query_entity_with_summary_list[i]['description_list'].append(self.description_list[i][j])

    @calculate_time
    def generate_summary(self, query_list):
        def save_query_entity_with_summary(output_query_entity_with_summary_path = os.path.join(work_dir, 'output', 'query_entity_with_summary.json')):
            with open(output_query_entity_with_summary_path, 'w', encoding='utf-8') as file:
                json.dump(self.query_entity_with_summary_list, file, ensure_ascii=False, indent=4)

        prompt = []
        for i, query in enumerate(query_list):
            for j, entity_name in enumerate(query['query_entity']):
                prompt.append(SUMMARIZE_PROMPT.format(input_entity_name = entity_name, input_description = '\n'.join(self.description_list[i][j]), input_questions = f'**{query['query']}**\n{query["questions"][j]}'))
        
        outputs = self.generator.generate(prompt)
        now_output_id = 0
        for i, query in enumerate(query_list):
            self.query_entity_with_summary_list[i]['summary'] = outputs[now_output_id:now_output_id + len(query['query_entity'])]
            now_output_id += len(query['query_entity'])
        save_query_entity_with_summary()

    @calculate_time
    def build_naive_answer(self, input_query_path = os.path.join(work_dir, 'query', query_file)):
        def sava_naive_answer(output_naive_path = os.path.join(work_dir, 'output', 'naive_answer.json')):
            with open(output_naive_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_naive_list, file, ensure_ascii=False, indent=4)

        chunk_list = self.splitter.get_chunk_list()
        with open(input_query_path, 'r', encoding='utf-8') as file:
            input_query_list = json.load(file)
            Log().print(f'Query Number: {len(input_query_list)}')
            query_embeddings = self.encoder.encode([input_query['query'] for input_query in input_query_list])
            scores, retrieve_ids = self.encoder.search(os.path.join(work_dir, 'index', encoder_name.lower() + '-chunk.index'), query_embeddings, naive_topk)
            prompt = []
            instruction_list = []
            for i, input_query in enumerate(input_query_list):
                prompt.append(input_query['query'])
                instruction_list.append(NAIVE_SYSTEM_PROMPT[query_type].format(input_information = '--New Chunk--\n'.join([chunk_list[chunk_id]['context'] for chunk_id in retrieve_ids[i]])))
            outputs = self.generator.generate(prompt, instruction_list = instruction_list)
            for i, input_query in enumerate(input_query_list):
                output_naive = copy.deepcopy(input_query)
                output_naive['model_answer'] = outputs[i]
                output_naive['retrieve_chunk'] = [{'score': scores[i][j], 'context': chunk_list[chunk_id]['context']} for j, chunk_id in enumerate(retrieve_ids[i])]
                self.output_naive_list.append(output_naive)
            sava_naive_answer()

    @calculate_time
    def build_summary(self, input_query_path = os.path.join(work_dir, 'output', 'query_entity_with_questions.json')):
        self.graph.build_graph()
        with open(input_query_path, 'r', encoding='utf-8') as file:
            input_query_list = json.load(file)
            self.query_entity_with_summary_list = input_query_list
            Log().print(f'Query Number: {len(input_query_list)}')
            self.match_initial_entity(input_query_list)
            self.graph_retrieval(input_query_list)
            self.graph_retrieval(input_query_list, 2)
            self.generate_summary(input_query_list)

    @calculate_time
    def build_fgrag_answer(self, input_summary_path = os.path.join(work_dir, 'output', 'query_entity_with_summary.json')):
        
        def format_summary_answer(outputs):
            for i, output in enumerate(outputs):
                output_detail = copy.deepcopy(self.query_entity_with_summary_list[i])
                output_detail['model_answer'] = output
                self.output_detail_list.append(output_detail)
                output_simplified = {}
                output_simplified['query'] = self.query_entity_with_summary_list[i]['query']
                output_simplified['model_answer'] = output
                self.output_simplified_list.append(output_simplified)
        
        def save_fgrag_answer(output_detail_answer_path = os.path.join(work_dir, 'output', 'detail_answer.json'),
                    output_simplified_answer_path = os.path.join(work_dir, 'output', 'simplified_answer.json')):
            with open(output_detail_answer_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_detail_list, file, ensure_ascii=False, indent=4)
            with open(output_simplified_answer_path, 'w', encoding='utf-8') as file:
                json.dump(self.output_simplified_list, file, ensure_ascii=False, indent=4)

        with open(input_summary_path, 'r', encoding='utf-8') as file:
            self.query_entity_with_summary_list = json.load(file)

        prompt = []
        instruction_list = []
        for query in self.query_entity_with_summary_list:
            input_information = '\n'.join(query['summary'])
            instruction_list.append(GENERATE_SYSTEM_PROMPT[query_type].format(input_information = input_information))
            prompt.append(query['query'])
        
        outputs = self.generator.generate(prompt, instruction_list = instruction_list)
        format_summary_answer(outputs)
        save_fgrag_answer()

    @calculate_time
    def process_corpus(self):
        self.splitter.split_chunk()
        self.extractor.extract_corpus()
        self.extractor.gleaning()

    @calculate_time
    def process_qureies(self):
        self.extractor.extract_query()
        self.extractor.extract_questions()
        self.build_summary()
        self.build_fgrag_answer()

    @calculate_time
    def run_naiverag(self):
        self.splitter.split_chunk()
        self.encoder.encode_chunk()
        self.build_naive_answer()
    
    def run_fgrag(self):
        self.process_corpus()
        self.process_qureies()
