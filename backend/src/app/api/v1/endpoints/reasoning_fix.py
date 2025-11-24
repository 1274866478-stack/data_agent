# 修复第287行的语法错误
import json

def format_reasoning_step(step):
    step_data = {
        'type': 'reasoning_step',
        'step': {
            'step_number': step.step_number,
            'description': step.description,
            'reasoning': step.reasoning
        }
    }
    newline = '\n\n'
    return f'data: {json.dumps(step_data)}{newline}'
