import copy
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

# Proposed field-name:
# - inheritance
# - inherit_from
# - inheritor
# - hereditary
# - based_on


class Fixtures:

    path: Path
    name: str
    elements: dict = {}

    def __init__(self, file_name: str, model_name: str):
        self.path = Path(__file__).parent.resolve() / file_name
        self.name = model_name
        with open(self.path) as fix_data:
            fixtures = yaml.safe_load(fix_data)[self.name]
            self.elements = {k.lower(): v for k, v in fixtures.items()}

    def __getitem__(self, key) -> dict:
        key = key.lower()
        if key in self.elements:
            return self.elements[key]
        else:
            ValueError(f"{self.name} '{key}' not found!")

    def inheritance(self, values: dict, chain: Optional[list] = None) -> (dict, list):
        if chain is None:
            chain = []
        values = copy.copy(values)
        if "inherit_from" in values:
            fixture_name = values.pop("inherit_from")  # will also remove entry from dict
            if "name" in values and len(chain) < 1:
                base_name = values.get("name")
                if base_name in chain:
                    raise ValueError(f"Inheritance-Circle detected ({base_name} already in {chain})")
                if base_name == fixture_name:
                    raise ValueError(f"Inheritance-Circle detected ({base_name} == {fixture_name})")
                chain.append(base_name)
            fixture_base = copy.copy(self[fixture_name])
            #print(f"{self.name} will inherit from {fixture_name}")
            fixture_base["name"] = fixture_name
            chain.append(fixture_name)
            base_dict, chain = self.inheritance(values=fixture_base, chain=chain)
            for key, value in values.items():
                base_dict[key] = value
            values = base_dict

        elif "name" in values and values.get("name").lower() in self.elements:
            fixture_name = values.get("name").lower()
            if fixture_name == "neutral":
                values = self[fixture_name]
                values["name"] = fixture_name
            else:
                fixture_base = copy.copy(self[fixture_name])
                #print(f"{self.name} '{fixture_name}' will init as {fixture_name}")
                fixture_base["name"] = fixture_name
                chain.append(fixture_name)
                values, chain = self.inheritance(values=fixture_base, chain=chain)

        return values, chain  # TODO: add _chain to values


class FixtureModel(BaseModel):

    class Config:
        # title = "Virtual Source MinDef"
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces
