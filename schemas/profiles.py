import datetime
import re

from fastapi import UploadFile, Form, File, HTTPException, status
from pydantic import BaseModel, field_validator, HttpUrl


class ProfileBaseSchema(BaseModel):
    first_name: str
    last_name: str
    gender: str
    date_of_birth: datetime.date
    info: str


class ProfileRequestSchema(ProfileBaseSchema):
    avatar: UploadFile

    @classmethod
    def as_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        info: str = Form(""),
        gender: str = Form(...),
        date_of_birth: datetime.date = Form(...),
        avatar: UploadFile = File(...),
    ):

        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
        )

    @field_validator("first_name")
    def first_name_validator(cls, name: str):
        try:
            if re.search(r"^[A-Za-z]*$", name) is None:
                raise ValueError(f"{name} contains non-english letters")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        return name

    @field_validator("last_name")
    def last_name_validator(cls, name: str):
        try:
            if re.search(r"^[A-Za-z]*$", name) is None:
                raise ValueError(f"{name} contains non-english letters")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        return name

    @field_validator("gender")
    def gender_validator(cls, gender: str):
        try:
            if gender not in ("man", "woman"):
                raise ValueError(f"Gender must be either 'man' or 'woman'")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        return gender

    @field_validator("date_of_birth")
    def date_of_birth_validator(cls, date: datetime.date):
        try:
            if date.year < 1900:
                raise ValueError(f"Date must be greater than 1900.")
            age = (datetime.date.today() - date).days // 365
            if age < 18:
                raise ValueError(f"Age must be greater than 18 years.")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        return date

    @field_validator("info")
    def info_validator(cls, info: str):
        if len(info) == 0 or len(info.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Info field cannot be empty or contain only spaces.",
            )
        return info


class ProfileResponseSchema(ProfileBaseSchema):
    avatar: str
