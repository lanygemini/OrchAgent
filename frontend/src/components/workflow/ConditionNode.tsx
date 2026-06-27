import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

const ConditionNode = ({ data, selected }: NodeProps) => {
  return (
    <div className={`px-4 py-2 shadow-md ${selected ? 'border-yellow-500' : 'border-yellow-200'} bg-yellow-400 text-black`}
      style={{ transform: 'rotate(45deg)', width: 80, height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div className="text-sm font-bold" style={{ transform: 'rotate(-45deg)' }}>{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </div>
  );
};

export default memo(ConditionNode);
