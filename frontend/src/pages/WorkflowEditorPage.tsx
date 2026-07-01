import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import AgentNode from '../components/workflow/AgentNode'
import ToolNode from '../components/workflow/ToolNode'
import ConditionNode from '../components/workflow/ConditionNode'
import NodePanel, { type NodeData } from '../components/workflow/NodePanel'
import { Button } from '../components/ui'
import { workflowApi, agentApi, toolApi } from '../api/client'

const nodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  condition: ConditionNode,
}

// 可拖拽的节点类型配置
const DRAGGABLE_NODE_TYPES = [
  { type: 'agent', icon: '🤖', label: 'Agent' },
  { type: 'tool', icon: '🔧', label: '工具' },
  { type: 'condition', icon: '◇', label: '条件' },
  { type: 'fork', icon: '⑂', label: '分支' },
  { type: 'join', icon: '⇉', label: '汇合' },
  { type: 'human', icon: '👤', label: '人工' },
]

const defaultNodes: Node[] = [
  {
    id: 'start',
    type: 'agent',
    position: { x: 250, y: 50 },
    data: { label: '开始', type: 'start', agent_id: null, tool_id: null },
  },
  {
    id: 'end',
    type: 'agent',
    position: { x: 250, y: 450 },
    data: { label: '结束', type: 'end', agent_id: null, tool_id: null },
  },
]

function toReactFlowNodes(dagNodes: any[]): Node[] {
  return dagNodes.map((n: any) => ({
    id: n.id,
    type: n.type === 'start' || n.type === 'end' ? 'agent' : n.type,
    position: { x: n.position_x || 0, y: n.position_y || 0 },
    data: {
      label: n.label || n.type,
      type: n.type,
      agent_id: n.agent_id || null,
      tool_id: n.tool_id || null,
      config: n.config || {},
    },
  }))
}

function toReactFlowEdges(dagEdges: any[]): Edge[] {
  return dagEdges.map((e: any) => ({
    id: e.id,
    source: e.source_node_id,
    target: e.target_node_id,
    label: e.label || e.condition_expr || '',
    type: 'smoothstep',
  }))
}

function toDAGFormat(nodes: Node[], edges: Edge[], startNodeId: string) {
  // 条件节点把 config.condition_expr 下放到其出边，供后端边路由使用
  const nodeCondition: Record<string, string> = {}
  for (const n of nodes) {
    const expr = (n.data as NodeData)?.config?.condition_expr
    if ((n.data as NodeData)?.type === 'condition' && typeof expr === 'string' && expr.trim()) {
      nodeCondition[n.id] = expr.trim()
    }
  }

  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: (n.data as NodeData)?.type || n.type || 'agent',
      label: (n.data as NodeData)?.label || '',
      config: (n.data as NodeData)?.config || {},
      position_x: n.position.x,
      position_y: n.position.y,
      agent_id: (n.data as NodeData)?.agent_id || null,
      tool_id: (n.data as NodeData)?.tool_id || null,
    })),
    edges: edges.map((e) => {
      const fromCondition = nodeCondition[e.source] || null
      const labelExpr = typeof e.label === 'string' && e.label.startsWith('if ') ? e.label : null
      return {
        id: e.id,
        source_node_id: e.source,
        target_node_id: e.target,
        condition_expr: fromCondition || labelExpr,
        label: typeof e.label === 'string' ? e.label : '',
      }
    }),
    start_node_id: startNodeId,
  }
}

