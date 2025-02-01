import json
import os

import inspect

class MyClass:
    pass


print(os.path.join(os.path.dirname(inspect.getfile(MyClass)),'abc/def.json'))