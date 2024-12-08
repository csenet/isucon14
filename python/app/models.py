from datetime import datetime

import pydantic
from pydantic import field_validator

from ulid import ULID
def encode_ulid(id: bytes) -> str:
    if isinstance(id, str):
        return id
    return str(ULID(id))

def decode_ulid(id: str) -> bytes:
    if isinstance(id, bytes):
        return id
    return ULID(id).bytes

class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)


class Chair(BaseModel):
    id: bytes
    owner_id: bytes
    name: str
    model_id: bytes
    is_active: bool
    access_token: str
    created_at: datetime
    updated_at: datetime
    @field_validator('id', 'owner_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v


class ChairModel(BaseModel):
    id: bytes
    name: str
    speed: int
    created_at: datetime
    updated_at: datetime
    @field_validator('id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v


class ChairLocation(BaseModel):
    id: bytes
    chair_id: bytes
    latitude: int
    longitude: int
    created_at: datetime
    @field_validator('id', 'chair_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v
    


class User(BaseModel):
    id: bytes
    username: str
    firstname: str
    lastname: str
    date_of_birth: str
    access_token: str
    invitation_code: str
    created_at: datetime
    updated_at: datetime
    @field_validator('id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v

class PaymentToken(BaseModel):
    user_id: bytes
    token: str
    created_at: datetime
    @field_validator('id', 'owner_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v


class Ride(BaseModel):
    id: bytes
    user_id: bytes
    chair_id: bytes | None
    pickup_latitude: int
    pickup_longitude: int
    destination_latitude: int
    destination_longitude: int
    evaluation: int | None
    created_at: datetime
    updated_at: datetime
    @field_validator('id', 'user_id', 'chair_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v

class RideStatus(BaseModel):
    id: bytes
    ride_id: bytes
    status: str
    created_at: datetime
    app_sent_at: datetime | None = None
    chair_sent_at: datetime | None = None
    @field_validator('id', 'ride_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v

class Owner(BaseModel):
    id: bytes
    name: str
    access_token: str
    chair_register_token: str
    created_at: datetime
    updated_at: datetime
    @field_validator('id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v

class Coupon(BaseModel):
    user_id: bytes
    code: str
    discount: int
    created_at: datetime
    used_by: str | None
    @field_validator('id', 'user_id', mode='before')
    def convert_str_to_bytes(cls, v):
        if isinstance(v, str):
            return decode_ulid(v)
        return v




