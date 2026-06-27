type SSEEventCallback = {
  onExecutionStarted?: (data: any) => void;
  onStepCompleted?: (data: any) => void;
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
  'step.completed': 'onStepCompleted',
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
  let aborted = false;
  const abortController = new AbortController();

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `/api/v1/executions/${executionId}/stream`;

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        if (callbacks.onError) callbacks.onError(new Error(`SSE connection failed: ${response.status}`));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      while (!aborted) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.slice(7).trim();
          } else if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6).trim();
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              const eventType = currentEvent || data.event || '';
              const callbackKey = EVENT_MAP[eventType];
              if (callbackKey && callbacks[callbackKey]) {
                (callbacks[callbackKey] as any)(data);
              }
            } catch {
              // skip unparseable data
            }
            currentEvent = '';
          }
        }
      }
      reader.releaseLock();
    } catch (e: any) {
      if (!aborted && callbacks.onError) {
        callbacks.onError(e);
      }
    }
  })();

  return () => {
    aborted = true;
    abortController.abort();
  };
}
