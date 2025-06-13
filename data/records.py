from dataclasses import dataclass
from typing import Any, List, Tuple

@dataclass(frozen=True)
class Record:
    category: str
    number: Any
    remarks: str
    criteria: List[str]
    match: str = 'any'
    photo_category: str = ''
    key: Tuple = ()

    def get_remarks(self) -> str:
        return self.remarks

    def get_number(self) -> Any:
        return self.number

    def get_category(self) -> str:
        return self.category
