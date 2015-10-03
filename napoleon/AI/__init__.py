from . random_man import RandomMan
from . taro import Taro

ai_classes = [RandomMan, Taro]
ai_names = [ai.__name__ for ai in ai_classes]
