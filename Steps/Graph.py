from Config import work_dir
import os, json, copy

class Graph:
    def __init__(self):
        self.node_number = 0
        self.edge_number = 0
        self.entity2id = {}
        self.id2entity = {}
        self.id2relationship = {}
        self.chunk2entity_id = {}
        self.graph_vector = []
        self.graph_detail = []

    def get_entity_id(self, entity_name):
        return self.entity2id.get(entity_name.lower())

    def build_entity(self, input_entity_path):
        with open(input_entity_path, 'r', encoding='utf-8') as file:
            input_entity_list = json.load(file)
            self.node_number = len(input_entity_list)
            for input_entity in input_entity_list:
                self.graph_vector.append([])
                self.entity2id[input_entity['entity_name'].lower()] = input_entity['entity_id']
                self.id2entity[input_entity['entity_id']] = input_entity
                for chunk_md5 in input_entity['from_chunk_md5']:
                    if self.chunk2entity_id.get(chunk_md5) == None:
                        self.chunk2entity_id[chunk_md5] = [input_entity['entity_id']]
                    else:
                        self.chunk2entity_id[chunk_md5].append(input_entity['entity_id'])
    
    def add_relationship(self, relationship):
        self.id2relationship[relationship['relationship_id']] = relationship
        self.graph_vector[relationship['source_id']].append(relationship)
        if relationship['source_id'] != relationship['target_id']:
            self.graph_vector[relationship['target_id']].append(relationship)

    def build_relationship(self, input_relationship_path):
        with open(input_relationship_path, 'r', encoding='utf-8') as file:
            input_relationship_list = json.load(file)
            self.edge_number = len(input_relationship_list)
            for input_relationship in input_relationship_list:
                self.add_relationship(input_relationship)

    def build_graph(self, input_entity_path = os.path.join(work_dir, 'output', 'extracted_entity.json'),
                    input_relationship_path = os.path.join(work_dir, 'output', 'extracted_relationship.json')):
        self.build_entity(input_entity_path)
        self.build_relationship(input_relationship_path)

    def save_graph(self, output_graph_path = os.path.join(work_dir, 'output', 'graph.json')):
        with open(output_graph_path, 'w', encoding='utf-8') as file:
            for i in range(self.node_number):
                entity_detail = {}
                entity_detail['entity_id'] = i
                entity_detail['entity_name'] = self.id2entity[i]['entity_name']
                entity_detail['neighbor'] = copy.deepcopy(self.graph_vector[i])
                self.graph_detail.append(entity_detail)
            json.dump(self.graph_detail, file, ensure_ascii=False, indent=4)
