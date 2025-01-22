from Config import work_dir
from Utils.CalculateTime import calculate_time
from Utils.Log import Log
from prompt.EvaluatorPrompt import EVALUATE_PROMPT
from Generator import Generator
from datetime import datetime
import json, os, copy, re

class Evaluator:
    def __init__(self):
        self.dir_path = None
        self.first_answer_list = None
        self.second_answer_list = None
        self.instruction = '''---Role---
        You are an expert tasked with evaluating two answers to the same question based on three criteria: **Comprehensiveness**, **Diversity**, and **Empowerment**.
        '''
        self.result_list = []
        self.static = None
        self.generator = Generator()
        self.log = Log()
    
    def create_dir(self, dir_path = os.path.join(work_dir, 'output', 'result-' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))):
        self.dir_path = dir_path
        try:
            os.mkdir(dir_path)
        except FileExistsError:
            self.log.print(f"Directory '{dir_path}' already exists")
    
    def format_result(self, outputs, first_answer_list, second_answer_list):
        def repair_result(output):
            keys = ['Comprehensiveness', 'Diversity', 'Empowerment', 'Overall Winner']
            answer_list = re.findall(r'"Answer 1"|"Answer 2"', output)
            if len(keys) != len(answer_list):
                return output
            result = {}
            for key, answer in zip(keys, answer_list):
                result[key] = {}
                result[key]['Winner'] = answer[1:-1]
                result[key]['Explanation'] = '' 
            return result
        
        for i, output in enumerate(outputs):
            result = {}
            result['query'] = first_answer_list[i]['query']
            result['answer1'] = first_answer_list[i]['model_answer']
            result['answer2'] = second_answer_list[i]['model_answer']
            try:
                if output.startswith('```json'):
                    output = output.strip()[7:-4]
                try:
                    result['result'] = json.loads(output)
                except:
                    result['result'] = repair_result(output)
                self.result_list.append(result)
            except:
                result['result'] = output
                self.result_list.append(result)
        

    @calculate_time
    def evaluate_alternate(self, first_answer_path = os.path.join(work_dir, 'output', 'simplified_answer.json'),
                         second_answer_path = os.path.join(work_dir, 'output', 'naive_answer.json')):
        def init():
            self.static = {'Comprehensiveness': {'Answer 1': 0, 'Answer 2': 0},
                       'Diversity': {'Answer 1': 0, 'Answer 2': 0},
                       'Empowerment': {'Answer 1': 0, 'Answer 2': 0},
                       'Overall Winner': {'Answer 1': 0, 'Answer 2': 0}}
            
        def save_result(output_compare_result_path):
            with open(output_compare_result_path, 'w', encoding='utf-8') as file:
                json.dump([self.static, self.result_list], file, ensure_ascii=False, indent=4)
    
        def switch_winner(winner):
            return winner.replace('Answer 1', 'TMP_STRING').replace('Answer 2', 'Answer 1').replace('TMP_STRING', 'Answer 2')
        
        def remake_alternate():
            for i, result in enumerate(self.result_list):
                for key in result['result']:
                    result['result'][key]['Winner'] = switch_winner(result['result'][key]['Winner'])
                    result['result'][key]['Explanation'] = switch_winner(result['result'][key]['Explanation'])

        def calculate_static():
            for result in self.result_list:
                if not isinstance(result['result'], dict):
                    continue
                for key, value in result['result'].items():
                    self.static[key][value['Winner']] += 1

        def calculate_probability():
            for key in self.static:
                total_count = sum(self.static[key].values())
                self.static[key]['Answer 1 Probability'] = self.static[key]['Answer 1'] / total_count
                self.static[key]['Answer 2 Probability'] = self.static[key]['Answer 2'] / total_count
        self.create_dir()
        init()
        with open(first_answer_path, 'r', encoding='utf-8') as file:
            self.first_answer_list = json.load(file)
        with open(second_answer_path, 'r', encoding='utf-8') as file:
            self.second_answer_list = json.load(file)
        prompt_opposite = []
        prompt_forward = []
        for i in range(len(self.first_answer_list)):
            first_answer = copy.deepcopy(self.first_answer_list[i]['model_answer'])
            second_answer = copy.deepcopy(self.second_answer_list[i]['model_answer'])
            input_query = self.first_answer_list[i]['query']
            prompt_opposite.append(EVALUATE_PROMPT.format(input_query = input_query, first_answer = second_answer, second_answer = first_answer))
            prompt_forward.append(EVALUATE_PROMPT.format(input_query = input_query, first_answer = first_answer, second_answer = second_answer))
        
        outputs = self.generator.generate(query_list = prompt_opposite, instruction_list = [self.instruction for _ in range(len(prompt_opposite))])
        self.format_result(outputs, self.first_answer_list, self.second_answer_list)
        remake_alternate()
        outputs = self.generator.generate(query_list = prompt_forward, instruction_list = [self.instruction for _ in range(len(prompt_forward))])
        self.format_result(outputs, self.first_answer_list, self.second_answer_list)
        calculate_static()
        calculate_probability()
        save_result(output_compare_result_path = os.path.join(self.dir_path, 'compare_result_alternate.json'))