export default function WorkflowEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isNew = !id || id === 'new'
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [agents, setAgents] = useState<any[]>([])
  const [tools, setTools] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(defaultNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const startNodeId = useMemo(() => {
    const start = nodes.find((n) => (n.data as NodeData)?.type === 'start')
    return start?.id || 'start'
  }, [nodes])

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId],
  )

  useEffect(() => {
    agentApi.list().then((res: any) => setAgents(res.data.items || [])).catch(() => {})
    toolApi.list().then((res: any) => setTools(res.data.items || res.data || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!isNew && id) {
      workflowApi.get(id).then((res: any) => {
        const wf = res.data
        setName(wf.name || '')
        setDescription(wf.description || '')
        if (wf.dag) {
          const rfNodes = toReactFlowNodes(wf.dag.nodes || [])
          // 把出边上的 condition_expr 回填到对应条件节点的 config，供面板回显
          const condBySource: Record<string, string> = {}
          for (const e of wf.dag.edges || []) {
            if (e.condition_expr) condBySource[e.source_node_id] = e.condition_expr
          }
          for (const n of rfNodes) {
            const d = n.data as NodeData
            if (d.type === 'condition' && condBySource[n.id]) {
              d.config = { ...(d.config || {}), condition_expr: condBySource[n.id] }
            }
          }
          setNodes(rfNodes)
          setEdges(toReactFlowEdges(wf.dag.edges || []))
        }
      }).catch(() => navigate('/workflows'))
    }
  }, [id, isNew])

  const onNodeClick: NodeMouseHandler = useCallback((_, node) => {
    setSelectedNodeId(node.id)
  }, [])

  const handleNodeChange = useCallback(
    (nodeId: string, patch: Partial<NodeData>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...(n.data as NodeData), ...patch } } : n,
        ),
      )
    },
    [setNodes],
  )

  const handleNodeDelete = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId))
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId))
      setSelectedNodeId(null)
    },
    [setNodes, setEdges],
  )

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: 'smoothstep' }, eds))
    },
    [setEdges],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const type = event.dataTransfer.getData('application/reactflow')
      if (!type) return
      const position = { x: event.clientX - 150, y: event.clientY - 50 }
      const newId = `${type}-${Date.now()}`
      const labelMap: Record<string, string> = {
        agent: 'AI助手', tool: '工具', condition: '条件',
        fork: '分支', join: '汇合', human: '人工审批',
      }
      const newNode: Node = {
        id: newId,
        type: type === 'condition' ? 'condition' : type === 'tool' ? 'tool' : 'agent',
        position,
        data: { label: labelMap[type] || type, type, agent_id: null, tool_id: null, config: {} },
      }
      setNodes((nds) => [...nds, newNode])
      setSelectedNodeId(newId)
    },
    [setNodes],
  )

  const handleValidate = async () => {
    if (!id || isNew) {
      alert('请先保存工作流后再验证')
      return
    }
    try {
      const res = await workflowApi.validate(id)
      const errors = res.data?.errors || res.data?.detail || []
      if (Array.isArray(errors) && errors.length > 0) {
        alert('验证发现问题：\n' + errors.join('\n'))
      } else {
        alert('✅ 工作流验证通过')
      }
    } catch (e: any) {
      alert(e?.response?.data?.detail || '验证失败')
    }
  }

  const handleSave = async () => {
    if (!name.trim()) {
      alert('请输入工作流名称')
      return
    }
    setSaving(true)
    try {
      const dag = toDAGFormat(nodes, edges, startNodeId)
      const payload = { name, description, dag }
      if (isNew) {
        await workflowApi.create(payload)
      } else {
        await workflowApi.update(id!, payload)
      }
      navigate('/workflows')
    } catch (e: any) {
      alert(e?.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate('/workflows')}>← 返回</Button>
          <input
            className="text-lg font-semibold bg-transparent border-b border-dashed border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100 outline-none focus:border-blue-500 px-1"
            placeholder="工作流名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={handleValidate}>验证</Button>
          <Button onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存'}</Button>
        </div>
      </div>

      <div className="flex flex-1">
        <div className="w-56 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">节点</h3>
          <div className="space-y-2">
            {DRAGGABLE_NODE_TYPES.map((nt) => (
              <div
                key={nt.type}
                className="cursor-grab rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow', nt.type)
                  e.dataTransfer.effectAllowed = 'move'
                }}
              >
                {nt.icon} {nt.label}
              </div>
            ))}
          </div>
          {agents.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-gray-400 mb-2">可用 Agent：</p>
              {agents.map((a: any) => (
                <div key={a.id} className="text-xs text-gray-500 truncate">
                  {a.name} ({a.model_name})
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1" onDragOver={onDragOver} onDrop={onDrop}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedNodeId(null)}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        <NodePanel
          node={selectedNode}
          agents={agents}
          tools={tools}
          onChange={handleNodeChange}
          onDelete={handleNodeDelete}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </div>
  )
}
