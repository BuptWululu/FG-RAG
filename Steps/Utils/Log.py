from Config import work_dir, log_name
import os
from pathlib import Path
class Log:
    def __init__(self) -> None:
        pass

    def create_log(self, log_path = os.path.join(work_dir, 'output/log', log_name)):
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    
    def print(self, text, log_path = os.path.join(work_dir, 'output/log', log_name)):
        if not os.path.exists(log_path):
            self.create_log()
        with open(log_path, 'a') as file:
            file.write('\n' + text)
