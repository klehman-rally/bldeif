from .konfabulus import Konfabulator

VALID_CONTAINER_ITEMS = ['View', 'Job', 'Folder']

class TestKonfabulator(Konfabulator):
    def add_to_container(self, item):
        item_type = [key for key in item.keys() if key in VALID_CONTAINER_ITEMS][0]
        container = "%ss" % item_type
        self.config['Jenkins'][container].append(item)

    def remove_from_container(self, item):
        item_type = [key for key in item.keys() if key in VALID_CONTAINER_ITEMS][0]
        container = "%ss" % item_type
        reduced_result = [s for s in self.config['Jenkins'][container] if s[item_type] != item[item_type] ]
        self.config['Jenkins'][container] = reduced_result

    def replace_in_container(self, item, new_item):
        self.remove_from_container(item)
        self.add_to_container(new_item)

    def has_item(self, item_type, item_name):
        result = [thing for thing in self.config['Jenkins']["%ss" % item_type] if thing[item_type] == item_name]
        return len(result) > 0



