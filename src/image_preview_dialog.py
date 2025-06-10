import sys
import os
# src配下に移動した場合のパス調整
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, 'src'))
sys.path.insert(0, project_root)

# ... existing code ... 