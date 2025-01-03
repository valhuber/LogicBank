class LBActivateException(Exception):

    message = "LogicBank Activation Error"
    def __init__(self, invalid_rules = [], missing_attributes = []):
        self.invalid_rules = invalid_rules
        self.missing_attributes = missing_attributes
        self.message = f'LBActivateException: \n{self.invalid_rules}\n{self.missing_attributes}\n{self.message}'
        super().__init__(self.message)


class LBCircularDependencyException(Exception):

    def __init__(self, message, formulas = []):
        self.formulas = formulas
        super().__init__(message)
