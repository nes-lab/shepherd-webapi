from pydantic import BaseModel
from pydantic import conint

# TODO: prototype for enabling one web-interface for all models with dynamic typecasting


class Wrapper(BaseModel):
    # initial recording
    type: str
    parameters: BaseModel

    class Config:
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces
