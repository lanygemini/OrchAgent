NL2SQL_TRANSLATION_PROMPT = """你是一个专业的 NL2SQL 翻译助手。请将用户的自然语言查询翻译为 SQL 查询语句。

数据库表结构：
{db_schema}

用户查询：
{nl_query}

要求：
1. 只生成 SELECT 查询语句
2. 表名和字段名严格使用数据库中实际存在的名称
3. 如果查询涉及模糊匹配，使用 LIKE 或 ILIKE
4. 如果查询涉及聚合，使用 GROUP BY
5. 如果查询需要排序，使用 ORDER BY
6. 生成简洁高效的 SQL，避免不必要的子查询
7. 如果无法将用户查询翻译为安全的 SQL，请说明原因

请只输出 SQL 语句，不要添加额外说明："""


SQL_SAFETY_PROMPT = """请审查以下 SQL 查询是否符合安全规范：

SQL: {sql}

安全规则：
1. 只允许 SELECT 和 WITH 语句
2. 不允许 DROP、ALTER、TRUNCATE、DELETE、INSERT、UPDATE、CREATE、GRANT、REVOKE
3. 不允许执行存储过程或函数
4. 不允许访问系统表或系统视图

请判断此 SQL 是否安全，并说明理由。"""
