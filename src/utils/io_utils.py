#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import shutil
from typing import List, Dict, Optional, Tuple, Any
import cv2

from src.utils.models import ClassDefinition, BoundingBox, Annotation, AnnotationDataset, IMAGE_EXTENSIONS

# ...（省略：PhotoCategorizer/src/io_utils.pyの内容をそのままコピー）...
