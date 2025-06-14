from dataclasses import dataclass

@dataclass
class BBoxYOLO:
    cid: int
    x: float
    y: float
    w: float
    h: float
    @property
    def xywh(self):
        return (self.x, self.y, self.w, self.h)
