from dataclasses import dataclass
from typing import List

from fastapi import File, Form, UploadFile


@dataclass
class UploadPhotosRequest:
    fcm_token: str = Form(
        ..., description="FCM registration token for push notifications"
    )
    left_faces: List[UploadFile] = File(..., description="3 left face photos")
    right_faces: List[UploadFile] = File(..., description="3 right face photos")
    front_faces: List[UploadFile] = File(..., description="3 front face photos")
