import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

const AgentNode = ({ data, selected }: NodeProps) => {
  const d = data as { label?: string; model?: string };
  return (
    <div className={`px-4 py-2 shadow-md rounded-lg border-2 ${selected ? 'border-blue-500' : 'border-blue-200'} bg-blue-500 text-white`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 bg-white rounded-full" />
        <div>
          <div className="text-sm font-bold">{d.label}</div>
          {d.model && <div className="text-xs opacity-75">{d.model}</div>}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
  );
};

export default memo(AgentNode);
