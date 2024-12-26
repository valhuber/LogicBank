class LBActivateException(Exception):

    message = "LogicBank Activation error"
    def __init__(self, invalid_rules = [], missing_attributes = []):
        self.invalid_rules = invalid_rules
        self.missing_attributes = missing_attributes
        super().__init__(self.message)

