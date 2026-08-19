const MCP_ENDPOINT = "http://localhost:8000/mcp";

// 공통 JSON-RPC 2.0 요청 헬퍼
async function sendMcpRequest(method, params = {}) {
  const payload = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: method,
    params: params
  };

  const response = await fetch(MCP_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
  }

  const result = await response.json();
  
  if (result.error) {
    throw new Error(`MCP RPC Error: ${result.error.message}`);
  }

  return result.result;
}

// 1. 도구 목록 조회 (LLM에 전달할 스키마 확보)
async function fetchTools() {
  const toolsData = await sendMcpRequest("tools/list");
  console.log("등록된 도구 목록:", toolsData.tools);
  return toolsData.tools;
}

// 2. 도구 실행 (LLM이 tool_call 요청을 보냈을 때 호출)
async function callTool(toolName, toolArgs) {
  const callResult = await sendMcpRequest("tools/call", {
    name: toolName,
    arguments: toolArgs
  });
  console.log(`[${toolName}] 실행 결과:`, callResult);
  return callResult;
}

// 사용 예시
async function runExample() {
  try {
    // 도구 목록 확인
    const tools = await fetchTools();

    // 'add_numbers' 도구 호출
    const result = await callTool("add_numbers", { a: 15, b: 27 });
    console.log("최종 결과 내용:", result.content[0].text); // "42"
  } catch (error) {
    console.error("요청 실패:", error);
  }
}

runExample();
