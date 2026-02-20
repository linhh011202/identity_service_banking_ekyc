from dataclasses import dataclass
from typing import List

from fastapi import File, UploadFile


@dataclass
class UploadPhotosRequest:
    left_faces: List[UploadFile] = File(..., description="3 left face photos")
    right_faces: List[UploadFile] = File(..., description="3 right face photos")
    front_faces: List[UploadFile] = File(..., description="3 front face photos")
