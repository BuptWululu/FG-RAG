from Config import generator_path, generator_api_key, generator_base_url, generate_parallel, generate_request_timeout, generate_max_retries
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from tqdm import tqdm
import httpx
import threading
from Utils.Log import Log

class Generator:
    def __init__(self):
        pass
    
    def generate_by_openai(self, query_list, history_list, instruction_list):
        self.stop_event = threading.Event()

        def predict(prompt, history, instruction):
            while not self.stop_event.is_set():
                client = OpenAI(
                    base_url=generator_base_url, 
                    api_key=generator_api_key,
                    http_client=httpx.Client(
                        base_url=generator_base_url,
                        follow_redirects=True,
                    ),
                )
                messages = [{"role": "system", "content": instruction}]
                messages.extend(history)
                messages.append({"role": "user", "content": prompt})
                response = client.chat.completions.create(
                    model=generator_path,
                    messages=messages
                )
                msg = response.choices[0].message.content.strip()

                return msg
        
        def submit_and_retry(executor, id, query, history, instruction):
            while not self.stop_event.is_set():
                retries = 0
                while retries < generate_max_retries:
                    future = executor.submit(predict, query, history, instruction)
                    try:
                        res = future.result(timeout = generate_request_timeout)
                        return id, res
                    except Exception as e:
                        retries += 1
                        Log().print(f"Exception occurred for job {id}, retrying... ({retries}/{generate_max_retries})")
                        Log().print(f'Exception Info: {str(e)}')
                        if retries == generate_max_retries:
                            Log().print(f"Max retries reached for job {id}, giving up.")
                            return id, str(e)
    
        Log().print(f'Generate Number: {len(query_list)}')
        Log().print(f'Generate Thread Number: {generate_parallel}')
        id2res = {}
        executor_outside = ThreadPoolExecutor(max_workers=generate_parallel)
        executor_inside = ThreadPoolExecutor(max_workers=generate_parallel)
        futures = [executor_outside.submit(submit_and_retry, executor_inside, id, query, history_list[id], instruction_list[id]) for id, query in enumerate(query_list)]
        for job in tqdm(as_completed(futures), total=len(futures), desc='LLM Generates', position=0):
            id, res = job.result()
            id2res[id] = res
        
        self.stop_event.set()
        
        executor_inside.shutdown(wait=False)
        
        executor_outside.shutdown(wait=False)
        return [id2res[id] for id in sorted(id2res.keys())]

    
    def generate(self, query_list, generator_path = generator_path, history_list = None, instruction_list = None):
        if history_list == None:
            history_list = [[] for _ in range(len(query_list))]
        if instruction_list == None:
            instruction_list = ['You are a helpful assistant.' for _ in range(len(query_list))]

        return self.generate_by_openai(query_list, history_list, instruction_list)
