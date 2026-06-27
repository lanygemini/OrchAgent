import { useCallback, useMemo } from 'react'
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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import AgentNode from '../components/workflow/AgentNode'
import ToolNode from '../components/workflow/ToolNode'
import ConditionNode from '../components/workflow/ConditionNode'
import { Button } from '../components/ui'

const nodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  condition: ConditionNode,
}

const defaultNodes: Node[] = [
  {
    id: 'start',
    type: 'agent',
    position: { x: 250, y: 50 },
    data: { label: '开始', type: 'start' },
  },
  {
    id: 'end',
    type: 'agent',
    position: { x: 250, y: 350 },
    data: { label: '结束', type: 'end' },
  },
]

export default function WorkflowEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isNew = !id || id === 'new'
  const [nodes, setNodes, onNodesChange] = useNodesState(defaultNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds))
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
      const newNode: Node = {
        id: newId,
        type,
        position,
        data: { label: `新 ${type}`, type },
      }
      setNodes((nds) => [...nds, newNode])
    },
    [setNodes],
  )

  const handleSave = () => {
    // TODO: Implement save logic
    navigate('/workflows')
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate('/workflows')}>← 返回</Button>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {isNew ? '新建工作流' : '编辑工作流'}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary">验证</Button>
          <Button onClick={handleSave}>保存</Button>
          <Button variant="primary">执行</Button>
        </div>
      </div>

      <div className="flex flex-1">
        <div className="w-56 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">节点</h3>
          <div className="space-y-2">
            {['agent', 'tool', 'condition'].map((type) => (
              <div
                key={type}
                className="cursor-grab rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow', type)
                  e.dataTransfer.effectAllowed = 'move'
                }}
              >
                {type === 'agent' && '🤖 Agent'}
                {type === 'tool' && '🔧 工具'}
                {type === 'condition' && '◇ 条件'}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1" onDragOver={onDragOver} onDrop={onDrop}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}
