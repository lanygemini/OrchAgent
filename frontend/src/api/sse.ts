type SSEEventCallback = {
  onExecutionStarted?: (data: any) => void;
  onStepStarted?: (data: any) => void;
  onLLMThinking?: (data: any) => void;
  onLLMComplete?: (data: any) => void;
  onToolCall?: (data: any) => void;
  onToolResult?: (data: any) => void;
  onMemoryRetrieved?: (data: any) => void;
  onPathUpdate?: (data: any) => void;
  onHumanRequired?: (data: any) => void;
  onExecutionCompleted?: (data: any) => void;
  onExecutionFailed?: (data: any) => void;
  onError?: (error: any) => void;
};

const EVENT_MAP: Record<string, keyof SSEEventCallback> = {
  'execution.started': 'onExecutionStarted',
  'step.started': 'onStepStarted',
  'llm.thinking': 'onLLMThinking',
  'llm.complete': 'onLLMComplete',
  'tool.call': 'onToolCall',
  'tool.result': 'onToolResult',
  'memory.retrieved': 'onMemoryRetrieved',
  'path.update': 'onPathUpdate',
  'human.required': 'onHumanRequired',
  'execution.completed': 'onExecutionCompleted',
  'execution.failed': 'onExecutionFailed',
};

export function subscribeExecution(
  executionId: string,
  callbacks: SSEEventCallback,
  token?: string,
): () => void {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const eventSource = new EventSource(
    `/api/v1/executions/${executionId}/stream`,
    headers as any,
  );

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[SSE]', data);
    } catch {
      console.log('[SSE] raw:', event.data);
    }
  };

  for (const [eventType, callbackKey] of Object.entries(EVENT_MAP)) {
    eventSource.addEventListener(eventType, (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const cb = callbacks[callbackKey];
        if (cb) cb(data);
      } catch (e) {
        if (callbacks.onError) callbacks.onError(e);
      }
    });
  }

  eventSource.onerror = () => {
    const cb = callbacks.onError;
    if (cb) cb(new Error('SSE connection error'));
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}
