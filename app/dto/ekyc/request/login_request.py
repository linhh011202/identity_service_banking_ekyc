from typing import List

from fastapi import File, Form, UploadFile
from dataclasses import dataclass


@dataclass
class LoginRequest:
    email: str = Form(..., description="User email")
    fcm_token: str = Form(
        ..., description="FCM registration token for push notifications"
    )
    faces: List[UploadFile] = File(..., description="3 face photos for login")
