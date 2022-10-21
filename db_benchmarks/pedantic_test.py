from pydantic import BaseModel, StrictInt
from typing import Union, Literal, Dict

sample = {0: {0: {'S': 'str1', 'T': 4, 'V': 0x3ff},
              1: {'S': 'str2', 'T': 5, 'V': 0x2ff}},
          1: {
              0: {'S': 'str3', 'T': 8, 'V': 0x1ff},
              1: {'S': 'str4', 'T': 7, 'V': 0x0ff},
              2: {'S': 'str4', 'T': 7, 'V': 0x0ff},
              }
          }


# innermost model
class Data(BaseModel):
    S: str
    T: int
    V: int


class Model(BaseModel):
    __root__: Dict[int, Dict[int, Data]]


print(Model.parse_obj(sample))
