class Area:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.explored = False

    def explore(self):
        if self.explored:
            print(f"You have already explored {self.name}.")
        else:
            print(f"Exploring {self.name}...")
            print(self.description)
            self.explored = True


class Map:
    def __init__(self):
        self.areas = {}
        self.current_area = None

    def add_area(self, area_name, area):
        self.areas[area_name] = area
        if self.current_area is None:
            self.current_area = area_name  # Set the first added area as the starting point

    def move_to(self, area_name):
        if area_name not in self.areas:
            print(f"Area {area_name} does not exist on the map.")
            return False
        self.current_area = area_name
        print(f"Moved to {area_name}.")
        return True

    def describe_current_area(self):
        if self.current_area is None:
            print("You are not in any area.")
            return
        area = self.areas[self.current_area]
        print(f"You are in {area.name}.")
        print(area.description)

    def explore_current_area(self):
        if self.current_area is None:
            print("You are not in any area.")
            return
        area = self.areas[self.current_area]
        area.explore()
