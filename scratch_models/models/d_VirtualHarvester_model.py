from pydantic import Field
from pydantic import BaseModel


class VirtualHarvester(BaseModel):

    name: str = Field(
        title="Name of virtual harvester",
        description="Slug to use this Name as later reference",
        default="mppt_opt",
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
    )
