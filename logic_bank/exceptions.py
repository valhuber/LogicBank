class LBActivateException(Exception):

    message = "LogicBank Activation error"
    def __init__(self, invalid_rules = [], missing_attributes = []):
        LBActivateException = invalid_rules
        self.invalid_rules = invalid_rules
        self.missing_attributes = missing_attributes
        self.message = f'LBActivateException: \n{LBActivateException}\n{self.missing_attributes}\n{self.message}'
        super().__init__(self.message)

    ''' 
    def __str__(self):
        return f'LBActivateException: \n{LBActivateException}\n{self.missing_attributes}\n{self.message}'
    '''
