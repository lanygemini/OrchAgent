export interface User {
  id: string
  username: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user_id: string
  username: string
}

export interface Agent {
  id: string
  name: string
  role: string
  description?: string
  llm_provider: string
  model_name: string
  temperature: number
  max_tokens: number
  system_prompt?: string
  enable_memory: boolean
  memory_window: number
  memory_policy: string
  created_at?: string
  updated_at?: string
}

export interface Tool {
  id: string
  name: string
  description: string
  type: 'builtin' | 'custom' | 'mcp'
  tool_schema?: any
  config?: any
  source?: string
  source_id?: string
  created_at?: string
}

export interface WorkflowNode {
  id: string
  type: 'start' | 'end' | 'agent' | 'tool' | 'condition' | 'fork' | 'join' | 'human'
  label: string
  config?: any
  position_x: number
  position_y: number
  agent_id?: string
  tool_id?: string
}

export interface WorkflowEdge {
  id: string
  source_node_id: string
  target_node_id: string
  condition_expr?: string
  label?: string
}

export interface Workflow {
  id: string
  name: string
  description?: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  start_node_id: string
  status?: string
  created_at?: string
  updated_at?: string
}

export type ExecutionStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'

export interface Execution {
  id: string
  workflow_id: string
  workflow_name: string
  status: ExecutionStatus
  input_data?: any
  output_data?: any
  token_usage?: number
  step_count: number
  started_at?: string
  finished_at?: string
  created_at?: string
}

export interface ExecutionStep {
  id: string
  execution_id: string
  node_id: string
  node_name: string
  status: ExecutionStatus
  input?: any
  output?: any
  token_usage?: number
  duration_ms?: number
  started_at?: string
  finished_at?: string
}

export interface MCPServer {
  id: string
  name: string
  type: 'stdio' | 'sse' | 'builtin'
  command?: string
  args?: string[]
  url?: string
  status: 'online' | 'offline' | 'error'
  tool_count: number
  created_at?: string
}

export interface DashboardStats {
  total_agents: number
  total_workflows: number
  total_tools: number
  total_executions: number
  total_tokens: number
  total_cost: number
  success_rate: number
  executions_today: number
  active_executions: number
  recent_executions: Execution[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface SSEEvent {
  type: 'execution.started' | 'step.started' | 'llm.thinking' | 'llm.complete'
    | 'tool.call' | 'tool.result' | 'memory.retrieved' | 'path.update'
    | 'human.required' | 'execution.completed' | 'execution.failed'
  data: any
}
