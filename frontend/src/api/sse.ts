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

      while (!aborted) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const raw = JSON.parse(line.slice(6));
              console.log('[SSE]', raw);
            } catch {
              console.log('[SSE] raw:', line.slice(6));
            }
          } else if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            buffer = eventType + '\n' + (buffer || '');
          }
        }
      }
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
