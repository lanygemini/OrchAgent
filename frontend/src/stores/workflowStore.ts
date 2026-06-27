import { create } from 'zustand';
import {
  Node,
  Edge,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
} from 'reactflow';

interface WorkflowState {
  nodes: Node[];
  edges: Edge[];
  selectedNode: Node | null;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: any) => void;
  setSelectedNode: (node: Node | null) => void;
  addNode: (type: string, position: { x: number; y: number }) => void;
  reset: () => void;
}

const initialNodes: Node[] = [
  {
    id: 'start-1',
    type: 'start',
    position: { x: 250, y: 5 },
    data: { label: '开始' },
  },
];

const initialEdges: Edge[] = [];

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: initialNodes,
  edges: initialEdges,
  selectedNode: null,

  onNodesChange: (changes: NodeChange[]) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) });
  },

  onEdgesChange: (changes: EdgeChange[]) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection: any) => {
    const edge = {
      ...connection,
      id: `edge-${Date.now()}`,
      type: 'smoothstep',
    };
    set({ edges: [...get().edges, edge] });
  },

  setSelectedNode: (node: Node | null) => {
    set({ selectedNode: node });
  },

  addNode: (type: string, position: { x: number; y: number }) => {
    const id = `${type}-${Date.now()}`;
    const newNode: Node = {
      id,
      type,
      position,
        data: { label: type === 'agent' ? 'Agent' : type === 'tool' ? '工具' : type === 'condition' ? '条件' : type === 'human' ? '人工' : type },
    };
    set({ nodes: [...get().nodes, newNode] });
  },

  reset: () => {
    set({ nodes: initialNodes, edges: initialEdges, selectedNode: null });
  },
}));
