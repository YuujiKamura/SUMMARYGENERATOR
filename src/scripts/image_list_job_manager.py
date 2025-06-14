import os
import time
import shutil
import subprocess
from pathlib import Path
import logging

class ImageListJobManager:
    """
    画像リストJSONをストックし、run_create_yolo_dataset_from_json.pyを順次実行するマネージャー
    """
    def __init__(self, job_dir, done_dir=None, log_dir=None, python_exe=None):
        self.job_dir = Path(job_dir)
        self.done_dir = Path(done_dir) if done_dir else self.job_dir / 'done'
        self.log_dir = Path(log_dir) if log_dir else self.job_dir / 'logs'
        self.python_exe = python_exe or 'python'
        self.script_path = Path(__file__).parent.parent.parent / 'run_create_yolo_dataset_from_json.py'
        self.job_dir.mkdir(exist_ok=True, parents=True)
        self.done_dir.mkdir(exist_ok=True, parents=True)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        logging.basicConfig(filename=self.log_dir / 'job_manager.log', level=logging.INFO)

    def get_job_list(self):
        return sorted(self.job_dir.glob('*.json'))

    def run_all_jobs(self, sleep_sec=10):
        for job_json in self.get_job_list():
            logging.info(f"[JOB] 開始: {job_json}")
            result = self.run_job(job_json)
            if result:
                shutil.move(str(job_json), str(self.done_dir / job_json.name))
                logging.info(f"[JOB] 完了: {job_json}")
            else:
                logging.error(f"[JOB] 失敗: {job_json}")
            time.sleep(sleep_sec)

    def run_job(self, job_json):
        log_path = self.log_dir / f"train_{job_json.stem}.log"
        try:
            cmd = [self.python_exe, str(self.script_path), '--image-list-json', str(job_json)]
            with open(log_path, 'w', encoding='utf-8') as logf:
                proc = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, check=False)
            return proc.returncode == 0
        except Exception as e:
            logging.error(f"[JOB] 例外: {job_json} {e}")
            return False

if __name__ == '__main__':
    # 例: python image_list_job_manager.py --job-dir ./job_queue
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--job-dir', type=str, required=True, help='画像リストJSONのディレクトリ')
    parser.add_argument('--done-dir', type=str, default=None, help='完了済み移動先')
    parser.add_argument('--log-dir', type=str, default=None, help='ログ出力先')
    parser.add_argument('--python-exe', type=str, default=None, help='Python実行ファイル')
    parser.add_argument('--sleep-sec', type=int, default=10, help='ジョブ間の待機秒数')
    args = parser.parse_args()
    mgr = ImageListJobManager(args.job_dir, args.done_dir, args.log_dir, args.python_exe)
    mgr.run_all_jobs(sleep_sec=args.sleep_sec)
