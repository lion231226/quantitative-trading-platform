import re

# Read the file
with open('app/schemas/strategy.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the validation method
old_pattern = r'@model_validator\(mode="after"\)\s*\n\s*@classmethod\s*\n\s*def validate_date_range\(cls, v: date, info\) -> date:\s*\n\s*if info\.data and \'start_date\' in info\.data and v < info\.data\[\'start_date\'\]:\s*\n\s*raise ValueError\(\'结束日期不能早于开始日期\'\)\s*\n\s*return v'

new_method = '''@model_validator(mode='after')
    def validate_date_range(self) -> 'StrategyRequest':
        if self.end_date < self.start_date:
            raise ValueError('结束日期不能早于开始日期')
        return self'''

content = re.sub(old_pattern, new_method, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('app/schemas/strategy.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed field validator syntax")
