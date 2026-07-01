import { type Node, type Edge } from '@xyflow/react'
import { Button } from '../ui'

export interface NodeData {
  label?: string
  type?: string
  agent_id?: string | null
  tool_id?: string | null
  config?: Record<string, any>
}

interface AgentOption {
  id: string
  name: string
  model_name?: string
}

interface ToolOption {
  id: string
  name: string
  type?: string
}

interface NodePanelProps {
  node: Node | null
  selectedEdge: Edge | null
  agents: AgentOption[]
  tools: ToolOption[]
  onChange: (nodeId: string, patch: Partial<NodeData>) => void
  onDeleteNode: (nodeId: string) => void
  onDeleteEdge: (edgeId: string) => void
  onClose: () => void
}

const TYPE_LABELS: Record<string, string> = {
  start: '开始',
  end: '结束',
  agent: 'Agent',
  tool: '工具',
  condition: '条件',
  fork: '分支',
  join: '汇合',
  human: '人工',
}

const fieldClass =
  'block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'

const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1'

export default function NodePanel({ node, selectedEdge, agents, tools, onChange, onDeleteNode, onDeleteEdge, onClose }: NodePanelProps) {
  // 选中边时显示边删除面板
  if (!node && !selectedEdge) return null

  // 边选中面板
  if (selectedEdge && !node) {
    return (
      <div className="w-80 shrink-0 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col">
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            连线配置
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none"
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <label className={labelClass}>连线 ID</label>
            <input className={`${fieldClass} text-gray-400`} value={selectedEdge.id} disabled readOnly />
          </div>
          <div>
            <label className={labelClass}>起点</label>
            <input className={`${fieldClass} text-gray-400`} value={selectedEdge.source} disabled readOnly />
          </div>
          <div>
            <label className={labelClass}>终点</label>
            <input className={`${fieldClass} text-gray-400`} value={selectedEdge.target} disabled readOnly />
          </div>
          {selectedEdge.label && (
            <div>
              <label className={labelClass}>标签</label>
              <input className={fieldClass} value={selectedEdge.label as string} disabled readOnly />
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <Button variant="danger" className="w-full" onClick={() => onDeleteEdge(selectedEdge.id)}>
            删除连线
          </Button>
        </div>
      </div>
    )
  }

  if (!node) return null

  const data = node.data as NodeData
  const nodeType = data.type || node.type || 'agent'
  const isStartEnd = nodeType === 'start' || nodeType === 'end'

  const patch = (p: Partial<NodeData>) => onChange(node.id, p)

  return (
    <div className="w-80 shrink-0 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          节点配置 · {TYPE_LABELS[nodeType] || nodeType}
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none"
          aria-label="关闭"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <div>
          <label className={labelClass}>节点名称</label>
          <input
            className={fieldClass}
            value={data.label || ''}
            onChange={(e) => patch({ label: e.target.value })}
            placeholder="节点名称"
          />
        </div>

        <div>
          <label className={labelClass}>节点 ID</label>
          <input className={`${fieldClass} text-gray-400`} value={node.id} disabled readOnly />
        </div>

        {nodeType === 'agent' && (
          <div>
            <label className={labelClass}>绑定 Agent</label>
            <select
              className={fieldClass}
              value={data.agent_id || ''}
              onChange={(e) => patch({ agent_id: e.target.value || null })}
            >
              <option value="">— 请选择 Agent —</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                  {a.model_name ? ` (${a.model_name})` : ''}
                </option>
              ))}
            </select>
            {agents.length === 0 && (
              <p className="mt-1 text-xs text-amber-600">暂无可用 Agent，请先在 Agent 管理中创建。</p>
            )}
            {!data.agent_id && agents.length > 0 && (
              <p className="mt-1 text-xs text-amber-600">未绑定 Agent，运行时该节点会报错。</p>
            )}
          </div>
        )}

        {nodeType === 'tool' && (
          <div>
            <label className={labelClass}>绑定工具</label>
            <select
              className={fieldClass}
              value={data.tool_id || ''}
              onChange={(e) => patch({ tool_id: e.target.value || null })}
            >
              <option value="">— 请选择工具 —</option>
              {tools.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                  {t.type ? ` [${t.type}]` : ''}
                </option>
              ))}
            </select>
            {tools.length === 0 && (
              <p className="mt-1 text-xs text-amber-600">暂无可用工具，请先在工具管理中注册。</p>
            )}
            {!data.tool_id && tools.length > 0 && (
              <p className="mt-1 text-xs text-amber-600">未绑定工具，运行时该节点会报错。</p>
            )}
          </div>
        )}

        {nodeType === 'condition' && (
          <div>
            <label className={labelClass}>条件表达式</label>
            <textarea
              className={`${fieldClass} font-mono`}
              rows={4}
              value={data.config?.condition_expr || ''}
              onChange={(e) => patch({ config: { ...(data.config || {}), condition_expr: e.target.value } })}
              placeholder={"例：state['tool_results'].get('xxx') == 'yes'"}
            />
            <p className="mt-1 text-xs text-gray-400">
              表达式可访问 <code>state</code> 与 <code>context</code>，求值为真时走对应分支。
            </p>
          </div>
        )}

        {nodeType === 'fork' && (
          <div>
            <p className="text-xs text-gray-400">
              分支节点会将执行分为多个并行分支。从此节点连出的多条边将并行执行。
            </p>
            <div className="mt-2">
              <label className={labelClass}>分支说明</label>
              <input
                className={fieldClass}
                value={data.config?.fork_description || ''}
                onChange={(e) => patch({ config: { ...(data.config || {}), fork_description: e.target.value } })}
                placeholder="描述并行分支的目的"
              />
            </div>
          </div>
        )}

        {nodeType === 'join' && (
          <div>
            <p className="text-xs text-gray-400">
              汇合节点会等待所有并行分支完成，合并结果后继续执行。所有分支应连入此节点。
            </p>
            <div className="mt-2">
              <label className={labelClass}>汇合策略</label>
              <select
                className={fieldClass}
                value={data.config?.join_strategy || 'wait_all'}
                onChange={(e) => patch({ config: { ...(data.config || {}), join_strategy: e.target.value } })}
              >
                <option value="wait_all">等待所有分支</option>
                <option value="wait_any">任一分支完成即继续</option>
              </select>
            </div>
          </div>
        )}

        {nodeType === 'human' && (
          <div>
            <p className="text-xs text-gray-400">
              人工审批节点：工作流执行到此会暂停，等待人工输入后继续。
            </p>
            <div className="mt-2">
              <label className={labelClass}>提示信息</label>
              <textarea
                className={fieldClass}
                rows={3}
                value={data.config?.human_prompt || ''}
                onChange={(e) => patch({ config: { ...(data.config || {}), human_prompt: e.target.value } })}
                placeholder="请审核以上结果，输入批准或拒绝"
              />
            </div>
          </div>
        )}

        {isStartEnd && (
          <p className="text-xs text-gray-400">起始 / 结束节点无需额外配置。</p>
        )}
      </div>

      {!isStartEnd && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <Button variant="danger" className="w-full" onClick={() => onDeleteNode(node.id)}>
            删除节点
          </Button>
        </div>
      )}
    </div>
  )
}
