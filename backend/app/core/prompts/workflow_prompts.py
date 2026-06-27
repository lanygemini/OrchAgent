CONDITION_EVAL_PROMPT = """请根据当前工作流执行状态评估以下条件表达式。

条件表达式：{condition_expr}

上下文变量：
{context}

请输出 true 或 false（仅输出单词，不要其他内容）。
如果条件满足输出 true，否则输出 false。"""


HUMAN_INPUT_PROMPT = """任务需要你的人工输入才能继续执行。

当前工作流：{workflow_name}
当前节点：{node_label}

上下文信息：
{context}

请提供你需要的输入或决策："""
