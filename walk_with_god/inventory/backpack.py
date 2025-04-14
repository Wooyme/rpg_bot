class Item:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight

    def __str__(self):
        return f"{self.name} (Weight: {self.weight})"


class Backpack:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = []
        self.current_weight = 0

    def add_item(self, item):
        if self.current_weight + item.weight > self.capacity:
            print(f"Cannot add {item.name}. Not enough capacity!")
            return False
        self.items.append(item)
        self.current_weight += item.weight
        print(f"Added {item.name} to the backpack.")
        return True

    def remove_item(self, item_name):
        for item in self.items:
            if item.name == item_name:
                self.items.remove(item)
                self.current_weight -= item.weight
                print(f"Removed {item.name} from the backpack.")
                return True
        print(f"Item {item_name} not found in the backpack.")
        return False

    def list_items(self):
        if not self.items:
            print("The backpack is empty.")
        else:
            print("Backpack contains:")
            for item in self.items:
                print(f" - {item}")

    def is_full(self):
        return self.current_weight >= self.capacity


class Equipment:
    def __init__(self):
        # 初始化装备槽
        self.slots = {
            "weapon": None,  # 武器槽
            "armor": None    # 护甲槽
        }

    def equip(self, slot, item, backpack):
        if slot not in self.slots:
            print(f"Invalid slot: {slot}")
            return False
        if self.slots[slot] is not None:
            print(f"Slot {slot} is already occupied by {self.slots[slot].name}. Unequip it first.")
            return False
        if item not in backpack.items:
            print(f"{item.name} is not in the backpack.")
            return False
        self.slots[slot] = item
        backpack.remove_item(item.name)
        print(f"Equipped {item.name} to {slot} slot.")
        return True

    def unequip(self, slot, backpack):
        if slot not in self.slots:
            print(f"Invalid slot: {slot}")
            return False
        if self.slots[slot] is None:
            print(f"Slot {slot} is already empty.")
            return False
        item = self.slots[slot]
        if not backpack.add_item(item):
            print(f"Cannot unequip {item.name}. Backpack is full.")
            return False
        self.slots[slot] = None
        print(f"Unequipped {item.name} from {slot} slot.")
        return True

    def list_equipment(self):
        print("Current Equipment:")
        for slot, item in self.slots.items():
            if item:
                print(f" - {slot.capitalize()}: {item}")
            else:
                print(f" - {slot.capitalize()}: Empty")

# 示例用法
if __name__ == "__main__":
    # 创建背包，容量为50
    backpack = Backpack(capacity=50)

    # 创建物品
    sword = Item("Sword", 10)
    shield = Item("Shield", 15)
    potion = Item("Potion", 5)

    # 添加物品到背包
    backpack.add_item(sword)
    backpack.add_item(shield)
    backpack.add_item(potion)

    # 查看背包内容
    backpack.list_items()

    # 移除物品
    backpack.remove_item("Shield")

    # 再次查看背包内容
    backpack.list_items()

    # 检查背包是否已满
    print("Is the backpack full?", backpack.is_full())