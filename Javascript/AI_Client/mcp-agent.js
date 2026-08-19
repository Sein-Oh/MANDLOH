class McpLlmAgent {
  constructor({ mcpUrl, llmUrl, modelName }) {
    this.mcpUrl = mcpUrl;   // 예: 'http://localhost:8000/mcp'
    this.llmUrl = llmUrl;   // 예: 'http://localhost:1234/v1/chat/completions'
    this.modelName = modelName;
    this.messages = [];
  }

  // JSON-RPC 2.0 프로토콜 전송 헬퍼
  async #sendMcp(method, params = {}) {
    const res = await fetch(this.mcpUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: method,
        params: params
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error.message);
    return data.result;
  }

  // 1. FastMCP 서버에서 도구 목록을 가져와 OpenAI 포맷으로 변환
  async getOpenAiTools() {
    const data = await this.#sendMcp("tools/list");
    return data.tools.map(tool => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema
      }
    }));
  }

  // 2. FastMCP 도구 실행
  async executeTool(name, args) {
    const result = await this.#sendMcp("tools/call", {
      name: name,
      arguments: args
    });
    // MCP 응답 결과 텍스트 추출
    return result.content ? result.content.map(c => c.text).join("\n") : JSON.stringify(result);
  }

  // 3. LLM 대화 및 Tool Calling 자동 루프
  async chat(userPrompt) {
    this.messages.push({ role: "user", content: userPrompt });

    // 도구 목록 조회
    const tools = await this.getOpenAiTools();

    while (true) {
      // LM Studio로 요청 전송
      const res = await fetch(this.llmUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: this.modelName,
          messages: this.messages,
          tools: tools.length > 0 ? tools : undefined,
          tool_choice: "auto"
        })
      });

      const data = await res.json();
      const responseMessage = data.choices[0].message;
      this.messages.push(responseMessage);

      // LLM이 도구 호출(Tool Calling)을 요청한 경우
      if (responseMessage.tool_calls && responseMessage.tool_calls.length > 0) {
        for (const toolCall of responseMessage.tool_calls) {
          const fnName = toolCall.function.name;
          const fnArgs = JSON.parse(toolCall.function.arguments);

          console.log(`[도구 실행 중] ${fnName}`, fnArgs);

          // FastMCP 서버 호출
          const toolOutput = await this.executeTool(fnName, fnArgs);

          // 실행 결과를 대화 내역에 추가
          this.messages.push({
            role: "tool",
            tool_call_id: toolCall.id,
            name: fnName,
            content: toolOutput
          });
        }
        // 도구 결과를 반영해 LLM이 다시 답변하도록 루프 지속
        continue;
      }

      // 도구 호출이 없는 일반 텍스트 답변이면 최종 반환
      return responseMessage.content;
    }
  }
}
