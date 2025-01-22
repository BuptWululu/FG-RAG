import faiss, os, json
from Utils.Log import Log
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import threading
import numpy as np
from hashlib import md5
from Utils.CalculateTime import calculate_time
from Config import work_dir, record_delimiter, encode_batch_size, encoder_name, encoder_api_key, encoder_base_url, encode_max_retries, encode_request_timeout, encode_parallel

class Encoder:
    def __init__(self):
        self.model = None
        self.entity_md5 = {}
        self.entity_description_index = None

    def set_model(self):
        if self.model == None:
            os.environ["OPENAI_API_KEY"] = encoder_api_key
            self.model = OpenAI(base_url=encoder_base_url,
                                http_client=httpx.Client(
                                base_url=encoder_base_url,
                                follow_redirects=True,
                            )).embeddings

    def model_encode(self, str_list):
        self.stop_event = threading.Event()
        def submit_and_retry(executor, id, batch):
            while not self.stop_event.is_set():
                retries = 0
                while retries < encode_max_retries:
                    future = executor.submit(self.model.create, model = encoder_name.lower(), input = batch, encoding_format = 'float')
                    try:
                        res = future.result(timeout = encode_request_timeout)
                        return id, res
                    except Exception as e:
                        retries += 1
                        Log().print(f"Exception occurred for job {id}, retrying... ({retries}/{encode_max_retries})")
                        Log().print(f'Exception Info: {str(e)}')
                        if retries == encode_max_retries:
                            Log().print(f"Max retries reached for job {id}, giving up.")
                            return id, str(e)
            
        Log().print(f'{encoder_name} is Encoding ...')
        Log().print(f'Encode Thread Number: {encode_parallel}')
        embeddings_list = []
        futures = []
        id2res = {}
        executor_outside = ThreadPoolExecutor(max_workers=encode_parallel)
        executor_inside = ThreadPoolExecutor(max_workers=encode_parallel)
        for id, i in enumerate(range(0, len(str_list), encode_batch_size)):
            batch = str_list[i:i + encode_batch_size]
            futures.append(executor_outside.submit(submit_and_retry, executor_inside, id, batch))
        
        for job in tqdm(as_completed(futures), total=len(futures), desc='Encoding', position=0):
            id, res = job.result()
            id2res[id] = res
        
        self.stop_event.set()
        
        executor_inside.shutdown(wait=False)
        executor_outside.shutdown(wait=False)

        for id, i in enumerate(range(0, len(str_list), encode_batch_size)):
            embeddings_list.append(np.array([dp.embedding for dp in id2res[id].data]))

        embeddings = np.concatenate(embeddings_list)
        Log().print(f'{encoder_name} Encode Finished...')
        return embeddings

    @calculate_time
    def encode_entity(self, input_entity_path = os.path.join(work_dir, 'output', 'extracted_entity.json'),
                      output_entity_description_index_path = os.path.join(work_dir, 'index', encoder_name.lower() + '-entity-description.index')):
        def save_entity_md5():
            with open(os.path.join(work_dir, 'output', 'entity_md5.json'), 'w', encoding='utf-8') as file:
                json.dump(self.entity_md5, file, ensure_ascii=False, indent=4)
        
        self.set_model()
        with open(input_entity_path, 'r', encoding='utf-8') as file:
            input_entity_list = json.load(file)
            encode_list = []
            new_id_dict = {}
            original_embeddings = []
            entity_embeddings = []
            self.entity_md5.clear()
            if os.path.exists(os.path.join(work_dir, 'output', 'entity_md5.json')):
                with open(os.path.join(work_dir, 'output', 'entity_md5.json'), 'r', encoding='utf-8') as file:
                    self.entity_md5 = json.load(file)
                self.entity_description_index = faiss.read_index(output_entity_description_index_path)
            
            for i, entity in enumerate(input_entity_list):
                entity_description_str = record_delimiter.join(entity['entity_description']).strip()
                md5_value = md5(entity_description_str.encode('utf-8')).hexdigest()
                if  md5_value not in self.entity_md5:
                    encode_list.append(entity_description_str)
                    new_id_dict[i] = True
                else:
                    original_embeddings.append(self.entity_description_index.reconstruct(self.entity_md5[md5_value]).tolist())
            if len(new_id_dict) == 0:
                Log().print('No New Entity to Encode')
                return
            Log().print(f'{len(new_id_dict)} Entity to Encode')
            new_embeddings = self.model_encode(encode_list).tolist()
            for i, entity in enumerate(input_entity_list):
                entity_description_str = record_delimiter.join(entity['entity_description']).strip()
                md5_value = md5(entity_description_str.encode('utf-8')).hexdigest()
                if i in new_id_dict:
                    entity_embeddings.append(new_embeddings[0])
                    del new_embeddings[0]
                else:
                    entity_embeddings.append(original_embeddings[0])
                    del original_embeddings[0]
                self.entity_md5[md5_value] = i
            entity_embeddings = np.array(entity_embeddings)
            if self.entity_description_index == None:
                self.entity_description_index = faiss.IndexFlatL2(len(entity_embeddings[0]))
            self.entity_description_index.reset()
            self.entity_description_index.add(entity_embeddings)
            faiss.write_index(self.entity_description_index, output_entity_description_index_path)
            save_entity_md5()
    
    @calculate_time
    def encode_chunk(self, input_chunk_path = os.path.join(work_dir, 'output', 'chunk.json'),
                     output_chunk_index = os.path.join(work_dir, 'index', encoder_name.lower() + '-chunk.index')):
        self.set_model()
        with open(input_chunk_path, 'r', encoding='utf-8') as file:
            input_chunk_list = json.load(file)
            chunk_embeddings = self.model_encode([chunk['context'] for chunk in input_chunk_list])
            self.chunk_index = faiss.IndexFlatL2(len(chunk_embeddings[0]))
            self.chunk_index.add(chunk_embeddings)
            faiss.write_index(self.chunk_index, output_chunk_index)

    def encode(self, input_str_list):
        self.set_model()
        if isinstance(input_str_list, str):
            input_str_list = [input_str_list]
        return self.model_encode(input_str_list)
    
    def search(self, index_param, embeddings, topk):
        index = None
        try:
            index = faiss.read_index(index_param)
        except:
            index = index_param
        scores, retrieve_ids = index.search(embeddings, topk)
        scores = scores.tolist()
        retrieve_ids = retrieve_ids.tolist()
        return scores, retrieve_ids