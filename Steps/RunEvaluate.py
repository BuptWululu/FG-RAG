from Evaluator import Evaluator
from Config import work_dir
import os

e = Evaluator()

e.evaluate_alternate(first_answer_path = os.path.join(work_dir, 'output', 'result_a.json'),
                    second_answer_path = os.path.join(work_dir, 'output', 'result_b.json'))
