import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

const AgentNode = ({ data, selected }: NodeProps) => {
  return (
    <div className={`px-4 py-2 shadow-md rounded-lg border-2 ${selected ? 'border-blue-500' : 'border-blue-200'} bg-blue-500 text-white`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 bg-white rounded-full" />
        <div>
          <div className="text-sm font-bold">{data.label}</div>
          {data.model && <div className="text-xs opacity-75">{data.model}</div>}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
  );
};

export default memo(AgentNode);
